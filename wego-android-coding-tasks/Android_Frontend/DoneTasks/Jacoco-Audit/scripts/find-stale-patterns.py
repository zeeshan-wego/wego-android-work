#!/usr/bin/env python3
"""
Find dead exclusion patterns: entries in fileFilter / sourceFileFilter that
match NO source file in the repo. These are likely stale (referencing renamed
or deleted classes) and can be removed.

For each pattern, we test it against:
  - fileFilter: every source file's class-name candidates
  - sourceFileFilter: every source file's source key (.kt/.java)

Output (TSV): <list_name>\t<pattern>\t<status>\t<sample_match_or_empty>

Where <status> is HIT (matches at least 1 file) or DEAD (matches nothing).
"""
import os
import re
import sys

SCRIPT_PATH = "/Users/zeeshanarif/Documents/GitHub/newandroid/wego-android-n/tools/script-jacoco.gradle"
SOURCE_INDEX = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "data", "source-index.tsv",
)


def parse_groovy_list(script_text: str, list_name: str) -> list[str]:
    pattern = re.compile(
        r"def\s+" + re.escape(list_name) + r"\s*=\s*\[(.*?)\]", re.DOTALL,
    )
    m = pattern.search(script_text)
    if not m:
        raise ValueError(f"could not find list {list_name!r}")
    body = m.group(1)
    body = re.sub(r"//[^\n]*", "", body)  # strip line comments to avoid stray apostrophes
    items = re.findall(r"'([^']*)'|\"([^\"]*)\"", body)
    return [a or b for a, b in items]


def compile_ant_glob(pat: str) -> "re.Pattern[str]":
    out = []
    i = 0
    n = len(pat)
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


def class_keys_for_source(key: str) -> list[str]:
    base, _, fn = key.rpartition("/")
    if "." not in fn:
        return [key]
    name, ext = fn.rsplit(".", 1)
    prefix = base + "/" if base else ""
    if ext == "kt":
        return [
            f"{prefix}{name}.class",
            f"{prefix}{name}Kt.class",
            f"{prefix}{name}$Inner.class",
            f"{prefix}{name}Kt$Inner.class",
        ]
    elif ext == "java":
        return [
            f"{prefix}{name}.class",
            f"{prefix}{name}$Inner.class",
        ]
    return [key]


def main() -> int:
    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        script_text = f.read()

    file_filter = parse_groovy_list(script_text, "fileFilter")
    source_filter = parse_groovy_list(script_text, "sourceFileFilter")

    # Build lookup of all source keys + their class candidates
    src_keys = []
    class_cands = []
    with open(SOURCE_INDEX, "r", encoding="utf-8") as f:
        for line in f:
            key = line.split("\t", 1)[0].strip()
            if not key:
                continue
            src_keys.append(key)
            class_cands.extend(class_keys_for_source(key))

    print(
        f"# Source keys: {len(src_keys)}  Class candidates: {len(class_cands)}",
        file=sys.stderr,
    )

    dead_ff = []
    for pat in file_filter:
        rx = compile_ant_glob(pat)
        hit = next((c for c in class_cands if rx.match(c)), None)
        status = "HIT" if hit else "DEAD"
        print(f"fileFilter\t{pat}\t{status}\t{hit or ''}")
        if status == "DEAD":
            dead_ff.append(pat)

    dead_sf = []
    for pat in source_filter:
        rx = compile_ant_glob(pat)
        hit = next((k for k in src_keys if rx.match(k)), None)
        status = "HIT" if hit else "DEAD"
        print(f"sourceFileFilter\t{pat}\t{status}\t{hit or ''}")
        if status == "DEAD":
            dead_sf.append(pat)

    print(
        f"# Dead in fileFilter: {len(dead_ff)} of {len(file_filter)}",
        file=sys.stderr,
    )
    print(
        f"# Dead in sourceFileFilter: {len(dead_sf)} of {len(source_filter)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
