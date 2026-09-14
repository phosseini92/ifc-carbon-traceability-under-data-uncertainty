"""Independent arithmetic, corruption controls, mapping integrity and reproducibility tests."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.api as api

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_model import create_model
from run import experiment_case
from workflow import (
    read_factors,
    read_mapping_contract,
    audit_model,
    simulate,
    declared_volume,
    material_assignment_descriptor,
)

ROOT = Path(__file__).resolve().parents[1]


class TestWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "model.ifc"
        cls.base = create_model(cls.path)
        cls.factors = read_factors(ROOT / "inputs/material_factors.csv")
        cls.mapping = json.loads((ROOT / "inputs/material_mapping.json").read_text())
        cls.contract = read_mapping_contract(ROOT / "inputs/material_mapping_contract.json")
        cls.config = json.loads((ROOT / "inputs/config.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def audit(self, m=None, mapping=None, contract=None):
        return audit_model(
            self.base if m is None else m,
            self.factors,
            self.mapping if mapping is None else mapping,
            self.config["quantity_geometry_relative_tolerance"],
            mapping_contract=self.contract if contract is None else contract,
        )

    def test_01_independent_hand_calculation(self):
        brick = (2 * 6.4 * 3 * .2 + 2 * 4 * 3 * .2) * 900 * .254
        concrete = 6.4 * 4.4 * .2 * 2300 * .0887
        result = self.audit()
        self.assertTrue(result["accepted"])
        self.assertAlmostEqual(result["total_kgco2e"], brick + concrete, places=8)
        self.assertEqual(len(result["rows"]), 5)

    def test_02_ifc_roundtrip_preserves_quantities_and_guids(self):
        original = self.audit()
        reloaded = self.audit(ifcopenshell.open(str(self.path)))
        self.assertEqual([r["guid"] for r in original["rows"]], [r["guid"] for r in reloaded["rows"]])
        self.assertAlmostEqual(original["total_kgco2e"], reloaded["total_kgco2e"])

    def test_03_metre_and_millimetre_geometry_give_same_result(self):
        mm = create_model(Path(self.tmp.name) / "mm.ifc", millimetres=True)
        self.assertTrue(self.audit(mm)["accepted"])
        self.assertAlmostEqual(self.audit()["total_kgco2e"], self.audit(mm)["total_kgco2e"], places=7)

    def test_04_explicit_cubic_millimetre_quantity_unit(self):
        model = ifcopenshell.file.from_string(self.base.to_string())
        q = model.by_type("IfcQuantityVolume")[0]
        original = q.VolumeValue
        q.Unit = api.run("unit.add_si_unit", model, unit_type="VOLUMEUNIT", prefix="MILLI")
        q.VolumeValue = original * 1e9
        self.assertTrue(self.audit(model)["accepted"])

    def test_05_structural_corruptions_block_complete_total(self):
        for name, code in [
            ("missing_material", "MISSING_MATERIAL"),
            ("unmapped_material", "UNMAPPED_MATERIAL"),
            ("volume_x1000", "QUANTITY_GEOMETRY_MISMATCH"),
            ("duplicate_guid", "DUPLICATE_GUID"),
        ]:
            with self.subTest(name=name):
                model, mapping, contract = experiment_case(self.base, name, self.mapping, self.contract)
                result = self.audit(model, mapping, contract)
                self.assertFalse(result["accepted"])
                self.assertIsNone(result["total_kgco2e"])
                self.assertIn(code, [i["code"] for i in result["issues"]])

    def test_06_mapping_tamper_is_blocked_by_contract(self):
        model, mapping, contract = experiment_case(self.base, "mapping_tamper", self.mapping, self.contract)
        result = self.audit(model, mapping, contract)
        self.assertFalse(result["accepted"])
        self.assertIn("MAPPING_CONTRACT_MISMATCH", [i["code"] for i in result["issues"]])

    def test_07_approved_wrong_mapping_remains_semantic_blind_spot(self):
        model, mapping, contract = experiment_case(self.base, "plausible_wrong_mapping_approved", self.mapping, self.contract)
        result = self.audit(model, mapping, contract)
        self.assertTrue(result["accepted"])
        self.assertNotAlmostEqual(result["total_kgco2e"], self.audit()["total_kgco2e"])

    def test_08_missing_contract_entry_is_blocked(self):
        contract = copy.deepcopy(self.contract)
        contract.pop("Clay brick (KBOB generic)")
        result = self.audit(contract=contract)
        self.assertFalse(result["accepted"])
        self.assertIn("MAPPING_CONTRACT_MISSING", [i["code"] for i in result["issues"]])

    def test_09_missing_quantity_is_not_silently_reconstructed(self):
        model = ifcopenshell.file.from_string(self.base.to_string())
        model.by_type("IfcQuantityVolume")[0].Name = "GrossVolume"
        self.assertFalse(self.audit(model)["accepted"])

    def test_10_negative_quantity_is_rejected(self):
        model = ifcopenshell.file.from_string(self.base.to_string())
        model.by_type("IfcQuantityVolume")[0].VolumeValue = -1
        self.assertIn("INVALID_QUANTITY", [i["code"] for i in self.audit(model)["issues"]])

    def test_11_empty_model_is_rejected(self):
        model = ifcopenshell.file(schema="IFC4")
        self.assertFalse(self.audit(model)["accepted"])

    def test_12_reordering_elements_does_not_change_draws(self):
        rows = self.audit()["rows"]
        np.testing.assert_array_equal(simulate(rows, self.config, draws=1000), simulate(rows[::-1], self.config, draws=1000))

    def test_13_smaller_sample_is_exact_prefix(self):
        rows = self.audit()["rows"]
        np.testing.assert_array_equal(simulate(rows, self.config, draws=500), simulate(rows, self.config, draws=2000)[:500])

    def test_14_all_fixed_multipliers_reproduce_nominal(self):
        config = copy.deepcopy(self.config)
        for key in ["quantity_multiplier_triangular", "density_multiplier_triangular", "factor_multiplier_triangular"]:
            config[key] = [1 - 1e-12, 1, 1 + 1e-12]
        np.testing.assert_allclose(simulate(self.audit()["rows"], config, draws=100), self.audit()["total_kgco2e"], rtol=1e-10)

    def test_15_empty_active_family_set_reproduces_nominal_exactly(self):
        rows = self.audit()["rows"]
        values = simulate(rows, self.config, draws=100, active_families=set())
        np.testing.assert_allclose(values, self.audit()["total_kgco2e"], rtol=0, atol=1e-10)

    def test_16_unknown_uncertainty_family_is_rejected(self):
        with self.assertRaises(ValueError):
            simulate(self.audit()["rows"], self.config, draws=100, active_families={"unknown"})

    def test_17_factor_unit_and_boundary_are_checked(self):
        text = (ROOT / "inputs/material_factors.csv").read_text()
        bad_unit = Path(self.tmp.name) / "bad_unit.csv"
        bad_unit.write_text(text.replace(",kg,", ",m3,"))
        with self.assertRaises(ValueError):
            read_factors(bad_unit)
        bad_boundary = Path(self.tmp.name) / "bad_boundary.csv"
        bad_boundary.write_text(text.replace("KBOB Herstellung / Fabrication only", "Full life cycle"))
        with self.assertRaises(ValueError):
            read_factors(bad_boundary)

    def test_18_rejects_simulation_of_invalid_elements(self):
        model, mapping, contract = experiment_case(self.base, "volume_x1000", self.mapping, self.contract)
        with self.assertRaises(ValueError):
            simulate(self.audit(model, mapping, contract)["rows"], self.config)

    def test_19_fixture_bytes_are_reproducible(self):
        path = Path(self.tmp.name) / "again.ifc"
        create_model(path)
        self.assertEqual(self.path.read_bytes(), path.read_bytes())

    def test_20_mapping_contract_reader_rejects_missing_fields(self):
        p = Path(self.tmp.name) / "bad_contract.json"
        p.write_text(json.dumps({"Brick": {"record_id": "02.001"}}))
        with self.assertRaises(ValueError):
            read_mapping_contract(p)

    def test_21_plain_material_descriptor(self):
        wall = self.base.by_type("IfcWall")[0]
        d = material_assignment_descriptor(wall)
        self.assertEqual(d["assignment_type"], "IfcMaterial")
        self.assertEqual(len(d["material_names"]), 1)

    def test_22_external_ifc_layer_assignment_is_recognised_but_not_carbon_released(self):
        path = ROOT / "inputs/external/IfcScript_Slab.ifc"
        model = ifcopenshell.open(str(path))
        slab = model.by_type("IfcSlab")[0]
        descriptor = material_assignment_descriptor(slab)
        self.assertEqual(descriptor["assignment_type"], "IfcMaterialLayerSetUsage")
        self.assertEqual(descriptor["material_names"], ["Concrete"])
        result = audit_model(model, self.factors, {"Concrete": "01.002"}, mapping_contract=None)
        self.assertFalse(result["accepted"])
        self.assertIn("UNSUPPORTED_ASSEMBLY", [i["code"] for i in result["issues"]])

    def test_23_declared_volume_function_requires_exactly_one_netvolume(self):
        wall = self.base.by_type("IfcWall")[0]
        self.assertGreater(declared_volume(self.base, wall), 0)

    def test_24_experiment_case_bytes_are_reproducible(self):
        # Regression test: a v0.2 execution audit (2026-09-05) found that
        # ifcopenshell.api material (un)assignment calls in missing_material
        # and unmapped_material generated a fresh random GlobalId for newly
        # created IfcRoot entities and left SET-valued relationship
        # attributes (e.g. RelatedObjects) in a transient, run-dependent
        # order, so those two derived .ifc fixtures were not
        # byte-reproducible even within a single process. Fixed by having
        # experiment_case() call build_model.stabilize_ids() before
        # returning. This test calls every case twice and requires
        # byte-identical serialisation, so a regression here is caught
        # immediately rather than only showing up as a hash mismatch in a
        # second full run.
        for name in ["complete", "missing_material", "unmapped_material", "volume_x1000",
                     "duplicate_guid", "mapping_tamper", "plausible_wrong_mapping_approved"]:
            with self.subTest(name=name):
                m1, map1, c1 = experiment_case(self.base, name, self.mapping, self.contract)
                m2, map2, c2 = experiment_case(self.base, name, self.mapping, self.contract)
                self.assertEqual(m1.to_string(), m2.to_string())
                self.assertEqual(map1, map2)
                self.assertEqual(c1, c2)


if __name__ == "__main__":
    unittest.main()
