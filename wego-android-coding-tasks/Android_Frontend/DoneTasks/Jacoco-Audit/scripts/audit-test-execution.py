#!/usr/bin/env python3
"""
Audit whether every unit-test file in the repo actually gets executed by the
Jacoco script — i.e. produces an .exec file that the aggregate report consumes.

Method:
  1. For every module, count *Test*.kt / *Test*.java under src/test/java.
  2. For every module, look for an .exec file at any of the candidate paths
     the script checks (see script-jacoco.gradle aggregateCoverageReport).
  3. Cross-correlate:
       module has tests AND has exec    → OK
       module has tests AND no exec     → MISSING (script not running these tests
                                                   or running with the wrong task)
       module has no tests AND has exec → odd but harmless (empty exec)
       module has no tests AND no exec  → expected (skip)

Output: TSV lines `<module>\t<status>\t<test_count>\t<exec_path_or_empty>`
"""
import os
import sys

REPO_ROOT = "/Users/zeeshanarif/Documents/GitHub/newandroid/wego-android-n"

# Candidate exec paths the script-jacoco.gradle aggregateCoverageReport task checks.
EXEC_CANDIDATES = [
    "build/outputs/unit_test_code_coverage/playstoreDebugUnitTest/testPlaystoreDebugUnitTest.exec",
    "build/jacoco/testPlaystoreDebugUnitTest.exec",
    "build/outputs/unit_test_code_coverage/debug/testDebugUnitTest.exec",
    "build/jacoco/testDebugUnitTest.exec",
]


def count_tests(module_path: str) -> int:
    """Count test files under <module>/src/test/java."""
    src_test = os.path.join(module_path, "src", "test", "java")
    if not os.path.isdir(src_test):
        return 0
    n = 0
    for dirpath, _dirnames, filenames in os.walk(src_test):
        for fn in filenames:
            if fn.endswith(".kt") or fn.endswith(".java"):
                n += 1
    return n


def find_exec(module_path: str) -> str:
    """Return the relative path of the first matching exec, or ''."""
    for cand in EXEC_CANDIDATES:
        full = os.path.join(module_path, cand)
        if os.path.isfile(full):
            return os.path.relpath(full, REPO_ROOT)
    return ""


def main() -> int:
    print(f"# Repo root: {REPO_ROOT}", file=sys.stderr)
    rows = []
    for entry in sorted(os.listdir(REPO_ROOT)):
        module_path = os.path.join(REPO_ROOT, entry)
        if not os.path.isdir(module_path):
            continue
        # Heuristic: a module has a build.gradle (or build.gradle.kts).
        if not (
            os.path.isfile(os.path.join(module_path, "build.gradle"))
            or os.path.isfile(os.path.join(module_path, "build.gradle.kts"))
        ):
            continue
        n_tests = count_tests(module_path)
        exec_path = find_exec(module_path)

        if n_tests > 0 and exec_path:
            status = "OK"
        elif n_tests > 0 and not exec_path:
            status = "MISSING_EXEC"
        elif n_tests == 0 and exec_path:
            status = "EXEC_NO_TESTS"
        else:
            status = "NO_TESTS"

        rows.append((entry, status, n_tests, exec_path))

    # Print in 4 sections: MISSING_EXEC first (the bug list), then OK, then others
    by_status = {"MISSING_EXEC": [], "OK": [], "EXEC_NO_TESTS": [], "NO_TESTS": []}
    for r in rows:
        by_status[r[1]].append(r)

    for status in ("MISSING_EXEC", "EXEC_NO_TESTS", "NO_TESTS", "OK"):
        for module, _, n, ep in by_status[status]:
            print(f"{module}\t{status}\t{n}\t{ep}")

    print(file=sys.stderr)
    print(f"# OK             : {len(by_status['OK'])} modules", file=sys.stderr)
    print(f"# MISSING_EXEC   : {len(by_status['MISSING_EXEC'])} modules (BUGS)", file=sys.stderr)
    print(f"# EXEC_NO_TESTS  : {len(by_status['EXEC_NO_TESTS'])} modules", file=sys.stderr)
    print(f"# NO_TESTS       : {len(by_status['NO_TESTS'])} modules", file=sys.stderr)
    print(file=sys.stderr)
    print(
        f"# Total tests in OK modules: {sum(n for _, _, n, _ in by_status['OK'])}",
        file=sys.stderr,
    )
    print(
        f"# Total tests in MISSING_EXEC modules: {sum(n for _, _, n, _ in by_status['MISSING_EXEC'])}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
