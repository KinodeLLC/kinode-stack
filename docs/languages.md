# The languages

Seven surface languages over one core IR. Each is shaped by one question: what
does this domain need to make machine-checkable that a general-purpose language
leaves to convention?

All examples below are taken from
[`examples/lending`](../examples/lending), which checks and runs.

---

## Canon

The core. Everything else lowers to it.

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

### Function clauses

| Clause | Meaning |
| --- | --- |
| `intent "..."` | What this is for. Part of the hash, and what Intent matches against. |
| `uses a.b, c.d` | Every effect operation this may perform. Not inferred. |
| `requires <expr>` | Precondition, checked on entry and used to filter generated inputs. |
| `ensures <expr>` | Postcondition, with `result` and `old(...)` in scope. |
| `law <name>` | A named property the verifier checks against generated inputs. |
| `cost steps N, io N, tokens N, millis N, money N` | Resource ceiling, enforced at runtime and compared against observed usage. |
| `decreases <expr>` | Required for recursion. The measure must strictly decrease. |

### Laws

`deterministic`, `pure`, `total`, `idempotent_by(key)`, `commutative`,
`associative`, `monotonic_in(param)`, `conserves(field)`,
`bounded_output(n)`, `never_negative`, `order_independent`, `injective`,
`invertible_by(fn)`, `grounded`, `explains`.

### Types

`Int` (arbitrary precision), `Dec` (exact decimal), `Text`, `Bool`, `Unit`,
`Bytes`, `Time`, `List<T>`, `Set<T>`, `Map<K,V>`, `Option<T>`,
`Result<T,E>`, records, enums, `Fn(A) -> B uses e.op`.

No subtyping, no implicit conversion, no truthiness. Every function, lambda
parameter and record field is annotated, so the checker only instantiates
polymorphism rather than inferring it — which means a type error always points
at one site with a concrete expected and actual type.

### Things Canon will not let you write

```canon
a / b                  -- no division operator; use Int.div, which returns Option
if count then ... else -- no truthiness; compare explicitly
match c { case Red => 1 }   -- non-exhaustive
fn f(n: Int) -> Int { f(n) }  -- recursion with no decreases measure
a + b                  -- where a is Int and b is Dec
```

Each produces a diagnostic with a repair attached.

### The `ask` expression

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

Settings: `system`, `input [label:]`, `grounded_in`, `examples`,
`temperature`, `retries N on ...`, `max_tokens`, `judge`.

Retry reasons: `contract_violation`, `type_error`, `refusal`, `timeout`,
`grounding_failure`, `judge_rejected`.

Models are named by alias (`claude.opus`, `claude.sonnet`, `claude.haiku`,
`claude.fable`, `stub.deterministic`). Model capabilities are checked at
compile time.

---

## Intent

Specifications whose scenarios are executable and whose traces are pinned to
content hashes.

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

**Scenarios lower to Canon tests.** A specification that cannot be run is
rejected — a goal with no scenarios does not compile.

**Traces are pinned.** `accept` records the current hash of every traced
definition. When that definition changes, the goal reports as stale — including
when every scenario still passes, which is the case a test suite cannot catch:

```
FAIL A strong application is approved automatically
     scenarios 2/2
     changed since acceptance: lending.underwriting.assess (#7fa2 -> #b104)
```

**Untraced code is reported.** Code nobody asked for is as much a finding as a
goal nobody implemented.

**Non-functional requirements are checked against declared cost**, so
"must complete within 250ms" is compared to something the compiler knows.

---

## Verdict

Decisions that cannot compile unless they explain themselves.

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

Four structural guarantees:

1. **Every rule states a reason.** Omitting `because` is a parse error.
2. **Every decision has a default.** There is no input the decision cannot
   answer and no outcome without a recorded reason.
3. **Every factor states why it is used.** An unexplainable factor is not
   usable in a regulated decision.
4. **Prohibited factors are unreachable**, not merely unused. A field named in
   `prohibited` is rejected whether a rule reads it directly or reaches it
   through a factor, and the diagnostic names the route:

```
error[CANON-E0903]: rule 'below_credit_floor' depends on a prohibited field
  fields: ['input.applicant.legal_name']
  via_factors: ['tenure']
  note: A prohibited field reached through a factor is still a prohibited field.
```

