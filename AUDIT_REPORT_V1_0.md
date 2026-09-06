# Execution and code audit report — v0.2 → v1.0

**Project:** Traceable IFC-to-carbon workflows under data uncertainty
**Author of the research:** Parisa Hosseini (independent work; not an EPFL,
REGEN4BE, KBOB or buildingSMART validation study)
**Technical audit assistance:** Claude (Anthropic AI) was used as a technical review assistant for reproducibility checks, consistency inspection and identification of potential implementation issues. Research framing, methodological decisions, implementation choices, validation criteria, interpretation of results and final claims were independently reviewed and verified by the author against executed evidence.
**Date:** 2026-09-06
**Environment:** clean virtual environment, Python 3.12.3, packages pinned per
`requirements-validation.txt` (ifcopenshell 0.8.5, numpy 2.5.2, matplotlib
3.11.1, pytest 9.1.1; full transitive closure in `requirements-v1_0-reproduced.txt`)

**Verdict: release criterion met. The project is promoted from v0.2
(source-complete / execution-pending) to v1.0 (executed and audited).** One
reproducibility bug was found during the audit and fixed; no scientific
claim in the project's own documentation was found to be false, and one
inaccurate claim written during an earlier draft of this audit's own
documentation was caught and corrected (see §5).

---

## 1. What this audit did, in order

1. Verified the integrity of the delivered package against `SHA256SUMS.txt`
   (63 files at the time of upload — all matched).
2. Built a clean Python 3.12.3 virtual environment and installed
   `requirements-validation.txt` with no other packages present.
3. Ran `build_model.py`, the full `tests/test_workflow.py` suite, `run.py`,
   `check_external_ifc.py` and `validate_ifc.py`, exactly as documented in
   `README.md`.
4. Independently recomputed the nominal carbon result from first principles
   (not by reading the test's own arithmetic) and compared it to the
   software's output.
5. Inspected every generated figure visually.
6. Ran the entire pipeline twice, independently, regenerating the IFC
   fixture from scratch each time, and compared every output file byte-for-
   byte by SHA-256.
7. Found a genuine reproducibility bug during step 6, diagnosed its root
   cause, fixed it, added a regression test, demonstrated the test fails
   without the fix and passes with it, and reran the entire suite above from
   scratch to confirm nothing else regressed.
8. Re-verified reproducibility (step 6) after the fix.
9. Updated the project's own documentation (`README.md`,
   `docs/VALIDATION_STATUS_V0_2.md`, `docs/VALIDATION.md`,
   `docs/RESEARCH_CLAIMS.md`, `docs/METHODS.md`, and the Persian-language
   docs) to state the actual, now-executed status, and archived the
   evidence under `docs/v1_0_validation/` and `outputs_v1_0_verified/`.

No step here added new scientific scope beyond what the v0.2 source already
specified. This is an execution and correctness audit of existing code, not
a redesign.

---

## 2. Package integrity

All 63 files listed in the delivered `SHA256SUMS.txt` matched their recorded
hashes (`sha256sum -c`: 63/63 OK, zero mismatches). The uploaded ZIP was not
corrupted or altered before this audit began.

---

## 3. Results, item by item

### 3.1 Manual carbon benchmark
Computed independently, outside the test suite, from the fixture's own
declared dimensions and the KBOB factors in `inputs/material_factors.csv`:

```
brick volume  = 2×(6.4×3×0.2) + 2×(4×3×0.2) = 12.48 m3
concrete vol. = 6.4×4.4×0.2                 = 5.632 m3
brick mass    = 12.48 × 900        = 11232.0 kg
concrete mass = 5.632 × 2300       = 12953.6 kg
brick GHG     = 11232.0 × 0.254    = 2852.928  kg CO2e
concrete GHG  = 12953.6 × 0.0887   = 1148.98432 kg CO2e
TOTAL         = 4001.91232 kg CO2e
```

`run.py`'s reported nominal total: **4001.9123200000013 kg CO2e** — matches to
full float precision. `tests/test_workflow.py::test_01` independently checks
the same identity to 8 decimal places; both agree.

