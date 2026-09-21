# Architecture

How the pieces fit together, and why each one is shaped the way it is.

## The premise

The usual framing of AI-native programming is "a language a model can write
easily". That framing is wrong, because models already write Python and
TypeScript fluently. Syntax was never the bottleneck.

The actual bottleneck is on the other side. When an agent writes the
implementation and no human reads it, something else has to establish that the
code is correct, that it cannot reach further than it was allowed to, and that
it still does what was asked. The design target is therefore:

> correctness, blast radius and intent-conformance established **without a
> human reading the implementation**.

Every decision below follows from that, and several of them cost ergonomics
that a human-authored language would not give up.

## Layers

```
Intent          specifications: executable scenarios, hash-pinned traces
   │
   ├── Verdict  decisions ──┐
   ├── Loom     workflows ──┤
   ├── Weft     data ───────┼──▶ Canon core IR
   ├── Tract    infra ──────┤       │
   └── Rune     policy ─────┘       │
                                    ▼
                          checker ── types, effects, exhaustiveness
                                    │
                          verifier ─ generation, shrinking, laws
                                    │
                          Ledger ─── journal, capabilities, audit
                                    │
                          Atlas ──── graph, projections, transactions
                                    │
                          gate ───── promote / escalate / block
```

Six surface languages lower to one IR. That is the single most important
structural decision here: it means the type system, the verifier, the effect
analysis, the journal, the audit chain and the promotion gate are written once
and apply to all of them. A Verdict decision, a Loom workflow and a Canon
function sit in the same dependency graph and are diffed by the same machinery.

The cost is that each surface language is constrained by what the core IR can
express. That has been worth paying every time it came up.

## Canon: the core

### Low syntactic entropy

One canonical way to write each thing. No user-defined operators, no macros,
no formatting choices. The printer's output is a function of the AST, so two
authors producing the same meaning produce identical bytes.

This is not a style preference. It is what makes a textual diff a semantic
diff, and what makes content addressing useful rather than noisy.

Supporting decisions:

- **Tabs are an error.** One indentation character.
- **One comment syntax** (`--`), one doc syntax (`---`). Ordinary comments do
  not survive into canonical form; documentation that matters goes in `doc` or
  `intent` clauses, which are part of the hashed definition.
- **No binary floating point.** `Int` is arbitrary precision, `Dec` is exact
  decimal. The target workloads are monetary and regulatory and cannot tolerate
  representation error.
- **A small reserved word set.** Everything that only has meaning inside a
  particular block — `system` inside an `ask`, `step` inside a workflow,
  `factor` inside a decision — is a contextual keyword. A language whose code
  is mostly generated should not litter the identifier space.

### Content addressing

Every definition has two hashes:

| Hash | Covers | Changes when |
| --- | --- | --- |
| local | the body, dependencies referenced by name | this definition is edited |
| deep | the body, dependencies referenced by *their* deep hashes | this definition or anything under it is edited |

The deep hash is the definition's identity. Verification results, cached
evaluations, journal entries and audit records are keyed by it, so a result can
never be attributed to the wrong version of the code.

The encoding is invariant under things that do not change meaning:

- **Local variables are encoded by binding depth**, not name. Renaming a
  parameter or a `let` is a zero-risk edit: nothing downstream is invalidated
  and no re-verification is needed.
- **Independent clause sets are sorted.** Two agents writing the same contracts
  in different order get the same hash.
- **Commutative operators are sorted by encoded operand**, so `a + b` and
  `b + a` share a hash.
- **Operator synonyms collapse.** `&&` and `and` are one form.

What is *not* invariant is as considered as what is. Enum variant order is
preserved, because it often encodes a severity ladder or a state progression.
Match arm order is preserved, because first-match-wins is semantic. A field's
default is hashed, because it decides what a literal that omits the field
produces. `intent` is hashed, because a change in stated purpose should force
re-verification and a new audit record even when the body is untouched.

Mutually recursive definitions are hashed as a group, so mutual recursion is
not a special case anywhere else in the system.

### Effects as capabilities

