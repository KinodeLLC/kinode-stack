# Architecture

how the pieces fit and why each one is shaped the way it is.

the thing everything comes out of: when an agent writes the code and nobody
reads it, something else has to establish that it is correct, that it cannot
reach further than it was allowed to, and that it still does what somebody
asked for. several of the decisions below cost ergonomics that a language for
humans would not give up, and that is why.

## layers

```
Intent          specs, runnable scenarios, traces pinned to hashes
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
                          journal ── effects, capabilities, audit
                                    │
                          atlas ──── graph, projections, transactions
                                    │
                          gate ───── promote / escalate / block
```

six surface languages lower to one ir, which is the decision everything else
hangs off. the type system, the verifier, the effect analysis, the journal, the
audit chain and the gate get written once and work on all of them, and a
verdict decision and a loom workflow and a canon function all end up in the
same dependency graph getting diffed by the same code. the cost is that each
language can only say what the core ir can hold, which has been worth paying
every time it came up.

## syntax

one way to write each thing. no user defined operators, no macros, no
formatting choices. the printer output is a function of the ast so two people
writing the same meaning produce the same bytes

that is not a style preference, it is what makes a text diff a semantic diff
and what makes content addressing worth anything

tabs are an error, one indentation character. one comment syntax `--` and one
doc syntax `---`, and ordinary comments do not survive into canonical form, so
anything you want kept goes in a `doc` or `intent` clause where it becomes part
of the hash. there is no binary floating point, `Int` is arbitrary precision
and `Dec` is exact decimal, since the workloads this is for are money and
regulation and cannot take representation error

the reserved word list is short. anything that only means something inside one
block, `system` inside an `ask`, `step` inside a workflow, `factor` inside a
decision, is contextual, because a language where most of the code is generated
should not be taking identifiers away from you

## hashing

two hashes per definition

| hash | covers | moves when |
| --- | --- | --- |
| local | the body, dependencies by name | you edit this definition |
| deep | the body, dependencies by their deep hashes | you edit this or anything under it |

the deep hash is the identity. verification results, cached evaluations,
journal entries and audit records all key off it so a result cannot get
attributed to the wrong version of the code

the encoding ignores things that do not change meaning. local variables get
encoded by binding depth instead of by name, so renaming a parameter or a `let`
invalidates nothing and needs no reverification. independent clause sets get
sorted so two people writing the same contracts in a different order land on
the same hash. commutative operators get sorted by encoded operand so `a + b`
and `b + a` come out the same. operator synonyms collapse, `&&` and `and` are
one form

what it does not ignore matters as much. enum variant order stays because it
usually encodes a severity ladder or a state progression. match arm order stays
because first match wins is semantic. a field default is hashed because it
decides what a literal that leaves the field out produces. `intent` is hashed,
so changing what a function is for forces reverification and a new audit record
even when you did not touch the body

mutually recursive definitions get hashed as a group so mutual recursion is not
a special case anywhere else

## effects

a function declares every effect operation it performs, and anything calling it
declares them too

the checker will not infer them. an inferred list gets wider every time
somebody edits a body, which is exactly the event this exists to surface. the
cost is real, adding an effect deep in a call graph means updating every caller
above it, but the error names each one and hands you the fix, and the
alternative is privilege creep nobody sees

`uses db.*` is legal and warns, because a wildcard turns the footprint into an
over approximation and widens every blast radius computed off it

## totality

no `/` or `%` operator, dividing by zero is the only arithmetic that can fail.
`Int.div` gives you an `Option` and the checker rejects `/` with a targeted fix
rather than a parse error

recursion needs a `decreases` measure, evaluated on entry and compared against
the enclosing call, and a measure that does not decrease is a fault with both
values in it

matches have to be exhaustive, there is no runtime match failure

everything runs under a budget for steps, io, tokens, wall time and money, and
a program that goes past its declared cost stops with a structured fault

together that is what lets you execute agent written code nobody has reviewed,
which the verifier and the shadow runner both need to be able to do

## errors

a diagnostic is a structured object, not a string

```json
{
  "code": "CANON-E0401",
  "severity": "error",
  "message": "effect 'db.write' is performed but not declared",
  "facts": {"operation": "db.write", "declared": [], "performed": ["db.write"]},
  "repairs": [{"kind": "add-clause", "text": "uses db.write", "confidence": 0.95}]
}
```

the rendered text gets generated from that, never the other way round. codes
are public api, you can add new ones but an existing one does not change what
it means

## models

`ask` is an expression rather than a library call, and that is what makes the
rest of it possible

the json schema comes off the declared canon type, every object closed with
`additionalProperties: false` and every field required, because a loose schema
is how a malformed value gets past a contract check that was never written to
catch it

when an `ask` is in tail position, when its value is the function's result, the
`ensures` clauses become obligations on what the model returned, and a failure
gets retried with the failure handed back as context. obligations only attach
in tail position, anywhere else they would be checking a clause against a value
it was never written about

coercion is strict. a model returning `"42"` where an `Int` was wanted is a
contract violation to retry, not something to quietly convert

