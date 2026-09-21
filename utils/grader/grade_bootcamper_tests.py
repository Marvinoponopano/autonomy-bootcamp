"""
Grades the tests the bootcamper wrote in ``tests/test_waypoint_utils.py``.

Gate 1 is that the tests pass on the real module with >= 90% branch
coverage. Gate 2 reruns them against each broken copy in
``grader/mutants/``, every one of which has to FAIL. Coverage alone proves
the code ran; the mutants prove the tests actually checked something.

Run from ``utils/``. Standard library only.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
MUTANTS_DIR = PROJECT_DIR / "grader" / "mutants"
BOOTCAMPER_TESTS = Path("tests") / "test_waypoint_utils.py"
TARGET_MODULE = Path("src") / "waypoint_utils.py"
COVERAGE_MINIMUM = 90


def _run_pytest(cwd: Path, extra_args: list[str]) -> subprocess.CompletedProcess:
    """Run the bootcamper's tests with this interpreter.

    Same Python as the grader, so a passing run can't depend on which
    environment picked it up.
    """
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(BOOTCAMPER_TESTS),
        "-q",
        "-p",
        "no:cacheprovider",
        *extra_args,
    ]
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)


def _tail(text: str, lines: int = 15) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def _read_coverage(report_path: Path) -> float | None:
    """Read the coverage percentage out of pytest-cov's JSON report.

    Asking for the number directly beats scraping it off the terminal table,
    which changes shape with terminal width and pytest-cov version.

    Returns None if there's no readable report, which means pytest fell over
    before it measured anything.
    """
    try:
        return json.loads(report_path.read_text())["totals"]["percent_covered"]
    except (OSError, ValueError, KeyError):
        return None


def _gate_correct_code_and_coverage() -> bool:
    """Gate 1: tests pass on the real code, with >= 90% branch coverage.

    Runs first because a suite that fails on correct code can't say anything
    useful about broken code.
    """
    with tempfile.TemporaryDirectory(prefix="grade-coverage-") as temp:
        report_path = Path(temp) / "coverage.json"
        result = _run_pytest(
            PROJECT_DIR,
            [
                "--cov=src.waypoint_utils",
                "--cov-branch",
                f"--cov-fail-under={COVERAGE_MINIMUM}",
                # term for the bootcamper to read, json for us to check.
                "--cov-report=term",
                f"--cov-report=json:{report_path}",
            ],
        )
        coverage = _read_coverage(report_path)

    if result.returncode == 0:
        if coverage is None:
            print("GATE 1  PASS  suite green, coverage report unavailable")
        else:
            print(
                f"GATE 1  PASS  suite green, branch coverage "
                f"{coverage:.0f}% (>= {COVERAGE_MINIMUM}%)"
            )
        return True

    print("GATE 1  FAIL")
    if coverage is not None and coverage < COVERAGE_MINIMUM:
        print(
            f"  Branch coverage on {TARGET_MODULE} is {coverage:.0f}%, "
            f"below the {COVERAGE_MINIMUM}% gate."
        )
        print("  Write tests for the branches nothing has run yet")
        print("  (see the checklist in tests/test_waypoint_utils.py).")
    else:
        print("  Your tests do not pass against the real, correct module.")
        print("  Fix that first. Nothing else can be graded until it passes.")
    print("  --- pytest output (tail) ---")
    print(_tail(result.stdout + "\n" + result.stderr))
    return False


def _gate_mutants() -> bool:
    """Gate 2: every broken copy has to make the tests fail.

    Each one runs in a temp copy of the project, so nothing here can touch
    the real module.
    """
    mutants = sorted(MUTANTS_DIR.glob("mutant_*.py"))
    if not mutants:
        print("GATE 2  FAIL  no mutants found in grader/mutants/")
        return False

    survivors: list[str] = []
    print(f"GATE 2  running {len(mutants)} mutants...")
    for mutant in mutants:
        category = ""
        first_line = mutant.read_text().splitlines()[0]
        if ":" in first_line:
            category = first_line.split(":", 1)[1].strip()

        with tempfile.TemporaryDirectory(prefix="grade-mutant-") as temp:
            temp_dir = Path(temp)
            ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
            shutil.copytree(PROJECT_DIR / "src", temp_dir / "src", ignore=ignore)
            shutil.copytree(PROJECT_DIR / "tests", temp_dir / "tests", ignore=ignore)
            shutil.copy(PROJECT_DIR / "pyproject.toml", temp_dir / "pyproject.toml")
            shutil.copy(mutant, temp_dir / TARGET_MODULE)

            result = _run_pytest(temp_dir, [])

        killed = result.returncode != 0
        status = "killed  " if killed else "SURVIVED"
        print(f"  {mutant.name:<14} {status} {category}")
        if not killed:
            survivors.append(mutant.name)

    if survivors:
        print(f"GATE 2  FAIL  {len(survivors)} mutant(s) survived: {', '.join(survivors)}")
        print("  A survivor means none of your tests can tell it apart from")
        print("  the real code.")
        print("  Look it up in grader/mutants/MANIFEST.md and write a test for it.")
        return False

    print(f"GATE 2  PASS  all {len(mutants)} mutants killed")
    return True


def main() -> int:
    print(f"Grading {BOOTCAMPER_TESTS} in {PROJECT_DIR.name}/")

    if not _gate_correct_code_and_coverage():
        print("RESULT  FAIL (gate 1)")
        return 1

    if not _gate_mutants():
        print("RESULT  FAIL (gate 2)")
        return 1

    print("RESULT  PASS  nice work, your tests catch every bug we planted.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
