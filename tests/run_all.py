"""
Run every test suite across every repository.

Each language repository owns its own tests; this runs all of them plus the
cross-language integration suite, so a change to Canon that breaks Loom is
caught here rather than by whoever next touches Loom.
"""

import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SUITES = [
    ("canon", "smoke_frontend", "lexer, parser, canonical form, hashing"),
    ("canon", "smoke_checker", "types, effects, exhaustiveness"),
    ("canon", "smoke_interp", "evaluation, contracts, budgets"),
    ("canon", "smoke_ledger", "journal, capabilities, replay, shadow"),
    ("canon", "smoke_verify", "verification, differential, promotion gate"),
    ("canon", "smoke_atlas", "graph queries, projections, transactions"),
    ("canon", "smoke_protocol", "the agent interface"),
    ("intent", "smoke_intent", "specifications and drift detection"),
    ("verdict", "smoke_verdict", "decisions and reason trees"),
    ("loom", "smoke_loom", "workflows, compensation, resumption"),
    ("weft", "smoke_weft", "schemas, migrations, lineage"),
    ("tract", "smoke_tract", "derived infrastructure"),
    ("rune", "smoke_rune", "governance policy"),
]

INTEGRATION = ("kinode-stack", "integration",
               "all seven languages end to end")


def run(repo, name, description) -> tuple:
    path = ROOT / repo / "tests" / f"{name}.py"
    if not path.exists():
        return (repo, name, "missing", 0.0, "no such file")
    started = time.monotonic()
    proc = subprocess.run([sys.executable, str(path)],
                          capture_output=True, text=True, cwd=str(ROOT / repo))
    elapsed = time.monotonic() - started
    tail = (proc.stdout.strip().splitlines() or ["(no output)"])[-1]
    status = "pass" if proc.returncode == 0 else "FAIL"
    return (repo, name, status, elapsed, tail, proc)


def main() -> int:
    results = []
    width = max(len(f"{r}/{n}") for r, n, _ in SUITES + [INTEGRATION])

    print("running every suite in the workspace\n")
    for repo, name, description in SUITES + [INTEGRATION]:
        r = run(repo, name, description)
        results.append(r)
        label = f"{r[0]}/{r[1]}".ljust(width)
        print(f"  {r[2]:4}  {label}  {r[3]:5.2f}s  {description}")
        if r[2] == "FAIL":
            proc = r[5]
            for line in (proc.stdout + proc.stderr).splitlines():
                if "FAIL" in line or "Error" in line or "error" in line:
                    print(f"         {line}")

    failed = [r for r in results if r[2] != "pass"]
    total = sum(r[3] for r in results)
    print(f"\n{len(results) - len(failed)}/{len(results)} suites passed "
          f"in {total:.1f}s")
    if failed:
        print("failed: " + ", ".join(f"{r[0]}/{r[1]}" for r in failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
