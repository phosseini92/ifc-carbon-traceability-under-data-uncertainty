# Upgrade notes — v0.1 → v0.2

## Scientific upgrade

The central contribution is now the distinction between **structural integrity**,
**mapping integrity** and **semantic validity**. This makes the project more relevant to
trustworthy interoperability: data can be syntactically valid and internally traceable
while still being environmentally wrong because a semantically unsuitable source record
was selected.

## Technical upgrade

- mapping review contract with record ID + UUID + review basis;
- explicit mapping-tamper release gate;
- approved-but-wrong semantic blind-spot experiment;
- broader IFC material-assignment descriptor;
- independently authored IFC4 fixture for import/material-layer probing;
- uncertainty-family screening;
- 23-test target suite;
- stricter claims matrix and execution-status separation;
- archived v0.1 outputs separated from fresh v0.2 outputs.

## Still intentionally not added

- automatic fuzzy material matching;
- automatic semantic correctness claims;
- multilayer carbon allocation;
- full LCA;
- BEM;
- LC3 / earth material data;
- empirical calibration.

These remain future research steps because adding them without independent data and
validation would make the portfolio look broader but scientifically weaker.