### 3.2 Metre/mm consistency and IFC re-import
- `test_03` (metre vs. millimetre-unit fixture) and `test_04` (explicit
  cubic-millimetre `NetVolume` quantity) both pass.
- `test_02` (write → reopen → re-audit) passes; GUIDs and totals are
  unchanged across the round trip.
- Every element's `relative_quantity_error` in `element_ledger.csv` is
  exactly `0.0` — declared and geometry-engine volumes agree exactly for
  this fixture (well inside the 1% author-declared tolerance).

### 3.3 IFC4 schema/EXPRESS validation
`validate_ifc.py` reports **0 findings** on the controlled fixture.

### 3.4 Material-mapping contract and fault-injection experiments
All seven controlled cases behaved exactly as `docs/METHODS.md` §5 specifies:

| Case | Accepted? | Issue code(s) | Naive bias vs. clean |
|---|---|---|---|
| `complete` | ✅ yes | — | 0.00% |
| `missing_material` | ❌ no | `MISSING_MATERIAL` | −13.71% |
| `unmapped_material` | ❌ no | `UNMAPPED_MATERIAL` | −13.71% |
| `volume_x1000` | ❌ no | `QUANTITY_GEOMETRY_MISMATCH` | +13695.74% |
| `duplicate_guid` | ❌ no | `DUPLICATE_GUID` | 0.00% |
| `mapping_tamper` | ❌ no | `MAPPING_CONTRACT_MISMATCH` | −34.83% |
| `plausible_wrong_mapping_approved` | ✅ **yes** | — | **−34.83%** |

The last row is the project's central point: an internally consistent,
fully "approved" mapping can still be substantively wrong, and no automated
structural or mapping-integrity check catches it. This was verified to
behave exactly as designed, not merely asserted.

Note on `duplicate_guid`: in this fixture, sharing a GUID does not itself
inflate the naive total (both elements keep their own real volume and
material), so its "naive bias" is legitimately 0.00% — the case is caught
purely as an identity/traceability defect (`DUPLICATE_GUID`), not a quantity
defect. This matches the code's intent and is not an inconsistency.

### 3.5 Uncertainty, convergence, sensitivity
- Monte Carlo (10,000 draws, seed 20260905): mean 4000.91, median 4000.43,
  P05–P95 3577.04–4430.47 kg CO2e — consistent with the nominal value and
  the configured triangular ranges.
- Convergence checked at 1,000/2,500/5,000/10,000/25,000 draws across three
  seeds (20260905–20260907): means and P95 values stay within a few kg CO2e
  of each seed's own 25,000-draw reference, with no directional drift.
- Uncertainty-family screening (quantity-only, density-only, factor-only,
  all-families) shows factor uncertainty dominates the P05–P95 width
  (≈822 kg CO2e) over density (≈210) and quantity (≈50), consistent with the
  factor triangular range (0.80–1.20) being the widest of the three.
- `one_at_a_time_sensitivity.csv` was cross-checked analytically: for a
  linear model (`GHG = Σ volume × density × factor`), each row equals
  `nominal + record_contribution × (multiplier − 1)` exactly. Recomputed by
  hand for one row (concrete, density, low endpoint: `4001.9123 +
  1148.9843×(0.95−1) = 3944.4631`) and matched the CSV to reported precision.
  This output existed since v0.1 but was undocumented; `docs/METHODS.md` §6
  now describes it.

### 3.6 External IFC interoperability probe
`check_external_ifc.py` opens `inputs/external/IfcScript_Slab.ifc` (an
independently authored, third-party IFC4 fixture), correctly identifies its
`IfcMaterialLayerSetUsage` material convention, its millimetre length unit
(scale 0.001 to metres), and computes a geometry volume — without releasing
a carbon total, per the project's own documented scope. `test_22` checks the
same behaviour programmatically; both agree.

### 3.7 Figures
All three generated figures (`model_and_carbon.png`,
`uncertainty_and_data_quality.png`, `uncertainty_family_screening.png`) were
inspected visually. All render correctly: the 3D shell geometry matches the
five-element fixture, the element-level bar chart matches
`element_ledger.csv`, the Monte Carlo histogram and its P05–P95 markers
match `summary.json`, and the fault-injection bias chart matches
`experiment_results.csv`.

