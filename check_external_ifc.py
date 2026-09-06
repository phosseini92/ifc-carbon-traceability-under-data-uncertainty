"""Inspect an independently authored IFC fixture without forcing a carbon calculation."""
import argparse
import json
from pathlib import Path
import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.shape
import ifcopenshell.util.unit
from workflow import material_assignment_descriptor, write_json

ROOT = Path(__file__).parent


def inspect(path):
    model = ifcopenshell.open(str(path))
    settings = ifcopenshell.geom.settings()
    elements = []
    for e in sorted(model.by_type("IfcBuildingElement"), key=lambda x: (x.GlobalId, x.id())):
        item = {
            "guid": e.GlobalId,
            "ifc_class": e.is_a(),
            "name": e.Name,
            "material": material_assignment_descriptor(e),
            "geometry_volume_m3": None,
            "geometry_error": None,
        }
        try:
            shape = ifcopenshell.geom.create_shape(settings, e)
            item["geometry_volume_m3"] = float(ifcopenshell.util.shape.get_volume(shape.geometry))
        except Exception as exc:
            item["geometry_error"] = str(exc)
        elements.append(item)
    header = model.header.file_name
    return {
        "file": str(path),
        "schema": model.schema,
        "preprocessor_version": str(header.preprocessor_version),
        "originating_system": str(header.originating_system),
        "length_unit_scale_to_m": ifcopenshell.util.unit.calculate_unit_scale(model, "LENGTHUNIT"),
        "element_count": len(elements),
        "elements": elements,
        "interpretation": "Independent-authoring import/material/geometry check only. No carbon total is released because this external fixture does not meet the strict monolithic quantity contract of the main audit.",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ifc", type=Path, default=ROOT / "inputs/external/IfcScript_Slab.ifc")
    p.add_argument("--output", type=Path, default=ROOT / "outputs/external_ifc_check.json")
    args = p.parse_args()
    result = inspect(args.ifc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
