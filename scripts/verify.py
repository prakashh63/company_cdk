"""Run every quality gate and print a PASS / FAIL / SKIP table.

Usage (inside the project's virtual environment):  python scripts/verify.py
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable
ENV = {**os.environ, "JSII_SILENCE_WARNING_DEPRECATED_NODE_VERSION": "1"}

results: list[tuple[str, str]] = []


def step(name: str, cmd: list[str], cwd: Path = ROOT) -> bool:
    print(f"\n>>> {name}\n$ {' '.join(cmd)}", flush=True)
    proc = subprocess.run(cmd, check=False, cwd=cwd, env=ENV, capture_output=True, text=True)
    ok = proc.returncode == 0
    tail = (proc.stdout + proc.stderr).strip().splitlines()[-30:]
    if not ok:
        print("\n".join(tail))
    results.append((name, "PASS" if ok else "FAIL"))
    return ok


def main() -> int:
    step("ruff format (auto-fixes style)", [PY, "-m", "ruff", "format", "."])
    step("ruff check", [PY, "-m", "ruff", "check", "."])
    step("mypy --strict", [PY, "-m", "mypy", "company_cdk", "tests"])

    if not (ROOT / "tests" / "snapshots" / "__snapshots__").exists():
        step(
            "snapshots (first run creates them)",
            [PY, "-m", "pytest", "tests/snapshots", "--snapshot-update", "-q"],
        )
    step("pytest", [PY, "-m", "pytest", "-q"])

    cdk = shutil.which("cdk")
    if cdk is None:
        results.append(("cdk synth (CDK CLI not found: npm install -g aws-cdk)", "SKIP"))
    else:
        app_cmd = f'"{PY}" app.py'
        step(
            "cdk synth: web app example (includes cdk-nag gate)",
            [cdk, "synth", "--quiet", "--app", app_cmd],
            cwd=ROOT / "examples",
        )
        step(
            "cdk synth: worker example (SNS + EventBridge, no API)",
            [cdk, "synth", "--quiet", "--app", app_cmd],
            cwd=ROOT / "examples" / "worker",
        )

    print("\n" + "=" * 60)
    for name, status in results:
        print(f"  [{status}] {name}")
    print("=" * 60)
    return 1 if any(status == "FAIL" for _, status in results) else 0


if __name__ == "__main__":
    sys.exit(main())
