"""Run the controlled IFC-to-carbon research demonstrator with explicit release gates."""
import argparse
import copy
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
import numpy as np
import ifcopenshell
import ifcopenshell.api as api
import ifcopenshell.geom
import ifcopenshell.util.shape
from build_model import create_model, stabilize_ids
from workflow import audit_model, read_factors, read_mapping_contract, simulate, stats, write_csv, write_json

ROOT = Path(__file__).parent


def experiment_case(base, name, mapping, contract):
    model = ifcopenshell.file.from_string(base.to_string())
    mapping = copy.deepcopy(mapping)
    contract = copy.deepcopy(contract)
    walls = sorted(model.by_type("IfcWall"), key=lambda e: e.Name)
    if name == "missing_material":
        api.run("material.unassign_material", model, products=[walls[0]])
    elif name == "unmapped_material":
        api.run("material.unassign_material", model, products=[walls[0]])
        mat = api.run("material.add_material", model, name="Unspecified masonry")
        api.run("material.assign_material", model, products=[walls[0]], type="IfcMaterial", material=mat)
    elif name == "volume_x1000":
        for rel in walls[0].IsDefinedBy:
            d = rel.RelatingPropertyDefinition
            if d.is_a("IfcElementQuantity"):
                for q in d.Quantities:
                    if q.Name == "NetVolume":
                        q.VolumeValue *= 1000
    elif name == "duplicate_guid":
        walls[1].GlobalId = walls[0].GlobalId
    elif name == "mapping_tamper":
        # Mapping configuration changes, but the recorded review contract does not.
        mapping["Clay brick (KBOB generic)"] = "02.003"
    elif name == "plausible_wrong_mapping_approved":
        # Stronger blind spot: the wrong valid record is also written into the review
        # contract, mimicking an erroneous human/configuration approval. Automated
        # integrity checks can then be internally consistent and still semantically wrong.
        mapping["Clay brick (KBOB generic)"] = "02.003"
        contract["Clay brick (KBOB generic)"] = {
            "record_id": "02.003",
            "source_uuid": "45766F6B-BC17-4725-B939-23AA76838736",
            "review_status": "deliberately_wrong_control",
            "review_basis": "Fault-injection control: intentionally approves a valid but unsuitable KBOB record to demonstrate the remaining semantic blind spot.",
            "applicability_note": "Not a valid project mapping."
        }
    elif name != "complete":
        raise ValueError(name)
    # ifcopenshell.api material (un)assignment calls above can create new
    # IfcRoot entities with a fresh random GlobalId and can leave SET-valued
    # relationship attributes in a transient, run-dependent order (see
    # docs/AUDIT_V0_1_TO_V0_2.md addendum / audit report for the v0.2
    # execution finding this fixes). Re-stabilize before this case's model is
    # serialised or hashed so every derived fixture is byte-reproducible,
    # matching the same guarantee already made for the base fixture.
    stabilize_ids(model)
    return model, mapping, contract


