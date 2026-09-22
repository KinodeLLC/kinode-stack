# Kinode

a family of programming languages and a runtime for code that agents write
instead of people.

the usual framing for this is a language a model finds easy to write, but
models already write python and typescript fine and syntax was never what was
stopping anybody. what is actually missing is a way to establish that a change
is correct, that it cannot reach further than it was allowed to, and that it
still does what somebody asked for, without a person sitting down and reading
the implementation. everything here comes out of that.

## status

working software, 0.1.0. fourteen suites, all passing

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

python 3.11+ and nothing else. the anthropic sdk is optional and only needed if
you want live model calls.

## languages

seven of them over one shared core. each one gets syntax that fits how its
domain actually works, and they all lower to the same ir, so there is one type
system, one verifier, one runtime, one audit trail and one blast radius
analysis covering all of them instead of seven of each

| language | file | what it is for |
| --- | --- | --- |
| [intent](../intent) | `.intent` | specs whose scenarios run and whose traces are pinned to hashes |
| [canon](../canon) | `.canon` | the core. contracts, effects as capabilities, content addressing |
| [loom](../loom) | `.loom` | durable workflows, compensation, resumption off the journal |
| [verdict](../verdict) | `.verdict` | regulated decisions that will not compile unless they explain themselves |
| [weft](../weft) | `.weft` | schemas, migrations with the round trip proved, data lineage |
| [tract](../tract) | `.tract` | infrastructure worked out from what the code can reach |
| [rune](../rune) | `.rune` | policy, compiled into grants and promotion authorisations |

## effects

a function declares every effect it performs, and anything calling it declares
them too. nothing is inferred, because an inferred list gets wider every time
somebody edits a body and you do not find out until production

```canon
fn persist(o: Order) -> Unit
  intent "Write an order to storage."
  uses store.write
{
  store.write(o.id, o.customer.id)
}
```

miss the declaration and you get told, with the fix attached

```
error[CANON-E0401]: effect 'store.write' is performed but not declared
  operation: store.write
  fix: declare the effect on 'persist' `uses store.write`
```

so what a call graph can reach is something you compute rather than something
you write down and hope stays true

```
$ canon atlas caps originate examples/lending
lending.origination.originate
  declared:   bureau.pull, ledger.append, ledger.commit, ledger.reverse,
              notify.email, workflow.checkpoint, workflow.compensated
  transitive: (the same set)
```

## hashing

every definition is identified by the hash of its normalised ast. local
variables get encoded by binding depth rather than by name and independent
contract clauses get sorted, so renaming a local does not move the hash,
neither does reordering your `requires` and `ensures` and `uses`, and neither
does reformatting. a rename is a zero risk edit, nothing downstream needs
rechecking

editing something a function depends on moves its deep hash but leaves its
local hash alone, which is how you tell somebody editing a function apart from
somebody editing what it calls

## verification

```canon
fn apply_discount(total: Int, percent: Int) -> Int
  requires percent >= 0
  requires percent <= 100
  ensures result >= 0
  ensures result <= total
  law never_negative
```

the verifier generates inputs off the parameter types, throws away the ones
that break the preconditions, runs the rest, checks the postconditions and the
laws, and shrinks anything that fails down to something you can read

```
FAIL billing.overcharge  0/38 runs
     postcondition: postcondition does not hold
     input: (0, 1)
```

generation is seeded so a failure comes back the same way next time, on another
machine, months later, off the seed

## totality

there is no division operator because dividing by zero is the only arithmetic
that can fail

```
error[CANON-E0301]: there is no `/` operator in Canon
  use_instead: Int.div
  try: use Int.div, which returns Option and cannot fault `Int.div(a, b)`
```

recursion needs a decreases measure that the runtime checks, matches have to
cover every case, and everything runs under a budget for steps, io, tokens and
money. that is what makes it safe to execute agent written code nobody has read
yet, which the verifier and the shadow runner both depend on

## models

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

`ask` is an expression rather than a library call, which gets you four things

the json schema comes off `Assessment`, so what you get back is a typed value
and not a string you have to parse

the `ensures` clauses on the function are enforced on what the model returned,
and if one fails you get a retry with the failure handed back as context, then
a structured fault if it still will not comply

`model.infer` has to be granted like any other effect, the call is budgeted in
tokens and money, and it goes in the journal, so a run replays exactly

model capabilities are checked when you compile. current claude models reject
`temperature` with a 400 rather than ignoring it, so canon rejects the clause
up front

