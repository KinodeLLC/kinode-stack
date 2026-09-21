# Kinode

A family of programming languages and a runtime for code written by agents
rather than by people.

The design target is not "a language a model finds easy to write" — models
already write Python and TypeScript fluently, and syntax was never the
bottleneck. The target is:

> a language and runtime where correctness, blast radius and intent-conformance
> can be established **without a human reading the implementation**.

Everything here follows from that.

## Status

Working software, version 0.1.0. Fourteen test suites, all passing:

```
$ python kinode-stack/tests/run_all.py
  pass  canon/smoke_frontend       lexer, parser, canonical form, hashing
  pass  canon/smoke_checker        types, effects, exhaustiveness
  pass  canon/smoke_interp         evaluation, contracts, budgets
  pass  canon/smoke_ledger         journal, capabilities, replay, shadow
  pass  canon/smoke_verify         verification, differential, promotion gate
  pass  canon/smoke_atlas          graph queries, projections, transactions
  pass  canon/smoke_protocol       the agent interface
  pass  intent/smoke_intent        specifications and drift detection
  pass  verdict/smoke_verdict      decisions and reason trees
  pass  loom/smoke_loom            workflows, compensation, resumption
  pass  weft/smoke_weft            schemas, migrations, lineage
  pass  tract/smoke_tract          derived infrastructure
  pass  rune/smoke_rune            governance policy
  pass  kinode-stack/integration   all seven languages end to end

14/14 suites passed in 1.8s
```

No dependencies beyond Python 3.11+. The Anthropic SDK is optional and only
needed for live model calls.

## The languages

Seven surface languages over one shared core. Each domain gets syntax tuned to
how that domain actually thinks; all of them lower to the same intermediate
representation, so there is one type system, one verifier, one runtime, one
audit trail and one blast-radius analysis across all of them.

| Language | Extension | Purpose |
| --- | --- | --- |
| [Intent](../intent) | `.intent` | Specifications whose scenarios are executable and whose traces are pinned to content hashes |
| [Canon](../canon) | `.canon` | The core: contracts, capability-typed effects, content-addressed definitions |
| [Loom](../loom) | `.loom` | Durable workflows with compensation and journal-based resumption |
| [Verdict](../verdict) | `.verdict` | Regulated decisions that cannot compile unless they explain themselves |
| [Weft](../weft) | `.weft` | Schemas, derived migrations with round-trip proofs, data lineage |
| [Tract](../tract) | `.tract` | Infrastructure derived from the program's capability footprint |
| [Rune](../rune) | `.rune` | Governance policy, compiled to capability grants and promotion authorisations |

## What the design actually buys

### Effects are capabilities, and they do not propagate silently

A function declares every effect it performs. Calling a function that performs
an effect requires the caller to declare it too. There is no inference, because
an inferred footprint widens silently when a body changes.

```canon
fn persist(o: Order) -> Unit
  intent "Write an order to storage."
  uses store.write
{
  store.write(o.id, o.customer.id)
}
```

Miss the declaration and you get a diagnostic with a repair attached, not a
runtime surprise:

```
error[CANON-E0401]: effect 'store.write' is performed but not declared
  operation: store.write
  fix: declare the effect on 'persist' `uses store.write`
```

The consequence is that the capability footprint of any call graph is a
computed fact:

```
$ canon atlas caps originate examples/lending
lending.origination.originate
  declared:   bureau.pull, ledger.append, ledger.commit, ledger.reverse,
              notify.email, workflow.checkpoint, workflow.compensated
  transitive: (the same set)
```

### Definitions are content-addressed

Every definition is identified by the hash of its normalised AST. Local
variable names are erased by binding depth and independent contract clauses are
sorted, so:

- renaming a local **does not** change the hash — a rename is a zero-risk edit
- reordering `requires` / `ensures` / `uses` does not change the hash
- reformatting does not change the hash
- editing a dependency changes the dependent's *deep* hash but not its *local*
  hash, which is how "what actually changed" is distinguished from
  "what moved because something under it moved"

### Verification comes from contracts, not from reading code

```canon
fn apply_discount(total: Int, percent: Int) -> Int
  requires percent >= 0
  requires percent <= 100
  ensures result >= 0
  ensures result <= total
  law never_negative
```

The verifier generates inputs from the parameter types, discards those failing
the preconditions, checks the postconditions and laws, and shrinks any failure
to a minimal case:

```
FAIL billing.overcharge  0/38 runs
     postcondition: postcondition does not hold
     input: (0, 1)
```

Generation is seeded, so a failure reproduces exactly from the seed alone.

### Nothing is partial

There is no `/` operator, because division is the one partial arithmetic
operation:

```
error[CANON-E0301]: there is no `/` operator in Canon
  use_instead: Int.div
  try: use Int.div, which returns Option and cannot fault `Int.div(a, b)`
  note: Making it return Option keeps every expression total, so no generated
        program can fault on a zero divisor.
```

Recursion requires a `decreases` measure the runtime checks. Every match must
be exhaustive. Every function runs under a step, io, token and spend budget.
The result is that unreviewed agent-authored code can be executed safely.

### The model is a language primitive

```canon
fn assess(t: Ticket) -> Assessment
  uses model.infer, model.judge
  ensures result.summary != ""
  cost tokens 4000, io 2
{
  ask Assessment from claude.opus {
    system "Assess the urgency of this support ticket."
    input body: t.body
    grounded_in t.body
    retries 3 on contract_violation, type_error, grounding_failure
    max_tokens 512
  }
}
```

