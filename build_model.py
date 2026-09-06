"""Create the openly documented controlled IFC4 fixture, in metres or mm."""
from pathlib import Path
import argparse
import uuid
import numpy as np
import ifcopenshell
import ifcopenshell.api as api


ELEMENTS = [
    # name, class, length, height, thickness, x, y, z, angle, material
    ("South wall", "IfcWall", 6.4, 3., .2, 0., 0., .2, 0., "Clay brick (KBOB generic)"),
    ("North wall", "IfcWall", 6.4, 3., .2, 0., 4.2, .2, 0., "Clay brick (KBOB generic)"),
    ("West wall", "IfcWall", 4., 3., .2, .2, .2, .2, 90., "Clay brick (KBOB generic)"),
    ("East wall", "IfcWall", 4., 3., .2, 6.4, .2, .2, 90., "Clay brick (KBOB generic)"),
    ("Floor slab", "IfcSlab", 6.4, .2, 4.4, 0., 0., 0., 0., "Concrete (unreinforced, KBOB generic)"),
]


STABLE_ID_EXEMPT_CLASSES = {"IfcProject", "IfcSite", "IfcBuilding", "IfcBuildingStorey", "IfcWall", "IfcSlab"}


def stabilize_ids(model, exempt_classes=STABLE_ID_EXEMPT_CLASSES):
    """Make GlobalIds and SET-valued relationship attributes reproducible.

    IfcOpenShell's higher-level ``ifcopenshell.api`` calls (e.g.
    ``material.assign_material``, ``material.unassign_material``) generate a
    fresh random GlobalId for any newly created IfcRoot entity, and can leave
    SET-typed relationship attributes such as ``RelatedObjects`` in an order
    that depends on transient Python object identity rather than on file
    content. Both are irrelevant to IFC data semantics (a STEP SET is
    unordered; a GlobalId only has to be a valid non-repeating identifier),
    but both break byte-for-byte reproducibility, which this project's
    manifest/hash-based reproducibility claim depends on. This function
    re-derives both deterministically from each entity's STEP id, which is
    itself stable across runs of the same explicit sequence of API calls.
    Excluded classes keep whatever GlobalId the caller already assigned
    (e.g. the human-readable-name-derived GUIDs on the core fixture
    entities, or a deliberately duplicated GUID in a fault-injection case).
    Must be called once, after all structural edits, immediately before the
    model is serialised or hashed.
    """
    for e in model.by_type("IfcRoot"):
        if e.is_a() not in exempt_classes:
            e.GlobalId = ifcopenshell.guid.compress(uuid.uuid5(uuid.NAMESPACE_URL, f"epfl-demo/{e.is_a()}/{e.id()}").hex)
    for cls, attribute in [("IfcUnitAssignment", "Units"), ("IfcRelAggregates", "RelatedObjects"),
                           ("IfcRelContainedInSpatialStructure", "RelatedElements"),
                           ("IfcRelAssociatesMaterial", "RelatedObjects")]:
        for e in model.by_type(cls):
            setattr(e, attribute, tuple(sorted(getattr(e, attribute), key=lambda x: x.id())))


def create_model(path, millimetres=False):
    model = api.run("project.create_file", version="IFC4")
    def entity(cls, name):
        e = api.run("root.create_entity", model, ifc_class=cls, name=name)
        e.GlobalId = ifcopenshell.guid.compress(uuid.uuid5(uuid.NAMESPACE_URL, "epfl-demo/" + name).hex)
        return e
    project = entity("IfcProject", "Traceable IFC-to-carbon controlled testbed")
    units = [api.run("unit.add_si_unit", model, unit_type="LENGTHUNIT", prefix="MILLI" if millimetres else None),
             api.run("unit.add_si_unit", model, unit_type="AREAUNIT"),
             api.run("unit.add_si_unit", model, unit_type="VOLUMEUNIT")]
    api.run("unit.assign_unit", model, units=units)
    context = api.run("context.add_context", model, context_type="Model")
    body = api.run("context.add_context", model, context_type="Model", context_identifier="Body", target_view="MODEL_VIEW", parent=context)
    site = entity("IfcSite", "Controlled site - no geographic calibration")
    building = entity("IfcBuilding", "Single-room shell - incomplete building")
    storey = entity("IfcBuildingStorey", "Ground floor")
    for parent, child in [(project, site), (site, building), (building, storey)]:
        api.run("aggregate.assign_object", model, relating_object=parent, products=[child])
    materials = {}
    for name, cls, length, height, thick, x, y, z, angle, material in ELEMENTS:
        e = entity(cls, name)
        api.run("spatial.assign_container", model, products=[e], relating_structure=storey)
        representation = api.run("geometry.add_wall_representation", model, context=body, length=length, height=height, thickness=thick)
        api.run("geometry.assign_representation", model, product=e, representation=representation)
        a = np.deg2rad(angle)
        matrix = np.eye(4)
        matrix[:3, :3] = [[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]]
        matrix[:3, 3] = [x, y, z]
        api.run("geometry.edit_object_placement", model, product=e, matrix=matrix, is_si=True)
        if material not in materials:
            materials[material] = api.run("material.add_material", model, name=material)
        api.run("material.assign_material", model, products=[e], type="IfcMaterial", material=materials[material])
        qto = api.run("pset.add_qto", model, product=e, name="Qto_WallBaseQuantities" if cls == "IfcWall" else "Qto_SlabBaseQuantities")
        # Project volume unit is explicitly m3 in both fixtures.
        api.run("pset.edit_qto", model, qto=qto, properties={"NetVolume": length * height * thick})
    # Stable fixture byte content, including IDs created by the API.
    stabilize_ids(model)
    model.header.file_name.time_stamp = "2026-09-05T00:00:00"
    model.header.file_name.name = "controlled_shell_mm.ifc" if millimetres else "controlled_shell.ifc"
    model.header.file_name.author = ("Parisa Hosseini",)
    model.header.file_name.organization = ("Independent research demonstrator - not an EPFL model",)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    model.write(str(path))
    return model


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "inputs/controlled_shell.ifc")
    parser.add_argument("--millimetres", action="store_true")
    args = parser.parse_args()
    create_model(args.output, args.millimetres)
    print(args.output)
