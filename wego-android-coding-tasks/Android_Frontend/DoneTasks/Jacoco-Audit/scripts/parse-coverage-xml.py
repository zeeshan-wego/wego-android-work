#!/usr/bin/env python3
"""
Parse a Jacoco coverage.xml and emit one line per (package + sourcefile) entry.

Output format (one per line, sorted, deduped):
    com/wego/android/foo/bar/MyFile.kt

This is the path-suffix relative to a module's src/main/java/ directory.
Use diff-coverage.py to match it against the source-file inventory.

Also writes summary stats to stderr.
"""
import sys
import xml.etree.ElementTree as ET


def main(xml_path: str) -> int:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    packages = root.findall('.//package')
    print(f"[parse-coverage-xml] packages={len(packages)}", file=sys.stderr)

    entries = set()
    classes = 0
    for pkg in packages:
        pkg_name = pkg.get('name', '')  # e.g. 'com/wego/android/foo'
        for sf in pkg.findall('sourcefile'):
            sf_name = sf.get('name', '')  # e.g. 'MyFile.kt'
            if not sf_name:
                continue
            full = f"{pkg_name}/{sf_name}" if pkg_name else sf_name
            entries.add(full)
        classes += len(pkg.findall('class'))

    print(
        f"[parse-coverage-xml] sourcefile entries (deduped)={len(entries)} classes={classes}",
        file=sys.stderr,
    )

    for entry in sorted(entries):
        print(entry)
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <coverage.xml>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
