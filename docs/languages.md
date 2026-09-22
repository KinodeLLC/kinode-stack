# Languages

seven surface languages over one core ir. each one comes from the same
question, what does this domain need to make checkable by a machine that a
general purpose language leaves up to convention

every example here is out of [`examples/lending`](../examples/lending), which
checks and runs.

---

## canon

the core, everything else lowers to it

```canon
module lending

record LoanRequest {
  reference: Text
  applicant_id: Text
  amount_requested: Int
  term_months: Int
  classify applicant_id pseudonymous
  invariant amount_requested >= 0
  invariant term_months >= 0
}

effect ledger {
  --- Stage an accounting entry. Reversible until it is committed.
  append(reference: Text, amount: Int) -> Result<Text, OriginationError>
  --- Make a staged entry permanent. This is the point of no return.
  commit(reference: Text) -> Result<Text, OriginationError>
  idempotent read(reference: Text) -> Option<Text>
}

fn affordability_ratio(amount: Int, annual_income: Int) -> Int
  intent "Borrowing as a whole-number percentage of annual income."
  requires amount >= 0
  requires annual_income >= 0
  ensures result >= 0
  law never_negative
  law deterministic
{
  Option.unwrap_or(Int.div(amount * 100, Int.max(annual_income, 1)), 100)
}
```

### clauses

| clause | what it means |
| --- | --- |
| `intent "..."` | what this is for. part of the hash, and what intent matches against |
| `uses a.b, c.d` | every effect operation this can perform. not inferred |
| `requires <expr>` | precondition, checked on entry and used to throw out generated inputs |
| `ensures <expr>` | postcondition, with `result` and `old(...)` in scope |
| `law <name>` | a named property the verifier checks against generated inputs |
| `cost steps N, io N, tokens N, millis N, money N` | ceiling, enforced at runtime and compared against what actually got used |
| `decreases <expr>` | needed for recursion, the measure has to go down |

### laws

`deterministic`, `pure`, `total`, `idempotent_by(key)`, `commutative`,
`associative`, `monotonic_in(param)`, `conserves(field)`, `bounded_output(n)`,
`never_negative`, `order_independent`, `injective`, `invertible_by(fn)`,
`grounded`, `explains`

### types

`Int` arbitrary precision, `Dec` exact decimal, `Text`, `Bool`, `Unit`,
`Bytes`, `Time`, `List<T>`, `Set<T>`, `Map<K,V>`, `Option<T>`, `Result<T,E>`,
records, enums, `Fn(A) -> B uses e.op`

no subtyping, no implicit conversion, no truthiness. every function and lambda
parameter and record field is annotated, so the checker only ever instantiates
polymorphism instead of inferring it, and a type error lands on one spot with a
concrete expected and actual instead of unwinding through three layers

### rejected

```canon
a / b                         -- no division operator, use Int.div
if count then ... else        -- no truthiness, compare it
match c { case Red => 1 }     -- not exhaustive
fn f(n: Int) -> Int { f(n) }  -- recursion with no decreases measure
a + b                         -- a is Int and b is Dec
```

each of those comes back with a fix attached

### ask

```canon
fn triage(body: Text) -> Severity
  uses model.infer, model.judge
  ensures result.level >= 1
  cost tokens 2000, io 1
{
  ask Severity from claude.opus {
    system "Triage this support ticket."
    input body
    grounded_in body
    retries 3 on contract_violation, type_error, grounding_failure
    max_tokens 512
  }
}
```

settings are `system`, `input [label:]`, `grounded_in`, `examples`,
`temperature`, `retries N on ...`, `max_tokens`, `judge`

retry reasons are `contract_violation`, `type_error`, `refusal`, `timeout`,
`grounding_failure`, `judge_rejected`

models go by alias, `claude.opus`, `claude.sonnet`, `claude.haiku`,
`claude.fable`, `stub.deterministic`, and their capabilities get checked when
you compile

---

## intent

specs whose scenarios run, and goals pinned to the hash of the code under them