Lowers to a result record carrying the outcome, the reasons and every factor
with its value, weight and basis, plus contracts asserting the result always
carries at least one reason and reports every factor considered.

---

## Loom

Durable workflows. Compensation sits next to the step it undoes; resumption is
journal replay.

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

**Step forms**: `step name = expr` names and binds; `step name: expr` names
without binding; `step expr` derives a name.

**Compensation is emitted explicitly.** The unwinding for every failure point
is written into the generated Canon rather than driven by a runtime stack, so
it is visible before it runs and provably in reverse order.

**Retries are unrolled, not looped.** This keeps every workflow total and keeps
the number of times an external system can be called a fact visible in the
source. Bounded at 8.

**Resumption is the Ledger's replay.** Each step checkpoints before it runs, so
a crashed workflow continues from the first step that never finished:

```
ok  an interrupted origination resumes without re-billing the bureau:
    replayed 8 journal entries, no external call repeated, identical offer
```

`on_failure continue` marks a step that must not unwind what came before — a
failed confirmation should not reverse a settled loan.

---

## Weft

Schemas, derived migrations, and data lineage.

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

**Every differing field must be accounted for.** A field added without a value
or default, or removed without a way back, is a compile error naming the field.

**Irreversible migrations must say so.** Otherwise both directions are
generated with an `invertible_by` law attached, so the round trip is checked by
the verifier against generated records rather than asserted:

```
ok  the round trip is checked by the verifier, not asserted:
    invertible_by verified over 40 generated records
```

**Classifications cannot weaken.** A field `personal` in v1 cannot be `public`
in v2, so a rename cannot launder protected data.

**Pipelines derive lineage.** A pipeline lowers to a function plus a lineage
record — which fields flowed where, and the highest classification that passed
through — generated from the stages rather than maintained alongside them.

---

## Tract

Infrastructure derived from the program's capability footprint.

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

You declare what to **expose**; what must be **provisioned** is computed.
Exposing a function whose call graph needs storage, with no storage declared,
is a compile error naming the capability, the function and the resource kinds
that would provide it:

```
error[CANON-E0403]: lending.origination.originate needs 'ledger.append' but no
                    declared resource provides it
  resource_kinds_that_provide_it: ['Table']
  note: The capability comes from the function's call graph, not from a
        declaration, so this is what the endpoint will actually try to do.
```

An endpoint's permissions and its actual reach are the same number by
construction. Resources nothing reaches are reported, and a public endpoint
touching protected data is flagged.

Kinds: `HttpService`, `Table`, `Queue`, `Cache`, `ObjectStore`, `Mailer`,
`ModelAccess`, `Secret`, `Schedule`, `WorkflowEngine`, `ExternalService`. A
resource may also declare `provides <effect>` for vocabularies Tract does not
know.

---

## Rune

Governance policy. Kept a separate language from the code it governs, so a
policy change is its own artifact with its own review path.

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

A policy compiles to the two objects that already make the decisions:
**capability grants** for the broker, and an **authorisation** for the
promotion gate. It is enforced by construction rather than consulted by
convention.

```
ok  a policy that denies money stops the workflow at the ledger:
    bureau.pull permitted, ledger.append refused at the boundary
```

Denials beat grants, and a policy that both grants and denies an operation is a
compile error rather than a precedence puzzle. Wildcard grants, missing
promotion conditions and missing blast-radius limits are reported.

Approval triggers: `new_capabilities`, `contracts_change`, `signature_change`,
`behaviour_change`, `classification_increase`, `intent_change`, `always`.

Promotion conditions: `verified`, `not_diverged`, `tests_pass`, `in_scope`,
`within_blast_radius`.

---

## How they compose

Because everything lowers to one IR, definitions from different languages sit
in one graph:

```
$ canon atlas blast affordability_ratio examples/lending
lending.affordability_ratio #ecpsvedi
  11 transitive dependents
  capabilities: bureau.pull, ledger.append, notify.email,
                workflow.checkpoint, workflow.compensated
  data: personal, pseudonymous
```

That one Canon function is called by a Verdict factor, which is called by a
Loom workflow, which is exercised by Intent scenarios, deployed by a Tract
resource, and governed by a Rune policy. Editing it is one change with one
blast radius, one verification pass and one promotion decision.