def figures(model, rows, samples, results, family_screen, output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

    fig = plt.figure(figsize=(12, 6))
    ax = fig.add_axes([.015, .10, .43, .75], projection="3d")
    settings = ifcopenshell.geom.settings()
    settings.set("use-world-coords", True)
    for e in model.by_type("IfcBuildingElement"):
        shape = ifcopenshell.geom.create_shape(settings, e)
        vertices = ifcopenshell.util.shape.get_vertices(shape.geometry)
        faces = ifcopenshell.util.shape.get_faces(shape.geometry)
        color = "#aa6b4e" if e.is_a("IfcWall") else "#8b98a2"
        ax.add_collection3d(Poly3DCollection(vertices[faces], facecolor=color, edgecolor="white", linewidth=.3, alpha=.7))
    ax.set(xlim=(-.2, 6.6), ylim=(-.2, 4.6), zlim=(0, 3.5), xlabel="X (m)", ylabel="Y (m)", zlabel="Z (m)", title="Controlled IFC4 shell")
    ax.set_box_aspect((6.4, 4.4, 3.2))
    ax.view_init(elev=29, azim=-56)
    ax2 = fig.add_axes([.61, .16, .36, .66])
    ordered = sorted(rows, key=lambda r: r["production_kgco2e"])
    ax2.barh([r["name"] for r in ordered], [r["production_kgco2e"] for r in ordered], color="#17666b")
    ax2.set(xlabel="Production-stage emissions (kg CO2e)", title="Element-level traceability")
    ax2.grid(axis="x", alpha=.15)
    fig.suptitle("IFC-to-carbon traceability demonstrator", fontsize=15, y=.97)
    fig.savefig(output / "model_and_carbon.png", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), layout="constrained")
    axes[0].hist(samples / 1000, bins=45, color="#17666b", alpha=.85)
    lo, hi = np.quantile(samples, [.05, .95]) / 1000
    axes[0].axvline(lo, color="#ac6930", linestyle="--")
    axes[0].axvline(hi, color="#ac6930", linestyle="--")
    axes[0].set(xlabel="Production-stage emissions (t CO2e)", ylabel="Monte Carlo draws", title="Illustrative uncertainty")
    axes[0].text(.03, .96, f"P05-P95: {lo:.2f}-{hi:.2f} t\nConditional on assumed ranges", transform=axes[0].transAxes, va="top", fontsize=9)

    select = [r for r in results if r["case"] != "volume_x1000"]
    labels = [r["case"].replace("_", " ") for r in select]
    values = [r["naive_bias_percent"] for r in select]
    colors = ["#ac6930" if r["case"] == "plausible_wrong_mapping_approved" else "#638d98" for r in select]
    axes[1].barh(labels, values, color=colors)
    axes[1].axvline(0, color="#35454d", linewidth=.8)
    axes[1].set(xlabel="Unchecked result bias versus clean fixture (%)", title="Controlled data-quality faults")
    axes[1].text(.02, -.24, "Mapping tamper is blocked by the review contract; an approved-but-wrong\nsemantic mapping remains an intentional blind spot.", transform=axes[1].transAxes, fontsize=8)
    fig.savefig(output / "uncertainty_and_data_quality.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8.8, 4.6), layout="constrained")
    labels = [r["family"] for r in family_screen]
    widths = [(r["p95_kgco2e"] - r["p05_kgco2e"]) / 1000 for r in family_screen]
    ax.barh(labels, widths, color="#17666b")
    ax.set(xlabel="P05-P95 width (t CO2e)", title="Uncertainty-family screening")
    ax.grid(axis="x", alpha=.15)
    ax.text(.01, -.18, "Screening compares isolated assumed uncertainty families; it is not a formal variance decomposition.", transform=ax.transAxes, fontsize=8)
    fig.savefig(output / "uncertainty_family_screening.png", dpi=180)
    plt.close(fig)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ifc", type=Path, default=ROOT / "inputs/controlled_shell.ifc")
    p.add_argument("--output", type=Path, default=ROOT / "outputs")
    p.add_argument("--draws", type=int)
    p.add_argument("--seed", type=int)
    p.add_argument("--no-charts", action="store_true")
    args = p.parse_args()
    output = args.output
    if output.exists() and any(output.iterdir()):
        p.error("Choose a new or empty output directory to avoid mixing runs")
    output.mkdir(parents=True, exist_ok=True)
    if not args.ifc.exists():
        p.error("IFC file missing; run build_model.py first")

    config = json.loads((ROOT / "inputs/config.json").read_text())
    if args.draws is not None:
        config["draws"] = args.draws
    if args.seed is not None:
        config["seed"] = args.seed
    factors = read_factors(ROOT / "inputs/material_factors.csv")
    mapping = json.loads((ROOT / "inputs/material_mapping.json").read_text())
    contract = read_mapping_contract(ROOT / "inputs/material_mapping_contract.json")
    model = ifcopenshell.open(str(args.ifc))
    audit = audit_model(model, factors, mapping, config["quantity_geometry_relative_tolerance"], mapping_contract=contract)
    write_json(output / "audit.json", audit)
    write_csv(output / "element_ledger.csv", audit["rows"])
    if not audit["accepted"]:
        raise SystemExit("Input blocked by data checks; inspect audit.json. No complete screening total issued.")

    samples = simulate(audit["rows"], config)
    summary = {
        "nominal_kgco2e": audit["total_kgco2e"],
        "draws": len(samples),
        "seed": config["seed"],
        **stats(samples),
        "scope": config["boundary"],
        "uncertainty_status": config["uncertainty_status"],
        "mapping_review_status": sorted({r["mapping_review_status"] for r in audit["rows"]}),
        "semantic_validity_claim": audit["semantic_validity_claim"],
    }
    write_json(output / "summary.json", summary)
    write_csv(output / "monte_carlo_draws.csv", [{"draw": i, "production_kgco2e": float(v)} for i, v in enumerate(samples)])

    cases = [
        "complete",
        "missing_material",
        "unmapped_material",
        "volume_x1000",
        "duplicate_guid",
        "mapping_tamper",
        "plausible_wrong_mapping_approved",
    ] if args.ifc.resolve() == (ROOT / "inputs/controlled_shell.ifc").resolve() else ["complete"]

    results = []
    case_dir = output / "experiments"
    case_dir.mkdir()
    for name in cases:
        altered, case_mapping, case_contract = experiment_case(model, name, mapping, contract)
        altered.write(str(case_dir / f"{name}.ifc"))
        write_json(case_dir / f"{name}_mapping.json", case_mapping)
        write_json(case_dir / f"{name}_contract.json", case_contract)
        result = audit_model(altered, factors, case_mapping, config["quantity_geometry_relative_tolerance"], mapping_contract=case_contract)
        write_json(case_dir / f"{name}_audit.json", result)
        naive = result["calculated_subtotal_kgco2e"]
        interpretation = {
            "mapping_tamper": "Mapping configuration drift detected by the recorded review contract",
            "plausible_wrong_mapping_approved": "Known semantic error remains undetected when an internally consistent review contract is itself wrong",
        }.get(name, "Controlled software experiment")
        results.append(dict(
            case=name,
            accepted_by_release_checks=result["accepted"],
            issue_codes=";".join(sorted({x["code"] for x in result["issues"]})),
            mapped_geometry_volume_fraction=result["mapped_geometry_volume_fraction"],
            released_total_kgco2e=result["total_kgco2e"],
            naive_kgco2e=naive,
            naive_bias_percent=100 * (naive / audit["total_kgco2e"] - 1),
            interpretation=interpretation,
        ))
    write_csv(output / "experiment_results.csv", results)

    convergence = []
    for seed in [config["seed"], config["seed"] + 1, config["seed"] + 2]:
        largest = simulate(audit["rows"], config, draws=25000, seed=seed)
        ref = stats(largest)
        for n in [1000, 2500, 5000, 10000, 25000]:
            st = stats(largest[:n])
            convergence.append(dict(
                seed=seed,
                draws=n,
                **st,
                mean_delta_vs_25000_kgco2e=st["mean_kgco2e"] - ref["mean_kgco2e"],
                p95_delta_vs_25000_kgco2e=st["p95_kgco2e"] - ref["p95_kgco2e"],
                is_comparator=n == 25000,
            ))
    write_csv(output / "convergence.csv", convergence)

    sensitivities = []
    nominal = audit["total_kgco2e"]
    for rid in sorted({r["record_id"] for r in audit["rows"]}):
        contribution = sum(r["production_kgco2e"] for r in audit["rows"] if r["record_id"] == rid)
        for variable, key in [("density", "density_multiplier_triangular"), ("factor", "factor_multiplier_triangular")]:
            for endpoint, multiplier in [("low", config[key][0]), ("high", config[key][2])]:
                value = nominal + contribution * (multiplier - 1)
                sensitivities.append(dict(record_id=rid, variable=variable, endpoint=endpoint, multiplier=multiplier, total_kgco2e=value, delta_percent=100 * (value / nominal - 1)))
    write_csv(output / "one_at_a_time_sensitivity.csv", sensitivities)

    family_screen = []
    for label, families in [
        ("quantity only", {"quantity"}),
        ("density only", {"density"}),
        ("factor only", {"factor"}),
        ("all assumed families", {"quantity", "density", "factor"}),
    ]:
        st = stats(simulate(audit["rows"], config, active_families=families))
        family_screen.append({"family": label, **st, "p05_p95_width_kgco2e": st["p95_kgco2e"] - st["p05_kgco2e"]})
    write_csv(output / "uncertainty_family_screening.csv", family_screen)

    write_json(output / "resolved_config.json", config)
    write_json(output / "resolved_mapping.json", mapping)
    write_json(output / "resolved_mapping_contract.json", contract)
    if not args.no_charts:
        figures(model, audit["rows"], samples, results, family_screen, output)

    tamper = next((r for r in results if r["case"] == "mapping_tamper"), None)
    wrong = next((r for r in results if r["case"] == "plausible_wrong_mapping_approved"), None)
    report = f"""# Run report\n\nNominal selected-material production emissions: {nominal:.3f} kg CO2e.\nMonte Carlo median: {summary['median_kgco2e']:.3f} kg CO2e.\nP05-P95: {summary['p05_kgco2e']:.3f}-{summary['p95_kgco2e']:.3f} kg CO2e.\nThese quantiles reflect illustrative input ranges, not a measured confidence interval.\n\nThe clean input contains {len(audit['rows'])} elements with complete mappings.\nGeometry-derived and declared volumes agree within the configured 1% tolerance.\nThe mapping file also matches the recorded author-review contract. This contract\nprotects configuration integrity; it does not prove semantic or LCA applicability.\n"""
    if tamper:
        report += f"\nA deliberate mapping-file tamper is blocked by {tamper['issue_codes'] or 'release checks'}.\n"
    if wrong:
        report += f"An internally consistent but deliberately wrong approved mapping passes the\nautomated release checks and changes the unchecked result by {wrong['naive_bias_percent']:.2f}%.\nThis is the central semantic limitation: internal consistency is not evidence that\nthe selected environmental record is substantively correct. Independent review of\nproduct identity, geography, technology, boundary and functional applicability remains necessary.\n"
    report += """\nThe geometry is a controlled single-room shell, not a real building study.\nKBOB Fabrication is used as published; EN 15804 A1-A3 equivalence is not asserted.\nExcluded: mortar, reinforcement, openings, roof, finishes, services, construction,\noperation, maintenance, end-of-life, circularity credits and occupant experience.\nThere is no BEM, LC3 validation, African case study or empirical calibration here.\nThe study tests traceability, release gates, uncertainty handling and known semantic\nblind spots; it does not establish design compliance or material superiority.\n"""
    (output / "REPORT.md").write_text(report)

    source_paths = sorted([
        *ROOT.glob("*.py"),
        *ROOT.glob("requirements*.txt"),
        *ROOT.glob("inputs/*"),
        *ROOT.glob("inputs/external/*"),
        *ROOT.glob("tests/*.py"),
    ])
    manifest = {
        "project_version": "0.2",
        "python": platform.python_version(),
        "packages": {k: importlib.metadata.version(k) for k in ["ifcopenshell", "numpy", "matplotlib"]},
        "seed": config["seed"],
        "draws": config["draws"],
        "input_model_sha256": hashlib.sha256(args.ifc.read_bytes()).hexdigest(),
        "source_hashes": {str(f.relative_to(ROOT)): hashlib.sha256(f.read_bytes()).hexdigest() for f in source_paths if f.is_file()},
        "output_hashes": {str(f.relative_to(output)): hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(output.rglob("*")) if f.is_file()},
    }
    write_json(output / "run_manifest.json", manifest)
    print(json.dumps(summary, indent=2))
    print(f"Results: {output}")


if __name__ == "__main__":
    main()
