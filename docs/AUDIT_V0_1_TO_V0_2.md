# Audit: v0.1 strengths, weaknesses and v0.2 response

## Strong foundations already present in v0.1

- explicit research question and narrow scope;
- element-level GUID/material/source/quantity ledger;
- independent geometry-versus-quantity check;
- transparent KBOB source provenance;
- controlled fault injection rather than only a clean demonstration;
- Monte Carlo with explicit non-empirical uncertainty boundaries;
- stable keyed random streams, convergence checks and manifests;
- manual arithmetic and unit-system checks;
- unusually clear limitations and non-claims.

## Main weaknesses for an EPFL representative-work trajectory

### 1. Structural checks and semantic validity were not sufficiently separated
The wrong-mapping experiment showed the issue, but v0.1 still treated the mapping file
as one undifferentiated configuration layer. This made it harder to demonstrate exactly
what provenance control can and cannot solve.

**v0.2 response:** add a mapping review contract and split accidental mapping drift from
an internally consistent but semantically wrong approved mapping.

### 2. The main fixture was authored by the same code that read it
This is a useful unit/integration fixture but weak evidence for interoperability across
independent authoring conventions.

**v0.2 response:** add a third-party IFC4 layer-set fixture and a separate inspector.
The project still avoids claiming general IFC support.

### 3. Layered material structures were only rejected
The rejection was scientifically honest, but the project did not yet show that it could
at least recognise and describe a different IFC material representation.

**v0.2 response:** add a broad material-assignment descriptor while preserving the strict
carbon release gate until layer allocation is explicitly defined.

### 4. Uncertainty output was strong but not decomposed by assumption family
The combined Monte Carlo result did not show which assumed uncertainty families were
most influential in widening the screening output.

**v0.2 response:** add isolated quantity/density/factor family screening. It is labelled
as descriptive screening, not formal variance decomposition.

### 5. Portfolio framing still sounded too educational
The method was better than the label suggested.

**v0.2 response:** reframe as a controlled research demonstrator, retain a separate AI
assistance disclosure, and strengthen research-claim boundaries.

## Remaining highest-value upgrades after v0.2 execution

1. a real IFC export from a current authoring tool, with manual quantity takeoff;
2. explicit multilayer quantity allocation with independent fixtures;
3. independent LCA/material review of source applicability;
4. documented source/model uncertainty rather than illustrative ranges;
5. only then, a separately validated BEM coupling.

These upgrades are more valuable than adding broader but weakly verified features.
