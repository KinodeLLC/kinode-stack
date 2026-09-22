# Diagnostics

every diagnostic is a structured object with a stable code, a severity, a
source span, machine readable facts, and a concrete fix where there is one.
the text you read gets generated off that structure, nothing downstream
parses the rendered output.

codes are public api. new ones get added, existing ones do not change what
they mean.

## errors

### lexing

| code | means |
| --- | --- |
| `CANON-E0001` | unexpected character |
| `CANON-E0002` | unterminated text literal |
| `CANON-E0003` | invalid numeric literal |
| `CANON-E0004` | unterminated block comment |
| `CANON-E0005` | tab character in source (canonical form uses spaces) |

### parsing

| code | means |
| --- | --- |
| `CANON-E0101` | unexpected token |
| `CANON-E0102` | expected a declaration |
| `CANON-E0103` | expected an expression |
| `CANON-E0104` | expected a type |
| `CANON-E0105` | unclosed delimiter |
| `CANON-E0106` | duplicate clause |
| `CANON-E0107` | missing module header |
| `CANON-E0108` | expected a pattern |

### naming

| code | means |
| --- | --- |
| `CANON-E0201` | unknown name |
| `CANON-E0202` | unknown type |
| `CANON-E0203` | duplicate definition |
| `CANON-E0204` | unknown effect |
| `CANON-E0205` | unknown effect operation |
| `CANON-E0206` | unknown field |
| `CANON-E0207` | unknown constructor |
| `CANON-E0208` | unknown module |
| `CANON-E0209` | cyclic definition |

### types

| code | means |
| --- | --- |
| `CANON-E0301` | type mismatch |
| `CANON-E0302` | wrong number of arguments |
| `CANON-E0303` | not callable |
| `CANON-E0304` | field access on non-record |
| `CANON-E0305` | non-exhaustive match |
| `CANON-E0306` | unreachable match arm |
| `CANON-E0307` | branches have different types |
| `CANON-E0308` | cannot infer type |
| `CANON-E0309` | constructor arity mismatch |
| `CANON-E0310` | error propagation outside Result-returning function |
| `CANON-E0311` | recursive definition without a decreases clause |
| `CANON-E0312` | type argument mismatch |

### effects

| code | means |
| --- | --- |
| `CANON-E0401` | undeclared effect |
| `CANON-E0402` | declared effect is never used |
| `CANON-E0403` | capability not granted |
| `CANON-E0404` | effect performed in a pure context |
| `CANON-E0405` | capability escalation across call boundary |
| `CANON-E0406` | effect operation outside its declared effect |

### contracts

| code | means |
| --- | --- |
| `CANON-E0501` | precondition not satisfiable |
| `CANON-E0502` | postcondition violated by counterexample |
| `CANON-E0503` | law violated by counterexample |
| `CANON-E0504` | contract references an unbound name |
| `CANON-E0505` | unknown law |
| `CANON-E0506` | law arity mismatch |
| `CANON-E0507` | precondition violated at runtime |
| `CANON-E0508` | postcondition violated at runtime |

### totality and cost

| code | means |
| --- | --- |
| `CANON-E0601` | step budget exceeded |
| `CANON-E0602` | io budget exceeded |
| `CANON-E0603` | declared cost exceeded under verification |
| `CANON-E0604` | unbounded recursion detected |
| `CANON-E0605` | decreases clause does not decrease |

### runtime

| code | means |
| --- | --- |
| `CANON-E0701` | division by zero |
| `CANON-E0702` | index out of bounds |
| `CANON-E0703` | key not found |
| `CANON-E0704` | arithmetic overflow |
| `CANON-E0705` | pattern match failure |
| `CANON-E0706` | explicit abort |

### journal and replay

| code | means |
| --- | --- |
| `CANON-E0801` | journal divergence: operation mismatch |
| `CANON-E0802` | journal divergence: argument mismatch |
| `CANON-E0803` | journal exhausted during replay |
| `CANON-E0804` | nondeterminism detected |
| `CANON-E0805` | journal integrity: hash chain broken |

### governance

| code | means |
| --- | --- |
| `CANON-E0901` | definition hash not found |
| `CANON-E0902` | edit transaction conflict |
| `CANON-E0903` | promotion blocked by policy |
| `CANON-E0904` | behavioral regression detected in shadow |
| `CANON-E0905` | blast radius exceeds authorization |

## warnings

| code | means |
| --- | --- |
| `CANON-W0001` | unused binding |
| `CANON-W0002` | unused parameter |
| `CANON-W0003` | shadowed binding |
| `CANON-W0004` | function has no contracts |
| `CANON-W0005` | function has no intent |
| `CANON-W0006` | broad capability requested |
| `CANON-W0007` | non-canonical formatting |
| `CANON-W0008` | law is untested (no generator for parameter type) |

## laws

named properties the verifier checks against generated inputs.

| law | args | means |
| --- | --- | --- |
| `associative` | 0 | f(f(a, b), c) == f(a, f(b, c)). |
| `bounded_output` | 1 | The result's size never exceeds the given bound. |
| `commutative` | 0 | f(a, b) == f(b, a). |
| `conserves` | 1 | The named quantity is the same before and after. |
| `deterministic` | 0 | Same inputs always give the same result. |
| `explains` | 0 | The result carries a reason for every factor used. |
| `grounded` | 0 | Every claim in the output is supported by the inputs. |
| `idempotent_by` | 1 | Calling twice with the same key has the same effect as calling once. |
| `injective` | 0 | Distinct inputs give distinct outputs. |
| `invertible_by` | 1 | Applying the named function to the result recovers the original input. |
| `monotonic_in` | 1 | Increasing the named parameter never decreases the result. |
| `never_negative` | 0 | The result is never negative. |
| `order_independent` | 0 | The result does not depend on input order. |
| `pure` | 0 | Performs no effects. |
| `total` | 0 | Defined for every input satisfying the preconditions. |

## retry reasons

what you can put after `retries N on ...` in an `ask`.

| reason | fires when |
| --- | --- |
| `type_error` | the response did not fit the declared type |
| `contract_violation` | the result failed an `ensures` clause |
| `grounding_failure` | the output was not backed by the grounding sources |
| `judge_rejected` | a `judge` clause turned it down |
| `refusal` | the model declined |
| `timeout` | it did not come back in time |

## classifications

least to most sensitive. a grant can cap what an actor reaches and a weft
migration cannot weaken one.

| rank | classification |
| --- | --- |
| 0 | `public` |
| 1 | `internal` |
| 2 | `confidential` |
| 3 | `pseudonymous` |
| 4 | `personal` |
| 5 | `sensitive` |
| 6 | `restricted` |