```intent
goal "A captured charge can be refunded once, up to its captured amount"
  owner "payments-team"
  rationale "Customers must be able to reverse a charge without contacting support."

  scenario "a captured charge refunds in full"
    given c = Charge { id: "c1", amount: Money { amount: 5000 }, status: Captured }
    expect refund(c, 5000) is Ok(Refund { amount: 5000 })

  scenario "refunding more than the captured amount is rejected"
    given c = Charge { id: "c1", amount: Money { amount: 5000 }, status: Captured }
    expect refund(c, 6000) is Err(AmountExceeded(5000))

  nonfunctional "refunds complete promptly"
    metric millis <= 250

  traces billing.refund at #mzod4ptezmedyw2dfsbywrumek
```

scenarios lower to canon tests, so a spec you cannot run is not a spec and a
goal with no scenarios will not compile

`accept` writes down the current hash of everything a goal traces to. change one
of those and the goal comes back stale, including when every scenario still
passes, which is the case tests cannot catch

```
FAIL A strong application is approved automatically
     scenarios 2/2
     changed since acceptance: lending.underwriting.assess (#7fa2 -> #b104)
```

definitions no goal traces to get listed. non functional requirements get
checked against declared cost so `millis <= 250` is compared against something
the compiler already knows

---

## verdict

decisions that will not compile unless they can explain themselves

```verdict
decision assess(input: Assessment) -> Ruling
  intent "Decide a personal loan on credit quality, affordability and tenure."
  cost steps 200000

  prohibited input.applicant.legal_name, input.applicant.email

  factor score: Int = Int.max(input.bureau_score, input.applicant.credit_score)
    because "Credit history is the strongest single predictor of repayment."
    weight 45

  factor burden: Int = affordability_ratio(input.request.amount_requested,
                                           input.applicant.annual_income)
    because "Borrowing as a share of income bounds what the applicant can afford."
    weight 35

  rule below_credit_floor
    when score < 560
    outcome Decline
    because "The credit score is below the published floor of 560."

  rule prime
    when score >= 720 and burden <= 30 and tenure >= 12
    outcome Approve
    because "Strong credit, affordable borrowing and stable employment."

  otherwise Refer
    because "Does not meet the published criteria for an automatic decision."
```

every rule states a reason and leaving `because` off is a parse error. every
decision has a default so there is no input it cannot answer and no outcome
with nothing recorded about why. every factor says why it is used, since one
that cannot go in the explanation is no use in a regulated decision

prohibited fields are unreachable rather than unused, and it does not matter
whether a rule reads one directly or gets at it through a factor, the error
tells you which route

```
error[CANON-E0903]: rule 'below_credit_floor' depends on a prohibited field
  fields: ['input.applicant.legal_name']
  via_factors: ['tenure']
```

it lowers to a result record holding the outcome and the reasons and every
factor with its value and weight and basis, plus contracts saying there is
always at least one reason and every factor considered gets reported

---

## loom

durable workflows, compensation next to the step it undoes, resumption off the
journal

```loom
workflow originate(request: LoanRequest, applicant: ApplicantV2)
    -> Result<LoanOffer, OriginationError>
  intent "Pull a credit file, decide, book the loan, and confirm it."
  uses bureau.pull, ledger.append, ledger.commit, ledger.reverse, notify.email
  deadline 900000
  idempotent by request
{
  step credit_file = bureau.pull(request.applicant_id)
    retry 2

  let ruling = assess_outcome(Assessment { ... })
  let offer = build_offer(request, ruling, credit_file)

  step booking: ledger.append(request.reference, offer.amount)
    compensate ledger.reverse(request.reference)

  step settlement: ledger.commit(request.reference)

  step confirmation: notify.email(applicant.email, "Your loan offer", request.reference)
    on_failure continue

  Ok(offer)
}
```

`step name = expr` names and binds, `step name: expr` names without binding,
`step expr` derives a name

the undoing gets written into the generated canon rather than driven by a
runtime stack, so you can read the failure path for every step before anything
runs and it goes in reverse

retries are unrolled instead of looped, which keeps workflows total and keeps
the number of external calls readable in the source, capped at 8

each step checkpoints before it runs so a crashed workflow picks up at the
first step that never finished

```
ok  an interrupted origination resumes without re-billing the bureau:
    replayed 8 journal entries, no external call repeated, identical offer
```

`on_failure continue` marks a step that must not unwind what came before,
because a failed confirmation should not reverse a settled loan

---

## weft

schemas, migrations, lineage

