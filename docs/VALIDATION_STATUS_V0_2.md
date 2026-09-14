# Validation status — v0.2

## Update 2026-09-06: release criterion met, promoted to v1.0

Every step in "Release criterion before portfolio use" below has now been executed and
evidenced. Environment: Python 3.12.3, ifcopenshell 0.8.5, numpy 2.5.2, matplotlib
3.11.1, pytest 9.1.1 (exact versions pinned in `requirements-validation.txt`, installed
in a clean virtual environment with no other packages present; full transitive
dependency list in `requirements-v1_0-reproduced.txt`).

- 24/24 tests pass (23 planned + 1 added during this audit; log in
  `docs/v1_0_validation/test_results.txt`).
- `python run.py --output outputs` completes; nominal total 4001.912320 kg CO2e,
  matching an independent manual recomputation (done outside the test suite, from
  first principles) to full float precision.
- `python check_external_ifc.py` and IFC4 schema/EXPRESS validation both run;
  schema validation reports 0 findings (`docs/v1_0_validation/ifc_schema_validation.json`).
- All three figures inspected visually; all render correctly and match the
  underlying numeric data.
- The full pipeline (fixture build, tests, run, external check) was executed twice,
  independently: separate processes, separate output directories, the IFC fixture
  regenerated from scratch each time. All 45 files produced by the two runs are
  byte-identical, verified by SHA-256
  (`docs/v1_0_validation/reproduction_check.json`). This was tested from a single
  checkout; a checkout at a different absolute install path would legitimately
  change one path string recorded in `external_ifc_check.json`, but that scenario
  was not itself exercised.
- One reproducibility bug was found in this process and fixed: two derived
  fault-injection fixtures (`missing_material.ifc`, `unmapped_material.ifc`) were not
  byte-reproducible, even within a single process, because of
  ifcopenshell.api-generated random GUIDs and transient SET serialisation order on
  newly created relationship entities. Full root-cause analysis, fix and before/after
  evidence are in `AUDIT_REPORT_V1_0.md`.

This package is therefore released as **v1.0**, built directly on the v0.2 feature set
below with no scientific scope added. The "What changed in v0.2" and "Release
criterion" sections below are preserved as the historical pre-execution record.

## What is already evidenced

The archived v0.1 execution record contains:

- 15 passing unittest cases;
- independent manual volume/mass/GHG agreement;
- metre and millimetre fixtures with consistent results;
- IFC4 schema/EXPRESS check record;
- four injected structural errors that blocked a complete total;
- one deliberately wrong semantic mapping that changed the result;
- repeated-run identity for six numerical outputs;
- source/input/output hashes in a run manifest.

These records are preserved in `outputs_v0_1_verified/` and `docs/`.

## What changed in v0.2 and therefore requires a fresh run

- material mapping review contract and mapping-tamper gate;
- approved-but-wrong semantic control;
- external independently authored IFC inspection;
- layer-assignment descriptor;
- uncertainty-family screening;
- expanded 23-test suite;
- updated reports and manifest content.

The current execution environment used to package this upgrade did not contain
IfcOpenShell 0.8.5 and did not have network access to install it. Therefore these new
v0.2 behaviours have **not** been represented as executed evidence here. Python source
files were syntax-checked only.

## Release criterion before portfolio use

Before any v0.2 result is placed in an EPFL representative work sample:

1. create a clean Python 3.12 environment;
2. install `requirements-validation.txt`;
3. run all 23 tests and save the log;
4. run `python run.py --output outputs`;
5. run `python check_external_ifc.py --output outputs/external_ifc_check.json`;
6. run schema validation;
7. inspect all generated figures;
8. reproduce the run in a second clean output directory;
9. compare key numeric outputs and hashes;
10. update this file with actual run date, package versions and pass/fail evidence.

Until those steps are complete, call v0.2 **source-complete / execution-pending**, not
"validated" or "verified".