A function declares every effect operation it performs. Calling a function that
performs an effect requires the caller to declare it too.

The checker deliberately does **not** infer effects. An inferred footprint
widens silently when a body changes, which is exactly the event the system
exists to surface. The cost is real — adding an effect deep in a call graph
requires updating every caller — but the diagnostic names each caller and
supplies the repair, and the alternative is privilege escalation nobody sees.

`uses db.*` is legal and warns, because a wildcard makes the footprint an
over-approximation, which widens every blast radius computed against it.

### Totality

- **No `/` or `%` operator.** Division is the one partial arithmetic operation.
  `Int.div` returns `Option`. The checker rejects `/` with a targeted repair
  rather than a parse error.
- **Recursion requires `decreases`.** The measure is evaluated on entry and
  compared against the enclosing call's; a measure that fails to decrease is a
  fault naming both values.
- **Matches must be exhaustive.** There is no runtime match failure.
- **Every evaluation runs under a budget** — steps, io, tokens, wall time,
  spend. A program that exceeds its declared cost stops with a structured
  fault.

Together these mean unreviewed, agent-authored code can be executed safely,
which is a precondition for everything the verifier and the shadow runner do.

### Errors designed as a repair signal

A diagnostic is a structured object, not a formatted string:

```json
{
  "code": "CANON-E0401",
  "severity": "error",
  "message": "effect 'db.write' is performed but not declared",
  "facts": {"operation": "db.write", "declared": [], "performed": ["db.write"]},
  "repairs": [{"kind": "add-clause", "text": "uses db.write", "confidence": 0.95}]
}
```

Rendered text is generated from this, never the reverse. Codes are a stable
public API: new ones can be added, but an existing code's meaning does not
change.

## The native model primitive

`ask` is an expression form rather than a library call. That placement is what
makes the following possible:

**Schema-constrained output.** A JSON Schema is derived from the declared Canon
type. Every object is closed with `additionalProperties: false` and every field
required — a loose schema is how a malformed value reaches a contract check
that was never designed to catch it.

**Contract-checked output.** When an `ask` is in tail position — when its value
*is* the function's result — the enclosing `ensures` clauses become obligations
on the model's answer. A violation is retried with the failure fed back as
repair context. Obligations are attached *only* in tail position; anywhere else
they would check a clause against a value it was never written about.

**Strict coercion.** A model returning `"42"` where an `Int` was required is a
contract violation to be retried, not something to quietly convert.

**Capability scope and budget.** `model.infer` must be granted. Calls are
charged against token and money budgets and journaled, so a run replays exactly
and a cost is attributable to a definition.

**Compile-time capability checking.** Current Claude models reject
`temperature` with a 400 rather than ignoring it, so a `temperature` clause
aimed at one of them is a compile error. Silently dropping the clause would be
worse: the author asked for behaviour the model cannot provide.

**Providers are pluggable.** `DeterministicProvider` produces schema-valid
values as a pure function of its inputs — not a mock, a real provider whose
outputs are reproducible. It is grounding-aware: when an `ask` declares
`grounded_in`, generated strings are drawn from the source vocabulary, so a
grounded function is testable without a network.

## The Ledger

Three separate things, kept separate on purpose.

**Journal** — every effect performed, in order, with arguments and result,
hash-chained. Altering a recorded argument breaks the chain at a specific
sequence number, so the journal is usable as evidence rather than as a log.

**Broker** — decides whether an effect may be performed at all. Denies by
default. A grant names operations, an actor, an expiry, a call ceiling and a
maximum data classification. Every decision, allow or deny, is audited: an
agent repeatedly attempting an operation it was never granted is exactly the
signal an operator wants surfaced.

**Audit** — an append-only hash-chained record of governance events. Distinct
from the journal because it answers a different question: not "what did the
program do" but "who authorised it, and on what basis". Nothing is ever
rewritten; a correction is a new record referring to the earlier one.

### Three execution modes

| Mode | Effects | Used for |
| --- | --- | --- |
| live | performed against handlers, recorded | production |
| replay | answered from the recording, asserted to match | resumption, reproduction |
| shadow | answered from the recording, divergences collected | evaluating a change |

