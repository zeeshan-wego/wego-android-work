#!/usr/bin/env python3
"""
Compute SonarQube-style coverage from a Jacoco coverage.xml.

The team's reported coverage (~22%) is what SonarQube shows in PR comments.
SonarQube reads the same coverage.xml that Jacoco produces, but applies
`sonar.coverage.exclusions` from sonar-project.properties to filter out
source files BEFORE computing percentages. This script replicates that.

Method:
  1. Parse coverage.xml — collect every <sourcefile> with its LINE counter.
  2. Read sonar-project.properties — extract `sonar.coverage.exclusions`.
  3. For each <sourcefile>, build the source path the same way Sonar does:
       <package>/<sourcefile> → <module>/src/main/java/<package>/<sourcefile>
     (Sonar matches against module-relative source paths in sonar.sources.)
  4. Apply each exclusion pattern; drop matched files.
  5. Sum covered/total LINE counts on what remains.

Output: coverage % stats matching what SonarQube reports.
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

REPO = "/Users/zeeshanarif/Documents/GitHub/newandroid/wego-android-n"
SONAR_PROPS = os.path.join(REPO, "sonar-project.properties")


def read_sonar_exclusions(path: str, key: str) -> list[str]:
    """Read a multi-line, backslash-continued property value from sonar.properties."""
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    m = re.search(rf"^{re.escape(key)}\s*=\s*((?:.*\\\n)*.*)$", text, re.MULTILINE)
    if not m:
        return []
    raw = m.group(1)
    # split on commas (handling line continuations), strip whitespace and backslashes
    parts = re.split(r",\s*", raw.replace("\\\n", "").replace("\\", ""))
    return [p.strip() for p in parts if p.strip()]


def compile_ant_glob(pat: str) -> "re.Pattern[str]":
    out = []
    i, n = 0, len(pat)
    while i < n:
        c = pat[i]
        if c == "*":
            if i + 1 < n and pat[i + 1] == "*":
                if i + 2 < n and pat[i + 2] == "/":
                    out.append(r"(?:.*?/)?")
                    i += 3
                else:
                    out.append(r".*?")
                    i += 2
            else:
                out.append(r"[^/]*")
                i += 1
        elif c == "?":
            out.append(r"[^/]")
            i += 1
        elif c in ".+()|^${}\\[]":
            out.append("\\" + c)
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    return re.compile("^" + "".join(out) + "$")


def find_source_path(pkg: str, sf_name: str, source_index: dict) -> str:
    """Find the actual filesystem path of the source file. Falls back to the package guess."""
    key = f"{pkg}/{sf_name}" if pkg else sf_name
    return source_index.get(key, key)


def main(xml_path: str) -> int:
    # Build source-key → relative path index
    src_index_path = "/Users/zeeshanarif/Documents/GitHub/newandroid/wego-android-work/wego-android-coding-tasks/Android_Frontend/OnGoingTasks/Jacoco-Audit/data/source-index.tsv"
    source_index = {}
    with open(src_index_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                source_index[parts[0]] = parts[1]

    # Sonar exclusions
    cov_excl = read_sonar_exclusions(SONAR_PROPS, "sonar.coverage.exclusions")
    src_excl = read_sonar_exclusions(SONAR_PROPS, "sonar.exclusions")
    print(f"[sonar] sonar.coverage.exclusions: {len(cov_excl)} patterns", file=sys.stderr)
    print(f"[sonar] sonar.exclusions:          {len(src_excl)} patterns", file=sys.stderr)
    excl_regexes = [compile_ant_glob(p) for p in cov_excl + src_excl]

    # Parse coverage.xml: per-sourcefile LINE counter
    tree = ET.parse(xml_path)
    root = tree.getroot()
    total_kept_missed = 0
    total_kept_covered = 0
    total_drop_missed = 0
    total_drop_covered = 0
    kept_sources = 0
    dropped_sources = 0
    drop_examples_per_pat: dict[str, list[str]] = {}

    for pkg in root.findall("package"):
        pkg_name = pkg.get("name", "")
        for sf in pkg.findall("sourcefile"):
            sf_name = sf.get("name", "")
            line_counter = next((c for c in sf.findall("counter") if c.get("type") == "LINE"), None)
            missed = int(line_counter.get("missed", 0)) if line_counter is not None else 0
            covered = int(line_counter.get("covered", 0)) if line_counter is not None else 0

            src_path = find_source_path(pkg_name, sf_name, source_index)
            # Try matching exclusion patterns against the relative source path
            matched_pat = None
            for pat, rx in zip(cov_excl + src_excl, excl_regexes):
                if rx.match(src_path):
                    matched_pat = pat
                    break

            if matched_pat:
                dropped_sources += 1
                total_drop_missed += missed
                total_drop_covered += covered
                drop_examples_per_pat.setdefault(matched_pat, []).append(src_path)
            else:
                kept_sources += 1
                total_kept_missed += missed
                total_kept_covered += covered

    total_kept = total_kept_missed + total_kept_covered
    total_drop = total_drop_missed + total_drop_covered
    pct_kept = (total_kept_covered / total_kept * 100) if total_kept else 0.0
    pct_drop = (total_drop_covered / total_drop * 100) if total_drop else 0.0

    print()
    print(f"=== SonarQube-style LINE coverage (after sonar.coverage.exclusions) ===")
    print(f"Sourcefiles kept:    {kept_sources}")
    print(f"Sourcefiles dropped: {dropped_sources}")
    print()
    print(f"Lines covered (kept):  {total_kept_covered:>7,}")
    print(f"Lines missed (kept):   {total_kept_missed:>7,}")
    print(f"Lines TOTAL (kept):    {total_kept:>7,}")
    print(f"  → SonarQube-style coverage: {pct_kept:.2f}%")
    print()
    print(f"Lines hidden by Sonar exclusions (would have been counted by raw Jacoco):")
    print(f"  covered:   {total_drop_covered:>7,}")
    print(f"  missed:    {total_drop_missed:>7,}")
    print(f"  total:     {total_drop:>7,}")
    print(f"  → drop-list coverage: {pct_drop:.2f}%")
    print()
    print("Top 15 exclusion patterns by lines hidden:")
    pat_stats = []
    for pat, files in drop_examples_per_pat.items():
        # recompute total lines per pattern by reparsing — we already have the count via examples
        # quick: count-only
        pat_stats.append((pat, len(files)))
    pat_stats.sort(key=lambda x: -x[1])
    for pat, n in pat_stats[:15]:
        print(f"  {n:>4} files  ←  {pat}")

    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <coverage.xml>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
