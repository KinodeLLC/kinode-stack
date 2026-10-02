# Handoff prompt

paste the block below into a new claude session to pick this up. it assumes a
cloud environment with no local copy of the code.

---

## the prompt

```
i own kinode (github org KinodeLLC). i have a working language family and
runtime for code that agents write instead of people. eight private repos,
version 0.1.0, all tests passing. you are picking it up from here.

## get set up first

clone all eight repos from github.com/KinodeLLC into one directory:

  canon intent loom verdict weft tract rune kinode-stack

then verify it actually works before you touch anything:

  cd kinode-stack && python tests/run_all.py

you should get "14/14 suites passed". if you do not, stop and tell me what
broke rather than working around it. python 3.11+, no dependencies. the
anthropic sdk is optional and only needed for live model calls.

to run anything else you need the packages on the path:

  export PYTHONPATH=canon/src:intent/src:loom/src:verdict/src:weft/src:tract/src:rune/src

## what it is

seven surface languages over one core ir. canon is the core and everything
else lowers to it, which is why there is one type system, one verifier, one
runtime, one audit trail and one blast radius analysis covering all of them.

  canon     contracts, effects that work like capabilities, definitions
            addressed by content hash. also holds the runtime, verifier,
            journal, atlas, cli and agent interface
  intent    specs. scenarios run as tests, goals pinned to content hashes
  loom      durable workflows, compensation next to the step, replay resumption
  verdict   regulated decisions that will not compile unless they explain
            themselves
  weft      schemas, migrations with the round trip verified, data lineage
  tract     infrastructure worked out from what the code can reach
  rune      policy, compiles into capability grants and promotion
            authorisations

the point of the whole thing is establishing that a change is correct, that it
cannot reach further than it was allowed to, and that it still does what
somebody asked for, without a person reading the implementation.

read kinode-stack/README.md, then docs/architecture.md, then docs/languages.md
before you change anything. kinode-stack/examples/lending is one system
written across all seven languages and it is the fastest way to see how they
fit. kinode-stack/tests/integration.py drives the whole path a change takes.

## how i want things written

this matters as much as the code. i have corrected it several times already
and i do not want to do it again.

- lowercase almost everywhere, headers included
- long sentences joined with commas where most people would use a period
- no contractions. "do not", "it is", "cannot"
- no em dashes, ever
- second person. what happens to you, not what an abstract noun does
- the reason goes in the same sentence as the thing, with "because" or
  "if x then y". not a separate explaining sentence after it
- repeat words instead of hunting for synonyms
- prose for sequences, not bullet lists. tables are fine for reference data
- no intro paragraph and no summary paragraph. start at the first fact, stop
  at the last one

do not write any of these:

- headers shaped like questions or answers. "what is enforced", "what it
  produces", "why it is shaped this way", "the problem it solves". use short
  plain nouns instead. install, constraints, output, migrations, retries
- several sentences of the same length in a row, each one a complete
  self-contained fact. that even rhythm is the biggest tell
- saying the thing then explaining it in a second sentence
- rhetorical concessions. "which is annoying but"
- thesis sentences. "nothing is partial"
- emphasis constructions. "the one x that can y", "the single most important"
- bolded lead-ins on every bullet
- blockquote pull-quotes
- the words deliberately, precisely, on purpose, exactly, which is what makes

## hard rules

- no ai watermarks anywhere. not in code, docs, readmes, commit messages, pr
  bodies or github metadata. no Co-Authored-By trailers for anyone including
  claude, no "generated with" lines, no session links
- i am the sole author. brent gordon. copyright kinode. no contributor lists
  or credits sections unless i ask
- apache-2.0 on everything
- semver, keep a changelog format, conventional commits. three versions get
  tracked separately, the package version, language_version for surface
  syntax, and ir_version for the core ir and canonical encoding. bumping
  ir_version invalidates every stored hash so it is always breaking
- run kinode-stack/tests/run_all.py before you commit anything, and if a test
  fails tell me with the output rather than skipping it

## what is open

- a hosted control plane. the languages are the open wedge, the control plane
  is what actually gets sold. verifier, capability broker, effect journal,
  shadow deployment, audit ledger, priced per agent action rather than per
  seat
- wasm compilation and ffi so a canon module runs inside an existing service
  instead of beside it
- a second implementation of the language, which would prove the hashes are a
  spec and not an implementation detail
- the repos are private. canon needs to go public at some point if it is going
  to get adoption, and that is easier before anybody outside has a link they
  cannot open

known gaps at 0.1.0 are in docs/architecture.md under limits. generic
functions get skipped by the verifier, the grounding check is syntactic rather
than entailment, loom retries cap at 8 because they are unrolled, and the
interpreter is a tree walker that is fine for verification and not a
production runtime.

tell me what you are going to do before you start on anything large.
```

---

## one thing to sort out first

the repos are private, so a cloud session needs access to the KinodeLLC org
before any of this works. either

- make them public, which canon needs eventually anyway, or
- give the cloud environment a token with read access to the org

if neither is done the session will fail at the clone step and everything
after it is wasted.
