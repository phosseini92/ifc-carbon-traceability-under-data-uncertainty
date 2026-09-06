"""IFC extraction, strict data checks and traceable production-stage GHG screening."""
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import ifcopenshell.util.shape
import ifcopenshell.util.unit


def read_factors(path):
    factors = {}
    with Path(path).open(newline="") as f:
        for row in csv.DictReader(f):
            rid = row["record_id"]
            if rid in factors:
                raise ValueError(f"Duplicate factor record ID: {rid}")
            for key in ("density_kg_m3", "production_kgco2e_per_kg"):
                row[key] = float(row[key])
                if not math.isfinite(row[key]) or row[key] <= 0:
                    raise ValueError(f"Non-positive or non-finite {key}: {rid}")
            if row["declared_unit"] != "kg":
                raise ValueError(f"Unsupported factor unit: {rid}")
            if row["boundary"] != "KBOB Herstellung / Fabrication only":
                raise ValueError(f"Incompatible assessment boundary: {rid}")
            factors[rid] = row
    return factors


def read_mapping_contract(path):
    data = json.loads(Path(path).read_text())
    if not isinstance(data, dict) or not data:
        raise ValueError("Mapping contract must be a non-empty object")
    required = {"record_id", "source_uuid", "review_status", "review_basis"}
    for material, entry in data.items():
        if not isinstance(entry, dict):
            raise ValueError(f"Contract entry must be an object: {material}")
        missing = required - set(entry)
        if missing:
            raise ValueError(f"Contract entry missing {sorted(missing)}: {material}")
    return data


def declared_volume(model, element):
    volumes = []
    for rel in element.IsDefinedBy:
        definition = rel.RelatingPropertyDefinition
        if definition.is_a("IfcElementQuantity"):
            for q in definition.Quantities:
                if q.Name == "NetVolume" and q.is_a("IfcQuantityVolume"):
                    unit = q.Unit
                    if unit:
                        if not unit.is_a("IfcSIUnit") or unit.UnitType != "VOLUMEUNIT":
                            raise ValueError("Only SI explicit volume units supported")
                        scale = ifcopenshell.util.unit.get_prefix_multiplier(unit.Prefix) ** 3
                    else:
                        if ifcopenshell.util.unit.get_project_unit(model, "VOLUMEUNIT") is None:
                            raise ValueError("Explicit project VOLUMEUNIT required for quantity interpretation")
                        scale = ifcopenshell.util.unit.calculate_unit_scale(model, "VOLUMEUNIT")
                    volumes.append(float(q.VolumeValue) * scale)
    if len(volumes) != 1:
        raise ValueError(f"Expected exactly one NetVolume; found {len(volumes)}")
    return volumes[0]


def material_assignment_descriptor(element):
    """Describe IFC material assignment without implying a carbon allocation rule.

    The carbon audit still requires one monolithic IfcMaterial. This descriptor is
    intentionally broader so independently authored IFCs with layer sets can be
    inspected without silently pretending that layer quantities are known.
    """
    material = ifcopenshell.util.element.get_material(element, should_inherit=True)
    out = {"assignment_type": None, "material_names": [], "layer_thicknesses_project_units": []}
    if material is None:
        return out
    out["assignment_type"] = material.is_a()
    if material.is_a("IfcMaterial"):
        out["material_names"] = [material.Name or ""]
    elif material.is_a("IfcMaterialLayerSetUsage"):
        layer_set = material.ForLayerSet
        out["material_names"] = [(layer.Material.Name or "") for layer in layer_set.MaterialLayers]
        out["layer_thicknesses_project_units"] = [float(layer.LayerThickness) for layer in layer_set.MaterialLayers]
    elif material.is_a("IfcMaterialLayerSet"):
        out["material_names"] = [(layer.Material.Name or "") for layer in material.MaterialLayers]
        out["layer_thicknesses_project_units"] = [float(layer.LayerThickness) for layer in material.MaterialLayers]
    elif hasattr(material, "Materials"):
        out["material_names"] = [(m.Name or "") for m in material.Materials]
    return out