---

## 4. Bug found and fixed: experiment fixtures were not byte-reproducible

### 4.1 How it was found
While performing the reproducibility check requested for this audit (run the
full pipeline twice, compare every output file by hash), two of the seven
files under `experiments/` — `missing_material.ifc` and
`unmapped_material.ifc` — differed between the two runs.

### 4.2 Root cause
`ifcopenshell.api`'s material (un)assignment calls, used only in
`run.experiment_case()` for these two cases:

- assign a **fresh, randomly generated GlobalId** to any newly created
  `IfcRoot`-derived relationship entity (confirmed: calling
  `experiment_case()` twice **in the same process** produced two different
  GlobalIds for the same new `IfcRelAssociatesMaterial` entity), and
- can leave SET-valued relationship attributes (e.g. `RelatedObjects`) in an
  order that depends on transient Python object identity rather than file
  content (confirmed: the surviving 3-member `RelatedObjects` tuple after
  `missing_material`'s unassignment was reordered between two same-process
  calls).

Neither affects IFC semantics (a GlobalId only needs to be a valid
non-repeating identifier; a STEP SET is unordered) and neither changed any
audited value, issue code, or test assertion — every numeric and pass/fail
result was identical between the two runs even before the fix. The defect
was purely in byte-level reproducibility of two derived fixture files,
which this project's own manifest/hash-based reproducibility claim depends
on.

The project's own `build_model.py` already solved exactly this class of
problem for the base fixture, with a two-part stabilization step run once at
the end of `create_model()`: deterministically re-deriving GlobalIds for all
non-core `IfcRoot` entities from their (stable) STEP id, and re-sorting
SET-valued relationship attributes by STEP id. `run.py`'s
`experiment_case()` mutates a clone of that already-stabilized model but
never re-ran this step, so any *new* entity or *modified* relationship it
introduced was left with these problems.

### 4.3 Fix
- Extracted the stabilization logic out of `build_model.create_model()` into
  a reusable function, `build_model.stabilize_ids(model, exempt_classes=...)`.
- Confirmed this refactor is behaviour-preserving: `build_model.py`'s output
  is byte-identical before and after the refactor.
- Called `stabilize_ids(model)` at the end of `run.experiment_case()`, after
  all case-specific mutations, before the model is returned/serialized. The
  same excluded-classes set (`IfcWall`, `IfcSlab`, etc.) is reused, so the
  `duplicate_guid` case's deliberately duplicated wall GUID is left
  untouched, as required for that test to remain meaningful.

### 4.4 Regression test and before/after evidence
Added `tests/test_workflow.py::test_24_experiment_case_bytes_are_reproducible`,
which calls `experiment_case()` twice for all seven cases and asserts
byte-identical serialization.

**Before the fix** (fix temporarily reverted to confirm the test actually
catches the bug):

```
test_24_experiment_case_bytes_are_reproducible ...
  ... (name='missing_material') ... FAIL
  ... (name='unmapped_material') ... FAIL
FAILED (failures=2)
```

Diffs confirmed exactly the predicted symptoms: a reordered `RelatedObjects`
tuple for `missing_material`, and a different GlobalId string for
`unmapped_material`'s new relationship entity.

**After the fix restored:**

```
Ran 24 tests in 0.592s
OK
```

### 4.5 Final reproducibility verification (post-fix)
Two fully independent executions of the entire pipeline (`build_model.py` →
tests → `run.py` → `check_external_ifc.py`), each in a separate process,
each regenerating the IFC fixture from scratch, writing to separate output
directories:

- **45 of 45 output files byte-identical** (verified by SHA-256), with no
  exceptions. This includes all seven `experiments/*.ifc` fixtures, all
  CSVs, JSONs, the run manifest, and `external_ifc_check.json`.
- This is a strictly stronger reproducibility guarantee than v0.1
  established (six numerical outputs only).
- Caveat, disclosed but not itself exercised: `external_ifc_check.json`
  records the resolved path of the `--ifc` argument it inspected, which
  defaults to a path under the project's own directory. Two runs from the
  *same checkout* are byte-identical, as verified above; a checkout at a
  *different absolute install path* would legitimately produce a different
  string in that one field. This audit did not run the project from two
  different install locations, so this remains a documented design note,
  not a tested claim.

