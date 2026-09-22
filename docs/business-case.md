# Business case

## the bet

writing software is moving from people to agents. what is holding that up is
not model capability, it is that nobody hands an agent write access to
production while the damage it can do is unbounded and nobody can audit it
afterwards

every team that points agents at a real system hits the same wall in the same
order. the agent writes something plausible that passes review and then fails
in a way nobody thought about, so the team adds review gates and loses most of
the speed, so the team pushes the agent onto low stakes work and loses most of
the value

the gap is not a better model. there is no mechanism to establish what an agent
written change can reach, whether it still does what somebody asked for, and
who authorised it, without a person reading the code

## what it does

three questions with mechanical answers

what can it reach. the capability footprint of a call graph gets computed off
the code, not declared, and blast radius is a graph query

does it still do what was asked. specs are runnable and pinned to content
hashes, so drift gets found by comparing hashes instead of by somebody noticing

who authorised it. every grant, denial, verification and promotion is in a hash
chained audit log keyed to the exact version of the code

the languages are how you get those properties. they are not the product

## licensing

rust, python, go and typescript are all enormously valuable and none of them
are a business. what makes money is the runtime and the control plane around
it, databricks and snowflake and temporal and hashicorp and vercel

so the languages are open, apache-2.0. they are the wedge, they exist to make
the control plane the only sensible place to run

the control plane is the product, the verifier, the capability broker, the
effect journal, shadow deployment and the audit ledger, and nothing agent
written reaches production without going through it

everything in this repo is the open half. the hosted half is multi tenant
policy administration, blast radius across services, journal retention and
search, promotion workflow, and the compliance reporting that falls out of the
audit chain on its own

## pricing

every developer tool that exists is priced per human seat, so every one of them
gets structurally damaged by the thing this is built for. fewer engineers,
fewer seats, less revenue

this is priced per agent action, per verification, per grant, per shadow
replay, per promotion. revenue goes up as humans come out of the loop

that is the part that matters commercially, more than anything technical here.
it is the only pricing model for a developer tool that gets better as the
transition goes on

| tier | unit | who buys it |
| --- | --- | --- |
| open | free | anybody, drives adoption |
| control plane | per verification, grant, promotion | platform engineering |
| compliance | per audited environment, annual | risk, audit, regulatory |
| corpus | licensed | ai providers and labs |

## buyers

the claim is not that every business needs a new language, that has never been
true of anything. it is that every business letting agents touch production
will need capability scoping, provable blast radius and replayable audit, the
way every business that touched the internet needed a firewall

that is a category and nobody owns it yet. the languages are how you get
position inside it, because when capabilities and contracts are structural the
enforcement is sound instead of best effort, and everybody else is pattern
matching on agent output and calling it a guardrail

in order of how fast they pay

regulated decision logic. underwriting, pricing, claims, eligibility, trading
limits. smallest surface, biggest budgets, shortest sales cycle. these teams
already have to explain decisions and prove they did not use protected
attributes, and verdict makes both structural, a decision that cannot explain
itself does not compile and a prohibited factor is unreachable rather than
unused. that is a stronger control than any process they have now and it is
auditable

service plumbing. biggest surface and where agents already do most of the work.
slower to monetise but it is the route to being infrastructure instead of a
compliance tool

infrastructure and config. where agents do the most damage. sharp pain, narrow
product

data pipelines. good technical fit, weft's derived migrations and lineage are
genuinely better than what is there now, but a crowded market

## adoption

nobody rewrites 40 million lines. it goes in incrementally, a new service or
one decision inside an existing one written in the family and run through the
control plane while everything around it stays where it is. the value shows up
straight away because what is being bought is the governance, and governance is
per change, not per codebase

## ai providers

running this normally produces, as exhaust, verified tuples of what was asked
for, what got written, the proof it holds, and what happened in the real world

that is the scarcest thing in ai right now. coding agent capability is
bottlenecked on verified reward signal and this produces it continuously off
real production work instead of off synthetic benchmarks. the deterministic
replayable runtime is also a reinforcement learning environment for coding
agents, real tasks and real environments with exact replay and success criteria
a machine can check

so the pitch to a provider is not use our language. it is that this is the
verified work substrate and the data flywheel runs through it, which is either
a large licensing relationship or the reason an acquisition happens at a number
nobody got to by discounted cash flow

## risks

agents have to keep getting more autonomous. if the industry settles on a human
in the loop for everything then governance is nice to have rather than
required. the trajectory says otherwise but this is the assumption everything
sits on

enterprises have to adopt a new language for new work. hardest part of it. what
makes it survivable is that the surface languages are narrow and shaped like
their domain, a risk team picking up verdict for one decision is a much smaller
ask than a platform team picking up a general purpose language, plus
compilation to wasm and ffi into what they already run

the control plane has to stay ahead of the open core. normal open core risk. the
moat is not the code, it is the accumulated journal and audit history and the
cross service graph, and none of that is portable

somebody with more distribution could ship the category first, most likely a
model provider or a big cloud shipping agent governance as a platform feature.
the defence is structural, guardrails bolted onto an unconstrained language are
approximate and approximate is not good enough for the buyers with the money

## status

0.1.0. seven languages, a checker, verifier, deterministic runtime, capability
broker, hash chained journal and audit, shadow deployment, promotion gate,
semantic codebase graph, cli and agent interface. fourteen suites all passing,
around 14,000 lines, no dependencies

what would change the commercial picture, in order

a hosted control plane, the thing that actually gets sold

wasm compilation and ffi so a canon module runs inside an existing service
instead of beside it

a second implementation of the language, which proves the hashes are a spec and
not an implementation detail

a reference deployment somewhere regulated, which is the only evidence that
moves the buyers who pay the most