def audit_model(model, factors, mapping, tolerance=.01, mapping_contract=None):
    rows, issues = [], []

    def issue(guid, code, message):
        issues.append(dict(guid=guid, code=code, severity="error", message=message))

    products = sorted(model.by_type("IfcBuildingElement"), key=lambda e: (e.GlobalId, e.id()))
    if not products:
        issue("MODEL", "EMPTY_MODEL", "No supported building elements found")
    if len(model.by_type("IfcProject")) != 1:
        issue("MODEL", "INVALID_PROJECT_COUNT", "Exactly one IfcProject is required")
    elif ifcopenshell.util.unit.get_project_unit(model, "LENGTHUNIT") is None:
        issue("MODEL", "MISSING_LENGTH_UNIT", "Project length unit is required")

    for guid, count in Counter(e.GlobalId for e in products).items():
        if count != 1:
            issue(guid, "DUPLICATE_GUID", "Repeated GlobalId would break traceability")

    settings = ifcopenshell.geom.settings()
    for e in products:
        row = dict(
            guid=e.GlobalId,
            ifc_id=e.id(),
            name=e.Name,
            ifc_class=e.is_a(),
            material_name="",
            material_assignment_type="",
            record_id="",
            mapping_contract_record_id="",
            mapping_contract_ok=None,
            mapping_review_status="",
            mapping_review_basis="",
            declared_volume_m3=None,
            geometry_volume_m3=None,
            relative_quantity_error=None,
            mass_kg=None,
            production_kgco2e=None,
        )
        start = len(issues)
        if e.is_a() not in {"IfcWall", "IfcSlab"}:
            issue(e.GlobalId, "UNSUPPORTED_ELEMENT", f"Not a supported monolithic wall/slab: {e.is_a()}")

        try:
            shape = ifcopenshell.geom.create_shape(settings, e)
            v = float(ifcopenshell.util.shape.get_volume(shape.geometry))
            if not math.isfinite(v) or v <= 0:
                raise ValueError("Geometry volume must be positive and finite")
            row["geometry_volume_m3"] = v
        except Exception as exc:
            issue(e.GlobalId, "INVALID_GEOMETRY", str(exc))

        try:
            v = declared_volume(model, e)
            if not math.isfinite(v) or v <= 0:
                raise ValueError("Declared volume must be positive and finite")
            row["declared_volume_m3"] = v
            if row["geometry_volume_m3"] is not None:
                delta = abs(v - row["geometry_volume_m3"]) / row["geometry_volume_m3"]
                row["relative_quantity_error"] = delta
                if delta > tolerance:
                    issue(e.GlobalId, "QUANTITY_GEOMETRY_MISMATCH", f"Relative difference {delta:.6g} exceeds {tolerance}")
        except Exception as exc:
            issue(e.GlobalId, "INVALID_QUANTITY", str(exc))

        material = ifcopenshell.util.element.get_material(e, should_inherit=True)
        if material is None:
            issue(e.GlobalId, "MISSING_MATERIAL", "Material assignment is absent")
        elif not material.is_a("IfcMaterial"):
            descriptor = material_assignment_descriptor(e)
            row["material_assignment_type"] = descriptor["assignment_type"] or ""
            row["material_name"] = ";".join(descriptor["material_names"])
            issue(e.GlobalId, "UNSUPPORTED_ASSEMBLY", "Layered/multiple-material elements require explicit layer-level allocation")
        else:
            row["material_assignment_type"] = material.is_a()
            row["material_name"] = material.Name or ""
            rid = mapping.get(material.Name)
            if rid not in factors:
                issue(e.GlobalId, "UNMAPPED_MATERIAL", "No explicit valid source record mapping")
            else:
                row["record_id"] = rid
                factor = factors[rid]
                row.update(
                    source_uuid=factor["uuid"],
                    source_row=factor["source_row"],
                    source_column=factor["source_column"],
                    source_name=factor["name_de"],
                    density_kg_m3=factor["density_kg_m3"],
                    production_factor=factor["production_kgco2e_per_kg"],
                    geography=factor["geography"],
                    boundary=factor["boundary"],
                )
                if mapping_contract is not None:
                    contract = mapping_contract.get(material.Name)
                    if contract is None:
                        row["mapping_contract_ok"] = False
                        issue(e.GlobalId, "MAPPING_CONTRACT_MISSING", "No reviewed mapping contract entry for material")
                    else:
                        row["mapping_contract_record_id"] = contract["record_id"]
                        row["mapping_review_status"] = contract["review_status"]
                        row["mapping_review_basis"] = contract["review_basis"]
                        ok = contract["record_id"] == rid and contract["source_uuid"] == factor["uuid"]
                        row["mapping_contract_ok"] = ok
                        if not ok:
                            issue(e.GlobalId, "MAPPING_CONTRACT_MISMATCH", "Mapping differs from the recorded review contract")
                if row["declared_volume_m3"] is not None:
                    row["mass_kg"] = row["declared_volume_m3"] * factor["density_kg_m3"]
                    row["production_kgco2e"] = row["mass_kg"] * factor["production_kgco2e_per_kg"]

        row["element_checks_passed"] = len(issues) == start and sum(x.GlobalId == e.GlobalId for x in products) == 1
        rows.append(row)

    accepted = not issues
    mapped_volume = sum(r["geometry_volume_m3"] or 0 for r in rows if r["record_id"])
    geometry_volume = sum(r["geometry_volume_m3"] or 0 for r in rows)
    return dict(
        accepted=accepted,
        issues=issues,
        rows=rows,
        total_kgco2e=sum(r["production_kgco2e"] for r in rows) if accepted else None,
        mapped_geometry_volume_fraction=mapped_volume / geometry_volume if geometry_volume else 0,
        calculated_subtotal_kgco2e=sum(r["production_kgco2e"] or 0 for r in rows),
        mapping_contract_enabled=mapping_contract is not None,
        semantic_validity_claim="Not established by automated checks; mapping contract protects configuration integrity only",
    )