`model.infer` needs a grant, calls get charged against token and money budgets
and written to the journal, so a run replays exactly and a cost can be pinned
to a definition

model capabilities get checked at compile time. current claude models reject
`temperature` with a 400 instead of ignoring it, so a `temperature` clause
aimed at one of them is a compile error, since dropping it silently would mean
somebody asked for behaviour they are not going to get

providers plug in. `DeterministicProvider` produces schema valid values as a
pure function of its inputs, so it is not a mock, it is a real provider you can
reproduce. it knows about grounding too, so when an `ask` declares
`grounded_in` the generated strings come out of the source vocabulary and a
grounded function stays testable with no network

## journal

three things, kept apart on purpose

the journal holds every effect performed, in order, with arguments and result,
hash chained. change a recorded argument and the chain breaks at a specific
sequence number, which is what makes it usable as evidence rather than as a log

the broker decides whether an effect happens at all and denies by default. a
grant names operations, an actor, an expiry, a call ceiling and a maximum data
classification. every decision gets audited either way, because an agent
repeatedly trying something it was never granted is exactly what an operator
wants to see

the audit chain is append only and hash chained and holds governance events. it
answers a different question from the journal, not what the program did but who
authorised it and on what basis. nothing gets rewritten, a correction is a new
record pointing at the old one

## modes

| mode | effects | what it is for |
| --- | --- | --- |
| live | performed against handlers, recorded | production |
| replay | answered from the recording, asserted to match | resumption, reproducing a bug |
| shadow | answered from the recording, divergences collected | evaluating a change |

shadow is what lets a change get evaluated against real production traffic
without being able to touch anything, and with no extra machinery it is also
how loom resumes a crashed workflow, since completed steps hand back what they
recorded

## verification

for each function it generates inputs off the parameter types, throws away the
ones that break preconditions, runs the rest under a budget with effects going
to a recording runtime, checks postconditions and laws, and shrinks failures

generation is seeded so a failure reproduces off the seed alone on another
machine months later, and the seed goes in the report

it biases toward boundaries, zero and one and negative one and integer limits
and empty strings and unicode and path traversal strings, because that is where
contract failures live

record invariants get respected, since generating a value that breaks one is
not a useful test input when it could never exist in a running program

effects get satisfied and never performed, verification has to be safe to point
at code nobody reviewed

shrinking is bounded. a counterexample of `(0, 1)` is something you can read and
one of `(-8213, 91, 4471)` is not, but a verifier spending minutes minimising is
worse than one handing you something slightly bigger right away

laws are named properties checked against generated inputs. `deterministic`,
`pure`, `idempotent_by`, `commutative`, `associative`, `monotonic_in`,
`conserves`, `bounded_output`, `never_negative`, `order_independent`,
`invertible_by`, `explains`

## diffing

three layers, cheapest first

structural diff is which definitions changed by hash and the blast radius
across the call graph, a graph walk over hashes so it costs nothing

differential execution runs both versions on the same generated inputs with an
effect runtime seeded off the arguments, so both see the same world and a
difference in outcome is a difference in the code

shadow replay runs the new version against a recorded journal

## gate

it takes all of that and an authorisation and returns promote, escalate or
block, and every finding names the rule it came from

two things here took getting wrong to find. capability deltas get computed per
definition and then unioned, not as one set difference across everything
touched, because unioning first lets a function that already had a capability
hide another one newly getting it, which is the escalation the gate is for.
and scope gets checked against definitions somebody actually edited, since a
definition whose deep hash moved because a dependency changed was not edited by
anyone, and counting that would make any authorisation narrower than the whole
call graph unusable

## atlas

the agent's way into the codebase instead of files and grep

queries are callers and callees direct or transitive, blast radius, transitive
capability footprint attributed back to where each effect comes from, reachable
data classifications, definitions with no contracts or no intent, and every
definition that can reach a given effect

projections get sized to a token budget and spend it by usefulness, focus
definitions in full, what they call as contracts so you can call them correctly
without reading them, what calls them as signatures so you know what a change
touches. whatever does not fit gets reported as omitted rather than cut off
quietly, since an agent that does not know its view is partial will reason like
it is complete

edits are transactional. a proposal gets parsed and checked and diffed without
being applied, because the expensive part of an agent's mistake is usually not
the mistake, it is the broken half state it leaves behind

## limits

dependency free python 3.11+, around 14,000 lines. the anthropic sdk is an
optional extra for live model calls

python was picked for reach, not speed. nothing in the design depends on it,
the ir is a plain data structure, the canonical encoding is text, and the
hashes are blake2b over that text, so a second implementation would produce
the same hashes

what is not there at 0.1.0. generic functions get skipped by the verifier and
checked at their call sites instead. the grounding check is syntactic, it
catches invented identifiers and quantities which is the failure that matters
for extraction, but it is not entailment and a `judge` clause is the semantic
route. loom retries are unrolled so they cap at 8. the interpreter is a tree
walker, fast enough for verification and shadow runs and not a production
runtime.
