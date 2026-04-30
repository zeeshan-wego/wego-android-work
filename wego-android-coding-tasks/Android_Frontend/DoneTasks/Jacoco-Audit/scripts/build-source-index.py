#!/usr/bin/env python3
"""
Build a canonical source index keyed by Jacoco's "<package>/<sourcefile>" format.

For every .kt / .java file under each module's src/main/java directory:
  1. Read the file and extract its `package X.Y.Z` declaration.
  2. Build the key: X/Y/Z/Filename.ext  (matches what Jacoco reports).
  3. Emit one line per file as: <key>\t<absolute_path>

Why we read the package declaration instead of using the directory: in this
repo many files live under directories that don't match their declared package
(legacy organization). Jacoco reports use the declaration, so we must too.

Output goes to stdout (sorted by key).
Stats go to stderr.
"""
import os
import re
import sys

REPO_ROOT_DEFAULT = "/Users/zeeshanarif/Documents/GitHub/newandroid/wego-android-n"

PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;?\s*$", re.MULTILINE)


def find_package(path: str) -> str:
    """Read the first 8KB of the file and return the declared package, or '' if none."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = f.read(8192)
    except OSError:
        return ""
    m = PACKAGE_RE.search(head)
    return m.group(1) if m else ""


def main() -> int:
    repo_root = os.environ.get("REPO_ROOT", REPO_ROOT_DEFAULT)
    if not os.path.isdir(repo_root):
        print(f"REPO_ROOT not found: {repo_root}", file=sys.stderr)
        return 2

    # Source sets compiled into the playstoreDebug variant:
    #  - src/main/java          (always)
    #  - src/common/java        (only libbase and wegoapk wire this into the
    #                            'playstore' flavor via build.gradle)
    extra_common = {"libbase", "wegoapk"}

    rows = []
    no_package = []
    for module in sorted(os.listdir(repo_root)):
        candidate_dirs = [os.path.join(repo_root, module, "src", "main", "java")]
        if module in extra_common:
            candidate_dirs.append(os.path.join(repo_root, module, "src", "common", "java"))

        for src_dir in candidate_dirs:
            if not os.path.isdir(src_dir):
                continue
            for dirpath, _dirnames, filenames in os.walk(src_dir):
                if "/build/" in dirpath:
                    continue
                for fn in filenames:
                    if not (fn.endswith(".kt") or fn.endswith(".java")):
                        continue
                    full = os.path.join(dirpath, fn)
                    pkg = find_package(full)
                    if pkg:
                        key = pkg.replace(".", "/") + "/" + fn
                    else:
                        key = fn  # default package
                        no_package.append(full)
                    rows.append((key, full))

    rows.sort()
    for key, full in rows:
        rel = os.path.relpath(full, repo_root)
        print(f"{key}\t{rel}")

    print(f"[build-source-index] total files: {len(rows)}", file=sys.stderr)
    print(f"[build-source-index] files with no package decl (default package): {len(no_package)}", file=sys.stderr)
    if no_package[:5]:
        print(f"  sample: {no_package[:5]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