Shadow mode is the mechanism that lets a change be evaluated against real
production traffic without being able to touch anything. It is also, with no
additional machinery, how Loom resumes a crashed workflow — completed steps
return their recorded results without being performed again.

## Verification

For each function the verifier generates inputs from the parameter types,
discards those violating preconditions, runs under a budget with effects going
to a recording runtime, checks postconditions and laws, and shrinks failures.

Details that matter:

- **Generation is seeded and deterministic.** A failure reproduces from the
  seed alone, on another machine, months later. The seed is part of the report.
- **Generation is biased toward boundaries** — zero, one, negative one,
  integer limits, empty strings, Unicode, path traversal strings. Most contract
  failures live at edges.
- **Record invariants are respected.** Generating a value that violates an
  invariant is not a useful test input, because it could never exist in a
  running program.
- **Effects are satisfied, never performed.** Verification must be safe to run
  against unreviewed code.
- **Shrinking is bounded.** A counterexample of `(0, 1)` is actionable and one
  of `(-8213, 91, 4471)` is not, but a verifier that spends minutes minimising
  is worse than one that reports a slightly larger case immediately.

Laws are named properties checked against generated inputs: `deterministic`,
`pure`, `idempotent_by`, `commutative`, `associative`, `monotonic_in`,
`conserves`, `bounded_output`, `never_negative`, `order_independent`,
`invertible_by`, `explains`.

## Change evaluation

Three layers, cheapest first.

**Structural diff** — which definitions changed by content hash, and the blast
radius across the call graph. A graph walk over hashes, so it is free.

**Differential execution** — both versions run on identical generated inputs
with an effect runtime seeded from the arguments alone, so both see the same
world. A difference in outcome is therefore a difference in the code.

**Shadow replay** — the new version runs against a recorded journal.

### The promotion gate

The gate compares all of that against a stated authorisation and returns
promote, escalate or block, with every finding naming the rule it came from.

Two subtleties that took getting wrong to find:

- **Capability deltas are computed per definition, then unioned** — not as one
  set difference across all touched definitions. Unioning first lets a function
  that already held a capability mask another newly gaining it, which is
  exactly the privilege increase the gate exists to catch.
- **Scope is checked against edited definitions only.** A definition whose deep
  hash moved because a dependency changed was not edited by anyone, and
  treating that as an out-of-scope modification would make any authorisation
  narrower than the whole call graph unusable.

## Atlas

The agent's interface to the codebase, replacing files and grep.

**Queries**: callers and callees (direct or transitive), blast radius,
transitive capability footprint attributed to its source, reachable data
classifications, definitions lacking contracts or intent, every definition that
can reach a given effect.

**Projections**: a view sized to a token budget, allocating by usefulness per
token — focus definitions in full, their callees as *contracts* (enough to call
them correctly without reading them), their callers as *signatures* (enough to
know what a change would affect). What does not fit is reported as omitted
rather than silently dropped; an agent that does not know its view is partial
will reason as though it is complete.

**Transactions**: a proposal is parsed, checked and diffed without being
applied. The expensive part of an agent's mistake is usually not the mistake,
it is the broken intermediate state left behind — here there is none.

## Implementation notes

Dependency-free Python 3.11+, about 14,000 lines. The Anthropic SDK is an
optional extra needed only for live model calls.

Python was chosen for reach rather than performance. Nothing in the design
depends on it: the IR is a plain data structure, the canonical encoding is
text, and the hashes are BLAKE2b over that text. A second implementation would
produce identical hashes.

Known limits at 0.1.0:

- Generic functions are skipped by the verifier; they are checked at their call
  sites.
- The grounding check is syntactic — it catches invented identifiers and
  quantities, which is the failure mode that matters for extraction, but it is
  not entailment. A `judge` clause is the semantic route.
- Retries in Loom are unrolled rather than looped, which bounds them at 8.
- The interpreter is a tree walker. It is fast enough for verification and
  shadow runs; it is not a production runtime.
