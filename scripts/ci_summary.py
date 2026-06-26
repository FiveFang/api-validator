"""Print a Markdown test summary from a JUnit XML file.

Used by CI to write a human-readable summary into the GitHub job output
(`$GITHUB_STEP_SUMMARY`). Dependency-free (stdlib only) so it runs even if the
test step failed.

Usage: python scripts/ci_summary.py reports/junit.xml
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def summarize(junit_path: str) -> str:
    path = Path(junit_path)
    if not path.exists():
        return f"### Test summary\n\n:warning: No JUnit report found at `{junit_path}`."

    root = ET.parse(path).getroot()
    suites = root.findall(".//testsuite") or [root]

    total = failures = errors = skipped = 0
    time = 0.0
    for s in suites:
        total += int(s.get("tests", 0))
        failures += int(s.get("failures", 0))
        errors += int(s.get("errors", 0))
        skipped += int(s.get("skipped", 0))
        time += float(s.get("time", 0) or 0)

    passed = total - failures - errors - skipped
    status = ":white_check_mark: PASS" if (failures + errors) == 0 else ":x: FAIL"

    lines = [
        "### API Validator — Test Summary",
        "",
        f"**Result:** {status}",
        "",
        "| Metric | Count |",
        "| --- | --- |",
        f"| Passed | {passed} |",
        f"| Failed | {failures} |",
        f"| Errors | {errors} |",
        f"| Skipped | {skipped} |",
        f"| Total | {total} |",
        f"| Duration | {time:.2f}s |",
        "",
    ]
    if skipped:
        lines.append(
            "> Skipped tests usually mean an environment's API token is not "
            "configured (e.g. `RESTCOUNTRIES_API_KEY`)."
        )
    return "\n".join(lines)


if __name__ == "__main__":
    junit = sys.argv[1] if len(sys.argv) > 1 else "reports/junit.xml"
    print(summarize(junit))
