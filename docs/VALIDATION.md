# Verification and validation record

## v0.1 archived execution evidence

The previous executed version is retained under `outputs_v0_1_verified/` and
`docs/v0_1_validation/`. It recorded:

- 15 passing unittest cases;
- IFC4 schema and EXPRESS checks with zero recorded findings for the controlled fixture;
- manual independent box-volume, mass and production-factor agreement;
- metre/mm geometry consistency, including explicit cubic-mm quantity handling;
- four structural corruption cases that blocked a complete total;
- one deliberately wrong mapping that passed the then-structural checks;
- byte-identical reproduction for six numerical outputs in two separate executions;
- source/input/output hashes in the run manifest.

Those checks are software/numerical evidence on controlled fixtures, not field validation,
LCA critical review or general IFC conformance certification.

## v1.0 execution evidence (2026-09-06)

The v0.2 feature set has been executed end-to-end in a clean Python 3.12.3 /
IfcOpenShell 0.8.5 environment (exact pins in `requirements-validation.txt`) and
released as v1.0. It recorded:

- 24 passing unittest cases (23 originally planned, plus one reproducibility
  regression test added during this audit);
- IFC4 schema and EXPRESS checks with zero recorded findings for the controlled fixture;
- manual independent volume/mass/GHG agreement, computed fresh from first principles
  outside the test suite;
- metre/mm geometry consistency, including explicit cubic-millimetre quantity handling;
- four structural corruption cases (`missing_material`, `unmapped_material`,
  `volume_x1000`, `duplicate_guid`) that blocked a complete total;
- a mapping-tamper case blocked by the material mapping review contract;
- a deliberately approved-but-wrong mapping that passed all automated checks and
  changed the unchecked result by -34.83%, demonstrating the intended semantic
  blind spot;
- Monte Carlo uncertainty propagation, convergence across 3 seeds x 5 sample sizes,
  and quantity/density/factor uncertainty-family screening, all inspected numerically
  and visually;
- an independent external IFC4 fixture inspected for import, geometry and
  material-layer structure without a carbon total being released;
- byte-identical reproduction across two fully independent full-pipeline
  executions, for all 45 output files, verified by SHA-256;
- source/input/output hashes in the run manifest.

One reproducibility bug was found and fixed during this execution: two
fault-injection fixtures were not byte-reproducible because of
ifcopenshell.api-generated random GUIDs and transient relationship-set ordering.
See `AUDIT_REPORT_V1_0.md` for the full root-cause analysis and before/after
evidence, and `docs/VALIDATION_STATUS_V0_2.md` for the completed release checklist.

Like the v0.1 record, this is software/numerical evidence on controlled fixtures —
not field validation, LCA critical review or general IFC conformance certification.
The mapping-review-contract and semantic-blind-spot findings above are, by design,
evidence of a limitation (what automated checks cannot establish), not a validated
carbon result for any real building.
