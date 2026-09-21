# Business case

## The bet

Software authorship is shifting from people to agents. The constraint on that
shift is not model capability — it is that nobody will give an agent write
access to production while the damage it can do is unbounded and unauditable.

Every team that has tried running agents against real systems hits the same
wall, in the same order:

1. The agent writes plausible code that passes review and fails in a way nobody
   anticipated.
2. The team adds review gates, which removes most of the speed advantage.
3. The team restricts the agent to low-stakes work, which removes most of the
   value.

The gap is not a better model. It is that there is no mechanism to establish
what an agent-authored change can reach, whether it still does what was asked,
and who authorised it — without a person reading the code.

## What this is

A substrate where those three questions have mechanical answers:

- **What can it reach?** The capability footprint of any call graph is computed
  from the code, not declared. Blast radius is a graph query.
- **Does it still do what was asked?** Specifications are executable and pinned
  to content hashes, so drift is detected by hash comparison rather than by
  someone noticing.
- **Who authorised it?** Every grant, denial, verification and promotion is in
  a hash-chained audit log, keyed to the exact version of the code.

The languages are how you get those properties. They are not the product.

## Commercial architecture

### Languages do not make money. Control planes do.

Rust, Python, Go, TypeScript — enormously valuable, none of them a business.
What monetises is the runtime and the control plane around it: Databricks,
Snowflake, Temporal, HashiCorp, Vercel.

So:

- **The languages are open and permissively licensed.** Apache-2.0. They are
  the wedge, not the product. They exist to make the control plane the only
  sensible place to run.
- **The control plane is the product**: the verifier, the capability broker,
  the effect journal, shadow deployment and the audit ledger. Nothing
  agent-authored reaches production without passing through it.

Everything in this repository is the open half. The control plane is the hosted
half: multi-tenant policy administration, cross-service blast radius, journal
retention and search, promotion workflow, and the compliance reporting that
falls out of the audit chain.

### Pricing scales with agents, not seats

Every existing developer tool is priced per human seat, which means every one
of them is structurally damaged by the transition this is built for. Fewer
engineers, fewer seats, shrinking revenue.

This is priced **per agent-action**: per verification, per capability grant,
per shadow replay, per promotion. Revenue grows precisely as humans leave the
loop.

That is the commercially important property, more than any technical one. It is
the only dev-tools pricing model that improves as the transition proceeds.

| Tier | Unit | Buyer |
| --- | --- | --- |
| Open | free | any team; drives adoption and standard-setting |
| Control plane | per verification / grant / promotion | platform engineering |
| Compliance | per audited environment, annual | risk, audit, regulatory affairs |
| Corpus | licensed | AI providers and research labs |

## Who buys it

### The defensible claim

Not "every business needs a new language" — that has never been true of
anything. The claim is:

> Every business that lets agents touch production will need capability
> scoping, provable blast radius and replayable audit — the way every business
> that touched the internet needed a firewall.

That is a category, and it is currently unowned. The languages are how you get
privileged position inside it: when capabilities and contracts are
*structural*, enforcement is sound rather than best-effort. Everyone else is
pattern-matching on agent output and calling it a guardrail.

### Entry points, in order of willingness to pay

**Regulated decision logic.** Underwriting, pricing, claims, eligibility,
trading limits. Smallest surface, highest budgets, shortest sales cycle. These
teams are already legally required to explain decisions and prove protected
attributes were not used. Verdict makes both structural: a decision that cannot
explain itself does not compile, and a prohibited factor is unreachable rather
than merely unused. That is a materially stronger control than any existing
process, and it is auditable.

**Service plumbing.** The largest surface and where agents already do the most
work. Slower to monetise, but it is the path to being infrastructure rather
than a compliance tool.

**Infrastructure and configuration.** Where agents cause the most catastrophic
damage. Sharp pain, narrow product.

**Data pipelines.** Good technical fit — Weft's derived migrations and lineage
are genuinely better than the status quo — but a crowded market.

### Adoption path

Nobody rewrites 40 million lines. Adoption is incremental: a new service, or
one decision inside an existing one, written in the family and run through the
control plane while everything around it stays as it is. The value shows up
immediately because the *governance* is what is being bought, and governance
is per-change, not per-codebase.

## Why AI providers specifically

The stack emits, as ordinary exhaust from normal operation:

> verified `(intent → implementation → proof → real-world outcome)` tuples

That is the scarcest asset in AI right now. Coding-agent capability is
bottlenecked on verified reward signal, and this produces it continuously from
real production work rather than from synthetic benchmarks. The deterministic,
replayable runtime is also a reinforcement-learning environment for coding
agents: real tasks, real environments, exact replay, machine-checkable success
criteria.

The pitch to a provider is therefore not "use our language". It is: *this is
the verified-work substrate, and the data flywheel runs through it.* That is
either a large licensing relationship or the reason an acquisition happens at a
number that is not arrived at by discounted cash flow.

## What has to be true

Honest list of what this depends on.

**Agents keep getting more autonomous.** If the industry settles on
human-in-the-loop for everything, the governance layer is a nice-to-have rather
than a requirement. Current trajectory says otherwise, but it is the load-bearing
assumption.

**Enterprises adopt a new language for new work.** The hardest sell. Mitigated
by the surface languages being narrow and domain-shaped — a risk team adopting
Verdict for one decision is a much smaller ask than a platform team adopting a
general-purpose language — and by compilation to WASM with FFI into existing
runtimes.

**The control plane stays ahead of the open core.** Standard open-core risk. The
moat is not the code; it is the accumulated journal, the audit history and the
cross-service graph, none of which is portable.

**Nobody with more distribution ships the same category first.** The most
likely competitive shape is a model provider or a major cloud shipping agent
governance as a platform feature. The defence is the structural one: guardrails
bolted onto an unconstrained language are approximate, and approximate is not
good enough for the buyers with the budgets.

## Status and cost to date

Version 0.1.0. Seven languages, a checker, verifier, deterministic runtime,
capability broker, hash-chained journal and audit, shadow deployment, promotion
gate, semantic codebase graph, CLI and agent interface. Fourteen test suites,
all passing. Roughly 14,000 lines, no dependencies.

The next milestones that change the commercial picture, in order:

1. **A hosted control plane** — the thing that is actually sold.
2. **WASM compilation and FFI**, so a Canon module runs inside an existing
   service rather than beside it.
3. **A second language implementation**, proving the hashes are a specification
   rather than an implementation detail.
4. **A reference deployment in a regulated environment**, which is the only
   evidence that matters to the buyers who pay most.