```weft
schema Applicant v1 {
  field id: Text key
  field email: Text classify personal unique
  field legal_name: Text classify personal
  field annual_income: Int
  retention 2555 days
  index email
  invariant annual_income >= 0
}

schema Applicant v2 {
  field id: Text key
  field email: Text classify personal unique
  field legal_name: Text classify personal
  field annual_income: Int
  field months_employed: Int = 0
  retention 2555 days
  index email
  invariant annual_income >= 0
}

migrate Applicant v1 -> v2 {
  intent "Add employment tenure, defaulting existing records to unknown."
  forward months_employed = 0
}
```

every field that differs has to be accounted for, and a field added with no
value or default or removed with no way back is a compile error naming it

a migration you cannot reverse has to say `lossy`, otherwise both directions
get generated with an `invertible_by` law on them so the verifier runs the
round trip against generated records instead of you asserting it

```
ok  the round trip is checked by the verifier, not asserted:
    invertible_by verified over 40 generated records
```

classifications cannot weaken, `personal` in v1 cannot come out `public` in v2,
so renaming does not launder protected data

a pipeline lowers to a function plus a lineage record, which fields went where
and the highest classification that passed through, generated off the stages so
it cannot drift

---

## tract

infrastructure worked out from what the code can reach

```tract
resource api: HttpService {
  expose lending.origination.originate at "/loans/originate" method "POST"
  region "eu-west-1"
  scale_to 24
  quota rps 400
  budget money 900
}

resource loan_ledger: Table {
  schema LoanOffer
  key reference
  retention 2555 days
}

resource credit_bureau: ExternalService {
  provides bureau
  quota daily 20000
}
```

you declare what to expose and what has to be provisioned gets computed.
exposing a function whose call graph needs storage with no storage declared is a
compile error naming the capability, the function and the resource kinds that
would cover it

```
error[CANON-E0403]: lending.origination.originate needs 'ledger.append' but no
                    declared resource provides it
  resource_kinds_that_provide_it: ['Table']
```

so an endpoint's permissions and what it can actually reach are the same number.
resources nothing reaches get reported, and a public endpoint touching protected
data gets flagged

kinds are `HttpService`, `Table`, `Queue`, `Cache`, `ObjectStore`, `Mailer`,
`ModelAccess`, `Secret`, `Schedule`, `WorkflowEngine`, `ExternalService`, and
any resource can add `provides <effect>` for names tract does not know

---

## rune

policy, kept out of the code it governs so a policy change is its own thing
with its own review

```rune
policy underwriting_maintenance {
  intent "A maintenance agent may tune the decision, but not touch money or customers."
  actor "agent:underwriting"

  grant bureau.pull limit 500 calls
  grant model.infer, model.judge
  grant workflow.checkpoint, workflow.compensated

  deny ledger.append, ledger.reverse
  deny notify.email

  scope lending.underwriting.*, lending.affordability_ratio

  limit blast_radius 12
  limit classification pseudonymous
  limit tokens 200000
  limit money 25

  require_approval when new_capabilities, contracts_change, signature_change
  promote when verified and not diverged

  audit all
}
```

it compiles into the two objects already making the decisions, capability
grants for the broker and an authorisation for the gate, so it is enforced by
construction rather than consulted by convention

```
ok  a policy that denies money stops the workflow at the ledger:
    bureau.pull permitted, ledger.append refused at the boundary
```

denials beat grants and granting plus denying the same thing is a compile
error. wildcard grants, missing promotion conditions and missing blast radius
limits all get reported

approval triggers are `new_capabilities`, `contracts_change`,
`signature_change`, `behaviour_change`, `classification_increase`,
`intent_change`, `always`

promotion conditions are `verified`, `not_diverged`, `tests_pass`, `in_scope`,
`within_blast_radius`

---

## composition

since everything lowers to one ir, definitions out of different languages sit
in one graph

```
$ canon atlas blast affordability_ratio examples/lending
lending.affordability_ratio #ecpsvedi
  11 transitive dependents
  capabilities: bureau.pull, ledger.append, notify.email,
                workflow.checkpoint, workflow.compensated
  data: personal, pseudonymous
```

that one canon function gets called by a verdict factor, which gets called by a
loom workflow, which gets exercised by intent scenarios, deployed by a tract
resource and governed by a rune policy. editing it is one change with one blast
radius, one verification pass and one promotion decision