```
error[CANON-E0301]: claude.opus does not accept a temperature setting
```

## journal

every effect goes into a hash chained journal, and that one mechanism gets you
exact replay of a recorded run with zero external calls, shadow deployment
where a changed version runs against recorded production traffic and answers
its effects out of the recording so it touches nothing while you collect what
diverged, workflow resumption without loom needing a state store of its own,
and tamper evidence, since altering a recorded argument breaks the chain at a
specific sequence number

## promotion

```
decision: BLOCK
  [block] CANON-E0905: lending.origination.originate was modified but is
          outside the authorised scope
```

the gate takes a change and an authorisation saying which definitions it can
touch, which capabilities it can reach, how big a blast radius is acceptable,
how sensitive the data can get and whether behaviour is allowed to change at
all. capability deltas get computed per definition rather than across the whole
set, so a function newly reaching something another function already had still
comes back as a privilege increase

## example

[`examples/lending`](examples/lending) is one system written across all seven
languages, 7 files and 43 definitions

```
$ canon check examples/lending
ok: 7 files, 43 definitions, 7 warnings
```

they end up in one graph. editing a single canon helper reaches into verdict,
loom and intent

```
$ canon atlas blast affordability_ratio examples/lending
lending.affordability_ratio #ecpsvedi
  11 transitive dependents
  capabilities: bureau.pull, ledger.append, notify.email,
                workflow.checkpoint, workflow.compensated
  data: personal, pseudonymous
```

the integration suite runs the whole path a change would take. some of what it
shows

a policy that denies money stops a workflow at the ledger. the underwriting
agent can pull a credit file but cannot book a loan, so the workflow runs up to
`ledger.append` and gets refused at the boundary

a two phase booking reverses properly. settlement fails, the staged ledger
entry gets reversed, and the customer does not get told about a loan that was
rolled back

an interrupted origination resumes without re billing the bureau. replay comes
back with the same offer and zero external calls

a behaviour preserving edit still reports its goals stale. every scenario
passes, but six goal traces went stale because the hash they were accepted
against moved, which is the thing a test suite cannot catch

the same edit gets judged differently by two policies. adding a schema field
escalates under the data agent and gets blocked under the underwriting agent

## agent interface

agents drive json-rpc over stdin and stdout instead of files and grep

```json
{"method": "atlas.view", "params": {"focus": "submit", "budget": 4000}}
{"method": "edit.propose", "params": {"changes": {"orders.canon": "..."}}}
{"method": "gate.evaluate", "params": {"proposal": "prop-1"}}
{"method": "edit.commit", "params": {"proposal": "prop-1", "write": true}}
```

`atlas.view` hands back a projection sized to a token budget, the focus
definition in full, what it calls as contracts, what calls it as signatures,
and it tells you what it left out rather than quietly cutting it off. an agent
that does not know its view is partial will reason like it is complete

edits are transactional. a proposal gets parsed and checked and diffed without
being applied, so a failed edit leaves nothing behind. there is no method that
writes code nobody checked

## running it

```sh
export PYTHONPATH=canon/src:intent/src:loom/src:verdict/src:weft/src:tract/src:rune/src

python -m canon.cli check  kinode-stack/examples/lending
python -m canon.cli test   kinode-stack/examples/lending
python -m canon.cli verify kinode-stack/examples/lending --runs 40
python -m canon.cli atlas blast affordability_ratio kinode-stack/examples/lending
python -m canon.cli serve  kinode-stack/examples/lending
```

or install them

```sh
pip install -e canon -e intent -e loom -e verdict -e weft -e tract -e rune
canon check kinode-stack/examples/lending
```

## docs

| doc | what is in it |
| --- | --- |
| [architecture](docs/architecture.md) | how the pieces fit and why each one is there |
| [languages](docs/languages.md) | all seven with worked examples |
| [business case](docs/business-case.md) | who buys it, pricing, what has to hold |
| [diagnostics](docs/diagnostics.md) | every code and what it means |

## layout

each language is its own repo, versioned on its own under semver, with its own
changelog and tests

```
kinode/
  canon/          core language, runtime, verifier, atlas, cli, agent interface
  intent/         spec layer
  loom/           durable workflows
  verdict/        decision rules
  weft/           schemas and migrations
  tract/          infrastructure
  rune/           policy
  kinode-stack/   docs, cross language examples, integration tests
```

## licence

Apache-2.0, Kinode.
