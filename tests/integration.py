"""
End-to-end integration across the whole stack.

Loads the lending example -- seven files in seven languages -- and drives the
complete path an agent-authored change would take: check, specify, verify,
plan infrastructure, enforce policy at runtime, propose an edit, and let the
gate decide whether it ships.

This is the test that would catch the languages drifting apart from each
other, which unit tests inside each repository cannot.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for pkg in ("canon", "intent", "loom", "verdict", "weft", "tract", "rune"):
    sys.path.insert(0, str(ROOT / pkg / "src"))

EXAMPLE = ROOT / "kinode-stack" / "examples" / "lending"

from canon import Hasher, values as V  # noqa: E402
from canon.atlas import Atlas  # noqa: E402
from canon.interp import Budget, Fault, Interpreter, run_tests  # noqa: E402
from canon.ledger import AuditLog, CapabilityBroker, Ledger, REPLAY  # noqa: E402
from canon.shadow import structural_diff  # noqa: E402
from canon.sources import check_workspace, load  # noqa: E402
from canon.verifier import Verifier  # noqa: E402
import intent as intent_lang  # noqa: E402
import loom as loom_lang  # noqa: E402
import rune as rune_lang  # noqa: E402
import tract as tract_lang  # noqa: E402


def main():
    failures = []

    def case(name, fn):
        try:
            print(f"  ok    {name}: {fn()}")
        except AssertionError as ae:
            failures.append(name)
            print(f"  FAIL  {name}: {ae}")

    # ---------------------------------------------------------------
    print("loading a seven-language workspace")

    ws = load([str(EXAMPLE)])
    assert not ws.bag.has_errors, ws.bag.render()
    cr = check_workspace(ws)
    if cr.bag.has_errors:
        for d in cr.bag:
            if d.severity.value == "error":
                print(d.render(ws.sources.get(d.span.start.file)))
        return 1
    defs = Hasher().add_modules(cr.modules)
    hashes = {qn: di.hash for qn, di in defs.items()}
    atlas = Atlas(cr, defs, sources=ws.sources)

    def t_loaded():
        s = ws.summary()
        assert s["files"] == 7, s
        langs = set(s["by_language"])
        assert langs == {"canon", "weft", "verdict", "loom", "tract",
                         "rune", "intent"}, langs
        return f"{s['files']} files, {len(defs)} definitions, {len(langs)} languages"
    case("all seven languages load into one workspace", t_loaded)

    def t_one_graph():
        # A Canon helper, a Verdict decision and a Loom workflow in one graph.
        callers = atlas.callers("affordability_ratio", transitive=True)
        assert any(c.startswith("lending.underwriting.") for c in callers), callers
        assert any(c.startswith("lending.origination.") for c in callers), callers
        assert any(c.startswith("lending.goals") for c in callers), callers
        return (f"editing one Canon function reaches {len(callers)} "
                f"definitions across Verdict, Loom and Intent")
    case("definitions from different languages share one graph", t_one_graph)

    # ---------------------------------------------------------------
    print("\nspecification conformance")

    def spec_ledger():
        audit = AuditLog(actor="spec")
        broker = CapabilityBroker(audit=audit)
        broker.grant("spec", ["*"], reason="specification run")
        return Ledger(broker=broker, audit=audit, actor="spec")

    def t_conformance():
        results = run_tests(cr, spec_ledger())
        rep = intent_lang.conformance(ws.goals, cr, hashes, results)
        assert rep.ok, rep.render()
        return (f"{len(rep.goals)} goals satisfied by "
                f"{sum(g.scenarios_passed for g in rep.goals)} scenarios")
    case("every stated goal is satisfied by the implementation", t_conformance)

    def t_untraced():
        results = run_tests(cr, spec_ledger())
        rep = intent_lang.conformance(ws.goals, cr, hashes, results)
        assert "lending.monthly_instalment" in rep.untraced_definitions, \
            rep.untraced_definitions
        return (f"{len(rep.untraced_definitions)} definitions no goal asks "
                f"for: {rep.untraced_definitions}")
    case("code no goal traces to is reported", t_untraced)

    def t_drift():
        intent_lang.accept(ws.goals, cr, hashes)
        changed = dict(ws.sources)
        target = str(EXAMPLE / "domain.canon")
        changed[target] = changed[target].replace(
            "  Option.unwrap_or(Int.div(amount * 100, Int.max(annual_income, 1)), 100)",
            "  Int.max(0, Option.unwrap_or(Int.div(amount * 100, Int.max(annual_income, 1)), 100))")
        ws2 = load([])
        for name, text in changed.items():
            from canon.sources import load_text
            load_text(text, name, ws2)
        cr2 = check_workspace(ws2)
        assert not cr2.bag.has_errors, cr2.bag.render()
        hashes2 = {qn: di.hash
                   for qn, di in Hasher().add_modules(cr2.modules).items()}
        results2 = run_tests(cr2, spec_ledger())
        assert all(r["passed"] for r in results2), \
            "the edit was supposed to preserve behaviour"
        rep = intent_lang.conformance(ws.goals, cr2, hashes2, results2)
        stale = [s for g in rep.goals for s in g.stale_traces]
        assert stale, "a changed traced definition did not report as stale"
        return (f"scenarios still pass, but {len(stale)} goal trace(s) went "
                f"stale on {stale[0]['definition']}")
    case("a behaviour-preserving edit still reports its goals as stale",
         t_drift)

    # ---------------------------------------------------------------
    print("\ninfrastructure derived from the code")

    def t_manifest():
        manifest = tract_lang.plan("", cr, ws.resources, cr.bag,
                                   "lending.platform")
        errs = [d for d in cr.bag if d.severity.value == "error"]
        assert not errs, [d.message for d in errs]
        ep = next(e for e in manifest.endpoints
                  if e.path == "/loans/originate")
        assert "ledger.append" in ep.capabilities, ep.capabilities
        assert ep.satisfied_by["ledger.append"] == "loan_ledger", \
            ep.satisfied_by
        assert ep.satisfied_by["notify.email"] == "postbox", ep.satisfied_by
        return (f"{len(manifest.endpoints)} endpoints, budget "
                f"{manifest.total_money_budget}, every capability attributed")
    case("the deployment manifest is derived from the call graph", t_manifest)

    # ---------------------------------------------------------------
    print("\npolicy enforced at runtime")

    policies = {p.name: p for p in ws.policies}

    def build_runtime(policy_name, scripted):
        audit = AuditLog(actor="agent:test")
        broker = CapabilityBroker(audit=audit)
        policies[policy_name].install(broker, actor="agent:test")
        led = Ledger(broker=broker, audit=audit, actor="agent:test")
        loom_lang.install(led)
        for key, fn in scripted.items():
            led.handle(key, fn)
        return led

    def handlers(fail=()):
        def bureau_pull(applicant_id):
            if "bureau.pull" in fail:
                return V.err(V.Variant("BureauUnavailable", (),
                                       "OriginationError"))
            return V.ok(742)

        def ledger_append(reference, amount):
            if "ledger.append" in fail:
                return V.err(V.Variant("LedgerRejected", (),
                                       "OriginationError"))
            return V.ok("staged-" + reference)

        def ledger_commit(reference):
            if "ledger.commit" in fail:
                return V.err(V.Variant("LedgerRejected", (),
                                       "OriginationError"))
            return V.ok("settled-" + reference)

        return {
            "bureau.pull": bureau_pull,
            "ledger.append": ledger_append,
            "ledger.commit": ledger_commit,
            "ledger.reverse": lambda r: V.UNIT,
            "notify.email": lambda a, b, c: V.ok("sent"),
        }

    def applicant(score=742, income=90000, months=36):
        return V.Record("ApplicantV2", (
            ("id", "a-1"), ("email", "a@example.com"),
            ("legal_name", "A Person"), ("annual_income", income),
            ("credit_score", score), ("months_employed", months)))

    def request(amount=20000, term=48):
        return V.Record("LoanRequest", (
            ("reference", "LN-1"), ("applicant_id", "a-1"),
            ("amount_requested", amount), ("term_months", term)))

    def t_underwriting_policy_denies_money():
        # The underwriting agent may pull a bureau file but must not book a
        # loan. Running the origination workflow under its policy must stop
        # at the ledger.
        led = build_runtime("underwriting_maintenance", handlers())
        it = Interpreter(cr, led, Budget(), hashes)
        try:
            it.call("originate", [request(), applicant()])
        except Fault as f:
            assert f.code == "CANON-E0403", f.code
            assert f.facts.get("operation") == "ledger.append", f.facts
            return (f"bureau.pull permitted, ledger.append refused at the "
                    f"boundary")
        raise AssertionError("the underwriting policy let a loan be booked")
    case("a policy that denies money stops the workflow at the ledger",
         t_underwriting_policy_denies_money)

    def t_release_policy_runs():
        # A wider policy, granting everything the workflow needs.
        audit = AuditLog(actor="ops")
        broker = CapabilityBroker(audit=audit)
        broker.grant("ops", ["bureau.*", "ledger.*", "notify.*", "workflow.*"],
                     reason="integration run")
        led = Ledger(broker=broker, audit=audit, actor="ops")
        loom_lang.install(led)
        for key, fn in handlers().items():
            led.handle(key, fn)
        it = Interpreter(cr, led, Budget(), hashes)
        out = it.call("originate", [request(), applicant()])
        assert V.is_ok(out), V.show(out)
        offer = out.args[0]
        assert offer.get("annual_rate_basis_points") > 0, V.show(offer)
        trace = loom_lang.trace_of(led)
        assert trace.steps_started() == ["credit_file", "booking",
                                         "settlement", "confirmation"], \
            trace.steps_started()
        return (f"approved at {offer.get('annual_rate_basis_points')}bp, "
                f"steps {trace.steps_started()}")
    case("under a sufficient policy the whole workflow runs",
         t_release_policy_runs)

    def run_with(fail):
        audit = AuditLog(actor="ops")
        broker = CapabilityBroker(audit=audit)
        broker.grant("ops", ["*"], reason="integration run")
        led = Ledger(broker=broker, audit=audit, actor="ops")
        loom_lang.install(led)
        calls = []
        for key, fn in handlers(fail=fail).items():
            def wrap(*a, _k=key, _f=fn):
                calls.append(_k)
                return _f(*a)
            led.handle(key, wrap)
        it = Interpreter(cr, led, Budget(), hashes)
        return it.call("originate", [request(), applicant()]), led, calls

    def t_stage_failure():
        out, led, calls = run_with(["ledger.append"])
        assert V.is_err(out), V.show(out)
        trace = loom_lang.trace_of(led)
        # Staging failed, so there is nothing staged to reverse. Pulling a
        # credit file cannot be undone and declares no compensation.
        assert not trace.compensations, trace.compensations
        assert "ledger.reverse" not in calls, calls
        return (f"staging failed, returned {V.show(out.args[0])}, "
                f"nothing to undo")
    case("a failed staging unwinds nothing", t_stage_failure)

    def t_settlement_failure():
        # The case the two-phase booking exists for: staging succeeded, the
        # commit failed, and the staged entry must be reversed.
        out, led, calls = run_with(["ledger.commit"])
        assert V.is_err(out), V.show(out)
        trace = loom_lang.trace_of(led)
        assert [s for _, s in trace.compensations] == ["booking"], \
            trace.compensations
        assert "ledger.reverse" in calls, calls
        assert "notify.email" not in calls, \
            "the customer was told about a loan that was rolled back"
        return (f"settlement failed, staged entry reversed, customer not "
                f"notified")
    case("a failed settlement reverses the staged booking",
         t_settlement_failure)

    def t_resume():
        audit = AuditLog(actor="ops")
        broker = CapabilityBroker(audit=audit)
        broker.grant("ops", ["*"], reason="integration run")
        led = Ledger(broker=broker, audit=audit, actor="ops")
        loom_lang.install(led)
        for key, fn in handlers().items():
            led.handle(key, fn)
        first = Interpreter(cr, led, Budget(), hashes).call(
            "originate", [request(), applicant()])

        calls = []
        audit2 = AuditLog(actor="ops")
        broker2 = CapabilityBroker(audit=audit2)
        broker2.grant("ops", ["*"], reason="resume")
        led2 = Ledger(broker=broker2, audit=audit2, mode=REPLAY, actor="ops")
        led2._source = led.journal
        loom_lang.install(led2)
        for key in handlers():
            led2.handle(key, lambda *a, _k=key: calls.append(_k))
        second = Interpreter(cr, led2, Budget(), hashes).call(
            "originate", [request(), applicant()])

        assert V.compare(first, second) == 0, "resumption changed the outcome"
        assert not calls, f"resumption re-performed effects: {calls}"
        return (f"replayed {len(led.journal)} journal entries, no external "
                f"call repeated, identical offer")
    case("an interrupted origination resumes without re-billing the bureau",
         t_resume)

    # ---------------------------------------------------------------
    print("\nverification")

    def t_verify():
        v = Verifier(cr, seed="kinode", runs=30, hashes=hashes)
        targets = ["lending.affordability_ratio", "lending.monthly_instalment",
                   "lending.rate_for", "lending.build_offer",
                   "lending.underwriting.assess",
                   "lending.data.migrate_applicant_v1_v2"]
        rep = v.verify_all(only=targets)
        bad = [f.qualname for f in rep.functions if not f.ok]
        assert not bad, [f.to_json() for f in rep.functions if not f.ok]
        return (f"{len(rep.functions)} definitions verified over "
                f"{sum(f.runs for f in rep.functions)} generated cases")
    case("contracts and laws hold across Canon, Verdict and Weft", t_verify)

    # ---------------------------------------------------------------
    print("\nthe promotion gate")

    def propose(replacement):
        changed = dict(ws.sources)
        target = str(EXAMPLE / "underwriting.verdict")
        changed[target] = changed[target].replace(*replacement)
        assert changed[target] != ws.sources[target], "the edit did not apply"
        return atlas.propose({target: changed[target]}, actor="agent:underwriting")

    def t_in_policy_promote():
        # Tighten the credit floor: in scope, no new capabilities.
        p = propose(("    when score < 560", "    when score < 580"))
        assert p.ok, p.render_diagnostics()
        diff = structural_diff(atlas.cr, p.result, atlas.defs,
                               p.new_atlas.defs)
        decision = rune_lang.evaluate(
            policies["underwriting_maintenance"], diff,
            verification={"ok": True, "functions": []},
            differential_report={"identical": False,
                                 "disagreements": [{"function":
                                                    "lending.underwriting.assess"}]})
        # Behaviour changed on purpose, and the policy requires no divergence.
        assert decision.decision == "block", decision.render()
        return "a deliberate behaviour change is held for a human, as written"
    case("a decision change is held back by promote-when-not-diverged",
         t_in_policy_promote)

    def t_reason_removed():
        # Removing a stated reason must not even compile.
        target = str(EXAMPLE / "underwriting.verdict")
        text = ws.sources[target].replace(
            '    because "The credit score is below the published floor of 560."\n',
            "")
        p = atlas.propose({target: text}, actor="agent:underwriting")
        assert not p.ok, "a rule without a reason was accepted"
        d = next(x for x in p.diagnostics()
                 if "does not state a reason" in x["message"])
        return d["message"]
    case("an edit that removes an explanation cannot be proposed",
         t_reason_removed)

    def t_prohibited_edit():
        # Using a prohibited field is rejected at the proposal stage.
        target = str(EXAMPLE / "underwriting.verdict")
        text = ws.sources[target].replace(
            "    when score < 560",
            '    when score < 560 and input.applicant.legal_name != ""')
        p = atlas.propose({target: text}, actor="agent:underwriting")
        assert not p.ok, "a prohibited factor was accepted"
        d = next(x for x in p.diagnostics() if x["code"] == "CANON-E0903")
        return d["message"]
    case("an edit reaching a prohibited factor cannot be proposed",
         t_prohibited_edit)

    def t_out_of_scope():
        # The underwriting policy's scope does not include origination.
        target = str(EXAMPLE / "origination.loom")
        text = ws.sources[target].replace("    retry 2", "    retry 3")
        p = atlas.propose({target: text}, actor="agent:underwriting")
        assert p.ok, p.render_diagnostics()
        diff = structural_diff(atlas.cr, p.result, atlas.defs,
                               p.new_atlas.defs)
        decision = rune_lang.evaluate(
            policies["underwriting_maintenance"], diff,
            verification={"ok": True, "functions": []},
            differential_report={"identical": True, "disagreements": []})
        assert decision.decision == "block", decision.render()
        f = next(x for x in decision.findings if x.code == "CANON-E0905")
        return f.message
    case("an edit outside the policy's scope is blocked", t_out_of_scope)

    def t_data_policy_scope():
        # The data agent may change schemas; the underwriting agent may not.
        target = str(EXAMPLE / "customers.weft")
        text = ws.sources[target].replace(
            "  field months_employed: Int = 0\n  retention 2555 days\n  index email\n"
            "  invariant annual_income >= 0\n  invariant credit_score >= 0\n"
            "  invariant months_employed >= 0\n",
            "  field months_employed: Int = 0\n  field marketing_opt_in: Bool = false\n"
            "  retention 2555 days\n  index email\n"
            "  invariant annual_income >= 0\n  invariant credit_score >= 0\n"
            "  invariant months_employed >= 0\n")
        p = atlas.propose({target: text}, actor="agent:data")
        assert p.ok, p.render_diagnostics()
        diff = structural_diff(atlas.cr, p.result, atlas.defs,
                               p.new_atlas.defs)

        allowed = rune_lang.evaluate(
            policies["data_maintenance"], diff,
            verification={"ok": True, "functions": []},
            differential_report={"identical": True, "disagreements": []})
        refused = rune_lang.evaluate(
            policies["underwriting_maintenance"], diff,
            verification={"ok": True, "functions": []},
            differential_report={"identical": True, "disagreements": []})
        assert refused.decision == "block", refused.render()
        return (f"data agent: {allowed.decision}, "
                f"underwriting agent: {refused.decision}")
    case("the same edit is judged differently by two policies",
         t_data_policy_scope)

    print("\nRESULT:", "pass" if not failures else f"FAIL ({failures})")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