`ask` is an expression, not a library call, which buys four things:

1. **Typed output.** A JSON Schema is derived from `Assessment` and constrains
   the response. The result is a typed value, not a string to parse.
2. **Contract-checked.** The enclosing `ensures` clauses are enforced on the
   model's output. A violation is retried with the failure fed back as repair
   context, then reported as a structured fault.
3. **Capability-scoped and journaled.** `model.infer` must be granted. Calls
   are budgeted in tokens and money and recorded, so a run replays exactly.
4. **Model capabilities are checked at compile time.** Current Claude models
   reject `temperature` with a 400 rather than ignoring it, so Canon rejects
   the clause at check time:

```
error[CANON-E0301]: claude.opus does not accept a temperature setting
  note: This model rejects the parameter outright rather than ignoring it, so
        the clause would fail every call at runtime.
```

### Effects are journaled, so replay is exact

Every effect lands in a hash-chained journal. That single mechanism gives:

- **Exact replay** — a recorded run re-executes with identical results and
  zero external calls
- **Shadow deployment** — a changed version runs against recorded production
  traffic, answering effects from the recording, so it touches nothing while
  its divergences are collected
- **Workflow resumption** — Loom needs no state store; a crashed workflow
  resumes by replaying its journal
- **Tamper evidence** — altering a recorded argument breaks the chain at a
  specific sequence number

### The promotion gate decides, and says why

```
decision: BLOCK
  [block] CANON-E0905: lending.origination.originate was modified but is
          outside the authorised scope
```

The gate compares a change against a stated authorisation: which definitions
it may touch, which capabilities it may reach, how large a blast radius is
acceptable, how sensitive the data may be, and whether behaviour may change at
all. Capability deltas are computed **per definition**, so a function newly
reaching a capability that another function already had is still reported as a
privilege increase.

## A worked example

[`examples/lending`](examples/lending) is one system written across all seven
languages — 7 files, 43 definitions:

```
$ canon check examples/lending
ok: 7 files, 43 definitions, 7 warnings
```

They form one graph. Editing a single Canon helper reaches definitions in
Verdict, Loom and Intent:

```
$ canon atlas blast affordability_ratio examples/lending
lending.affordability_ratio #ecpsvedi
  11 transitive dependents
  capabilities: bureau.pull, ledger.append, notify.email,
                workflow.checkpoint, workflow.compensated
  data: personal, pseudonymous
```

The integration suite drives the whole path an agent-authored change would
take. Some things it demonstrates:

- **A policy that denies money stops a workflow at the ledger.** The
  underwriting agent may pull a credit file but not book a loan; the workflow
  runs until `ledger.append` and is refused at the boundary.
- **A two-phase booking reverses correctly.** When settlement fails, the staged
  ledger entry is reversed and the customer is *not* notified about a loan that
  was rolled back.
- **An interrupted origination resumes without re-billing the bureau.** Replay
  produces an identical offer with zero external calls.
- **A behaviour-preserving edit still reports its goals as stale.** Every
  scenario still passes, but six goal traces went stale because the hash of the
  definition they were accepted against changed. A test suite cannot catch this.
- **The same edit is judged differently by two policies.** Adding a schema field
  escalates under the data agent's policy and is blocked under the underwriting
  agent's.

## The agent interface

Agents drive a JSON-RPC interface over stdin/stdout rather than files and grep:

```json
{"method": "atlas.view", "params": {"focus": "submit", "budget": 4000}}
{"method": "edit.propose", "params": {"changes": {"orders.canon": "..."}}}
{"method": "gate.evaluate", "params": {"proposal": "prop-1"}}
{"method": "edit.commit", "params": {"proposal": "prop-1", "write": true}}
```

Three things this fixes:

- `atlas.view` returns a projection sized to a token budget — the focus
  definition in full, its callees as contracts, its callers as signatures — and
  **reports what it omitted** rather than truncating silently.
- Edits are transactional. A proposal is parsed, checked and diffed without
  being applied. A failed edit leaves nothing behind.
- There is no method that writes unchecked code.

## Getting started

```sh
# From the workspace root
export PYTHONPATH=canon/src:intent/src:loom/src:verdict/src:weft/src:tract/src:rune/src

python -m canon.cli check  kinode-stack/examples/lending
python -m canon.cli test   kinode-stack/examples/lending
python -m canon.cli verify kinode-stack/examples/lending --runs 40
python -m canon.cli atlas blast affordability_ratio kinode-stack/examples/lending
python -m canon.cli serve  kinode-stack/examples/lending      # agent interface
```

Or install each package:

```sh
pip install -e canon -e intent -e loom -e verdict -e weft -e tract -e rune
canon check kinode-stack/examples/lending
```

## Documentation

| Document | Contents |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | How the pieces fit, and why each one exists |
| [docs/languages.md](docs/languages.md) | All seven languages with worked examples |
| [docs/business-case.md](docs/business-case.md) | Who buys this, how it is priced, why it is defensible |
| [docs/diagnostics.md](docs/diagnostics.md) | Every diagnostic code and what it means |

## Repository layout

Each language is its own repository, versioned independently under SemVer,
with its own changelog and tests.

```
kinode/
  canon/          core language, runtime, verifier, Atlas, CLI, agent interface
  intent/         specification layer
  loom/           durable workflows
  verdict/        decision rules
  weft/           schemas and migrations
  tract/          infrastructure
  rune/           governance policy
  kinode-stack/   documentation, cross-language examples, integration tests
```

## Licence

Apache-2.0. Copyright Kinode.
