# Research claims matrix

Status as of the v1.0 execution audit (2026-09-06). See `AUDIT_REPORT_V1_0.md` and
`docs/v1_0_validation/` for the underlying execution evidence.

| Claim | Supported in v1.0? | Evidence / boundary |
|---|---|---|
| Can read and audit the controlled IFC4 wall/slab fixture | **Yes — executed and verified** | Strict supported contract; `outputs_v1_0_verified/audit.json`, `element_ledger.csv` |
| Can trace element GUID → material → KBOB record → quantity → screening GHG | **Yes — executed and verified** | Element ledger and source UUIDs; nominal total cross-checked by independent manual arithmetic |
| Detects missing material, unmapped material, duplicate GUID and large quantity mismatch | **Yes — executed and verified** | Controlled fault injection; all four cases blocked as specified (`experiment_results.csv`) |
| Detects mapping-file drift relative to a recorded review contract | **Yes — executed and verified** | `MAPPING_CONTRACT_MISMATCH` control; `mapping_tamper` case blocked |
| Proves a material mapping is semantically correct | **No** | Deliberately approved wrong mapping is designed to pass automated consistency checks; executed `plausible_wrong_mapping_approved` case passes release checks while changing the result by -34.83% |
| Supports arbitrary IFC exports | **No** | One independent external fixture is an interoperability probe, not general validation |
| Supports multilayer carbon allocation | **No** | Layer structures can be described, but main carbon release gate rejects them |
| Performs whole-building LCA | **No** | Selected material production-stage screening only |
| Provides empirical uncertainty | **No** | Triangular ranges are explicit teaching/research assumptions |
| Provides calibrated BEM or design-to-operation validation | **No** | Proposed future research step |
| Demonstrates reproducibility practices | **Yes — executed and verified, and strengthened** | Stable RNG keys, 24 tests, manifests, hashes, explicit source provenance; full 45-file output tree confirmed byte-identical across two independent runs (v0.1 only checked six numerical outputs) |