---

## 5. A note on this audit's own accuracy

An earlier draft of this audit's supporting documentation (written before
the full 45-file comparison in §4.5 was completed) stated that the two
independent runs were "byte-identical except for one field that legitimately
records an absolute filesystem path" — implying that exception had actually
been observed. It had not: within a single checkout, all 45 files matched
exactly, with no exception encountered in practice. That claim has been
corrected in `README.md`, `docs/VALIDATION_STATUS_V0_2.md`, and here, to
report only what was actually observed (45/45 identical) plus the disclosed,
untested caveat above. This correction is recorded here in the interest of
holding this audit itself to the same standard it was asked to apply to the
underlying project: report only executed evidence, and do not let a
plausible-sounding caveat stand in for a claim that was actually tested.

---

## 6. Remaining limitations (unchanged by this audit — by design, not oversight)

Executing and auditing the code does not, and cannot, resolve the following,
which the project's own documentation already states as intentional scope
boundaries. This audit did not attempt to change the project's scientific
scope, only to verify that the code does what it claims within that scope:

- **Semantic correctness of the material mapping is not established.** The
  `plausible_wrong_mapping_approved` case is deliberately designed to pass
  every automated check while being substantively wrong — this is the
  project's central research point, not a gap in the audit.
- No claim of general IFC interoperability: one independent external fixture
  is a probe, not a validation suite.
- No multilayer carbon allocation, no whole-building LCA, no EN 15804 A1-A3
  equivalence claim.
- Uncertainty ranges are illustrative author assumptions, not KBOB or
  empirically derived uncertainty.
- No BEM, sensor/occupant validation, LC3 or earth-construction case study.
- `one_at_a_time_sensitivity.csv` covers density and factor only, not
  quantity (by design — quantity uncertainty is per-element and better
  suited to the Monte Carlo/family-screening analysis already provided).

---

## 7. Files changed by this audit

- `build_model.py` — extracted `stabilize_ids()` as a reusable function
  (behaviour-preserving refactor, verified byte-identical output).
- `run.py` — imports and calls `stabilize_ids()` in `experiment_case()`
  (the actual bug fix).
- `tests/test_workflow.py` — added `test_24_experiment_case_bytes_are_reproducible`.
- `requirements-v1_0-reproduced.txt` — new, full pinned environment actually
  used for this audit (identical to `requirements-v0_1-reproduced.txt`).
- `docs/v1_0_validation/` — new, archived test log, schema-validation
  record, and reproduction-check record for this execution.
- `outputs_v1_0_verified/` — new, archived canonical v1.0 output tree.
- `README.md`, `docs/VALIDATION_STATUS_V0_2.md`, `docs/VALIDATION.md`,
  `docs/RESEARCH_CLAIMS.md`, `docs/METHODS.md`, `START_HERE_FA.md`,
  `docs/PROJECT_BRIEF_FA.md`, `docs/LEARNING_GUIDE_FA.md` — updated to state
  the actual executed/audited status in place of "execution-pending"
  language, and to document the bug found and fixed.
- `SHA256SUMS.txt` — regenerated for the final v1.0 file tree.

No change was made to the project's research question, scope, accounting
formulas, uncertainty model, mapping-contract logic, or fault-injection
design. The one behavioural change (`stabilize_ids()` in `experiment_case()`)
affects only the byte-level serialization of derived fixture files, not any
audited value.

---

## 8. Verified headline numbers (for quick reference)

- Nominal screening total: **4001.9123200000013 kg CO2e** (manual benchmark
  agrees to full float precision).
- Monte Carlo (10,000 draws): mean 4000.91, median 4000.43, P05–P95
  3577.04–4430.47 kg CO2e.
- Tests: **24/24 pass** (23 original + 1 added by this audit).
- Schema/EXPRESS findings: **0**.
- Fault-injection cases behaving as specified: **7/7**.
- Output files byte-identical across two independent full-pipeline runs:
  **45/45**.
