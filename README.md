# Traceable IFC-to-carbon workflows under data uncertainty

Research demonstrator | Version 1.0 (validated) | September 2026

A small, reproducible study of how quantity errors, missing information, mapping
configuration drift and semantic material-selection errors affect a BIM-linked
production-stage GHG screening calculation.

The project is independent work by Parisa Hosseini. It is not an EPFL,
REGEN4BE, KBOB or buildingSMART validation study.

**Version 1.0 status:** the v0.2 feature set described below (see "What changed
from v0.1") has now been executed end-to-end in a clean, pinned IfcOpenShell
0.8.5 / Python 3.12.3 environment, audited, and released. All 24 tests pass,
the manual benchmark, metre/mm, IFC re-import, mapping-contract and
fault-injection checks all hold, and two fully independent full-pipeline runs
(each regenerating the IFC fixture from scratch in a separate process) are
byte-identical for all 45 files produced, verified by SHA-256. One
reproducibility bug was found and fixed during this audit (see "What changed
from v0.2 to v1.0" below and `AUDIT_REPORT_V1_0.md`). See
`docs/VALIDATION_STATUS_V0_2.md` for the completed release checklist and
`docs/v1_0_validation/` and `outputs_v1_0_verified/` for the archived
execution evidence.

Note on portability: `external_ifc_check.json` records the resolved path of
the IFC file it inspected (`--ifc`, which defaults to a path under this
project's own directory). Two runs from the same checkout are therefore
byte-identical, as verified; a checkout at a different absolute install path
would legitimately produce a different string in that one field. This was
not itself exercised, since the audit did not run the project from two
different install locations.

## Research question

**Which data and mapping failures can be detected automatically in an IFC-to-carbon
workflow, which require an explicit review/provenance contract, and which semantic
errors can remain internally consistent while still changing the environmental result?**

The v0.2 upgrade, carried through unchanged into v1.0, separates three questions
that should not be conflated:

1. **Structural integrity** — is geometry, quantity, identity and material data present
   and internally consistent?
2. **Mapping integrity** — does the active material-to-database mapping match the
   recorded review contract and source UUID?
3. **Semantic validity** — is the selected environmental record substantively the
   correct product/technology/geography/boundary for the intended study?

The first two can be checked computationally in this demonstrator. The third cannot
be proven by software consistency alone.

## What changed from v0.1

- Added a hashed **material mapping review contract** that can block accidental or
  unreviewed mapping-file drift.
- Split the previous semantic-error case into (a) detectable mapping tamper and
  (b) an intentionally approved-but-wrong mapping that remains a true semantic blind spot.
- Added an independently authored IFC4 fixture from the buildingSMART-community
  IfcScript examples to test import, geometry and material-layer interpretation without
  pretending that it satisfies the main carbon accounting contract.
- Added broader material-assignment inspection for `IfcMaterialLayerSetUsage` while
  keeping the carbon release gate strict: layered assemblies are rejected until an
  explicit layer-quantity allocation method is implemented.
- Added uncertainty-family screening for quantity, density and production-factor
  assumptions separately, alongside the existing 10,000-draw analysis and convergence checks.
- Expanded the planned verification suite from 15 to 23 tests.
- Tightened project claims, provenance language and the distinction between
  reproducibility, mapping integrity and environmental validity.

## What changed from v0.2 to v1.0

- Executed the full v0.2 source tree end-to-end for the first time, in a clean
  Python 3.12.3 environment with the exact pinned packages from
  `requirements-validation.txt`.
- Found, during that execution audit, that two of the seven fault-injection
  fixtures (`missing_material.ifc`, `unmapped_material.ifc`) were not
  byte-reproducible: `ifcopenshell.api` material (un)assignment calls generate
  a fresh random GlobalId for newly created relationship entities and can
  leave SET-valued relationship attributes in a transient, process-dependent
  order. Fixed by extracting the existing fixture-stabilisation logic into
  `build_model.stabilize_ids()` and calling it from `run.py`'s
  `experiment_case()` as well. See `AUDIT_REPORT_V1_0.md` for the full
  before/after evidence.
- Added `test_24_experiment_case_bytes_are_reproducible`, a regression test
  covering all seven fault-injection cases, so a recurrence is caught inside
  the test suite rather than only as a hash mismatch in a later reproduction
  check. The verification suite is now 24 tests.
- Documented `one_at_a_time_sensitivity.csv`, an output that existed since
  v0.1 but was never described in `docs/METHODS.md`.
- Confirmed byte-for-byte reproducibility of every other output across two
  fully independent full-pipeline executions (separate processes, separate
  directory trees, freshly regenerated IFC fixture in both).

## Main workflow

1. Read IFC4 with IfcOpenShell.
2. Extract GUIDs, element classes, monolithic material assignments and declared `NetVolume`.
3. Independently calculate solid geometry volume.
4. Check duplicate IDs, supported classes, required quantities, units, mappings and
   geometry/quantity agreement.
5. Compare the active material mapping against a recorded source UUID/review contract.
6. Block the complete screening total if any release check fails.
7. Calculate selected-material production GHG: `volume × density × source factor`.
8. Propagate declared illustrative uncertainty with stable keyed random streams.
9. Run controlled fault injection and distinguish structural, mapping-integrity and
   semantic failure modes.
10. Record element-level evidence, source metadata, configuration and file hashes.

## Run

The delivered project targets Python 3.12 and the pinned packages in `requirements.txt`.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-validation.txt
python build_model.py
python -m unittest discover -s tests -v
python run.py --output outputs
python check_external_ifc.py --output outputs/external_ifc_check.json
python validate_ifc.py
```

Do not reuse a non-empty output folder. A fresh run should generate its own manifest.
The verified v0.1 outputs are archived under `outputs_v0_1_verified/` and the
verified v1.0 outputs under `outputs_v1_0_verified/`; both are reference records of
one specific past execution each and should not be overwritten by a new run, nor
described as evidence for a different version than the one that produced them.

## Controlled fixture and environmental data

The main authored IFC4 fixture is an intentionally simple shell: four clay-brick walls
and one unreinforced-concrete slab. It has no roof, openings, mortar, reinforcement,
finishes or services. It is a data-quality testbed, not a complete building design.

Three KBOB/ecobau 2022 v9.0 records are retained as an attributed excerpt. Concrete
and fired brick are used in the clean screening calculation; a light-earth-brick record
is used only for a deliberate wrong-mapping control. Source URL, workbook version,
row/column, UUID and source hash are recorded under `inputs/`.

KBOB source landing page:
https://www.kbob.admin.ch/fr/donnees-ecobilans-dans-la-construction

## External IFC fixture

`inputs/external/IfcScript_Slab.ifc` is an independently authored IFC4 example from
the public `buildingsmart-community/IfcScript` repository, originally produced with
GeometryGymIFC. It contains a material layer set and is used only to test that the
project can inspect a different authoring convention. It is **not** used to claim a
validated carbon result or general IFC compatibility.

Source:
https://github.com/buildingsmart-community/IfcScript/blob/master/Examples/Slab.ifc

## Supported carbon-release contract

- Exact `IfcWall` and `IfcSlab` classes.
- One monolithic `IfcMaterial` per element.
- Exactly one interpretable `NetVolume` per element.
- Positive closed geometry and explicit project units.
- Explicit material-to-source-record mapping.
- Active mapping must match the recorded review contract.
- Geometry and declared quantity must agree within the author-declared tolerance.

Layered assemblies are now *described* by the interoperability inspector but still
rejected by the carbon calculation until a defensible layer-quantity allocation method
is implemented. This is intentional.

## Boundaries and claims

The indicator is the published KBOB `Herstellung / Fabrication` GHG value for the
selected generic records. This is not a whole-building LCA and no EN 15804 A1-A3
equivalence is asserted. The Monte Carlo ranges are illustrative author assumptions,
not KBOB uncertainties or empirical confidence intervals.

The mapping review contract is a reproducibility and configuration-integrity control.
It does **not** establish semantic correctness. A wrong record can be made internally
consistent and still pass automated checks. Independent material/product/LCA review
is therefore a required next validation layer.

There is no calibrated BEM, sensor/occupant validation, LC3 case, African field study
or complete lifecycle assessment in v0.2/v1.0.

## Validation status in this package

The v0.1 core workflow was previously executed with 15 passing tests, schema checks,
manual arithmetic, metre/mm fixtures and byte-identical reproduction checks; those
records are preserved under `outputs_v0_1_verified/`.

The v0.2 feature set has now been executed end-to-end (2026-09-06, Python 3.12.3,
IfcOpenShell 0.8.5) and released as **v1.0**: 24/24 tests pass, the manual
benchmark and metre/mm checks agree exactly, IFC4 schema/EXPRESS validation
reports zero findings, all seven fault-injection cases behave as specified,
and two fully independent full-pipeline runs (fixture regenerated fresh each
time) are byte-identical across all 45 output files, verified by SHA-256. One
reproducibility bug was found and fixed in the process (see "What changed
from v0.2 to v1.0" above). Full evidence, including the found-and-fixed bug,
is in `AUDIT_REPORT_V1_0.md`, `docs/VALIDATION_STATUS_V0_2.md` (completed
checklist), `docs/v1_0_validation/` (raw logs) and `outputs_v1_0_verified/`
(archived numeric outputs).


## Development transparency

AI-assisted tools were used during parts of implementation and technical review.
They were used as supporting tools, not as substitutes for research decisions or validation.
The research question, methodological boundaries, implementation choices, validation
strategy, interpretation of results and final claims were defined and reviewed by the
author against executed evidence.