def rng(seed, key):
    digest = hashlib.sha256(f"{seed}/{key}".encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:16], "big"))


def simulate(rows, config, draws=None, seed=None, active_families=None):
    """Propagate declared uncertainty families with stable keyed streams.

    active_families may be any subset of {'quantity','density','factor'} and is
    used for screening each uncertainty family in isolation. None activates all.
    """
    n = config["draws"] if draws is None else draws
    seed = config["seed"] if seed is None else seed
    if not isinstance(n, int) or n < 2:
        raise ValueError("At least two integer draws required")
    if not rows or any(not r["element_checks_passed"] for r in rows):
        raise ValueError("Only audited complete rows can be simulated")
    active = {"quantity", "density", "factor"} if active_families is None else set(active_families)
    if not active <= {"quantity", "density", "factor"}:
        raise ValueError("Unknown uncertainty family")

    total = np.zeros(n)
    for row in sorted(rows, key=lambda r: r["guid"]):
        q = rng(seed, "quantity/" + row["guid"]).triangular(*config["quantity_multiplier_triangular"], size=n) if "quantity" in active else np.ones(n)
        d = rng(seed, "density/" + row["record_id"]).triangular(*config["density_multiplier_triangular"], size=n) if "density" in active else np.ones(n)
        f = rng(seed, "factor/" + row["record_id"]).triangular(*config["factor_multiplier_triangular"], size=n) if "factor" in active else np.ones(n)
        total += row["production_kgco2e"] * q * d * f
    return total


def stats(values):
    return {
        "mean_kgco2e": float(np.mean(values)),
        "std_kgco2e": float(np.std(values, ddof=1)),
        "p05_kgco2e": float(np.quantile(values, .05)),
        "median_kgco2e": float(np.median(values)),
        "p95_kgco2e": float(np.quantile(values, .95)),
        "mc_mean_standard_error_kgco2e": float(np.std(values, ddof=1) / np.sqrt(len(values))),
    }


def write_csv(path, rows):
    if not rows:
        Path(path).write_text("")
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
