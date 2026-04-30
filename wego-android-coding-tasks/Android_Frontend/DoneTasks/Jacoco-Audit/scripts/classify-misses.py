#!/usr/bin/env python3
"""
Classify each "missing from coverage report" source file against the three
exclusion layers in tools/script-jacoco.gradle:

  1. fileFilter         — class-file globs (applied to all JacocoReport tasks)
  2. sourceFileFilter   — source-file globs (applied to aggregateCoverageReportByModule)
  3. removeExcludedSourceFilesFromXml — post-processing regex on 5 basenames

For each missing source file we emit:

    <key>\t<reason>\t<matched_pattern>\t<source_path>

Where <reason> is one of:
    EXCLUDED_BY_FILEFILTER
    EXCLUDED_BY_SOURCEFILTER
    EXCLUDED_BY_XML_POSTPROCESS
    UNEXPLAINED   <- this is the suspicious bucket: file is missing but not
                    matched by any exclusion. Most likely no test was written,
                    OR the build didn't compile this file, OR coverage XML
                    drift since the run.

Note: the heuristic for matching `fileFilter` (which targets `.class` files):
we translate the source file's package+filename into the most likely class
file names and match those against fileFilter's globs:
  - Foo.kt  →  com/.../Foo.class, com/.../FooKt.class, com/.../Foo$*.class, com/.../FooKt$*.class
  - Foo.java →  com/.../Foo.class, com/.../Foo$*.class
"""
import fnmatch
import os
import re
import sys


# ============================================================================
# Pull the exclusion lists from tools/script-jacoco.gradle directly so we
# don't drift. We parse the two Groovy list literals.
# ============================================================================
SCRIPT_PATH = "/Users/zeeshanarif/Documents/GitHub/newandroid/wego-android-n/tools/script-jacoco.gradle"


def parse_groovy_list(script_text: str, list_name: str) -> list[str]:
    """
    Parse a Groovy list literal of the form:
        def {list_name} = [ '...', "...", ... ]
    Strip Groovy comments, return the entry strings in order.
    """
    pattern = re.compile(
        r"def\s+" + re.escape(list_name) + r"\s*=\s*\[(.*?)\]",
        re.DOTALL,
    )
    m = pattern.search(script_text)
    if not m:
        raise ValueError(f"could not find list {list_name!r}")
    body = m.group(1)
    # Strip line comments BEFORE pattern extraction so apostrophes inside
    # comments (e.g. "doesn't") don't desync the quote-pair scanner.
    # We do NOT strip block comments — patterns like '**/foo/**/*.class'
    # contain '/**/' which a naive block-comment regex would mistake for a
    # comment span. Quoted patterns themselves never contain '//'.
    body = re.sub(r"//[^\n]*", "", body)
    items = re.findall(r"'([^']*)'|\"([^\"]*)\"", body)
    return [a or b for a, b in items]


XML_POSTPROCESS_PATTERNS = [
    "TravellerFormScreen.kt",
    "BottomSheetScanDocument.kt",
    "BottomSheetInfo.kt",
    "DynamicViewHandler.kt",
    "DFWegoTextField.kt",
]


def class_keys_for_source(key: str) -> list[str]:
    """
    Translate a source file key (com/foo/bar/Baz.kt) into the candidate class-
    file globs we'd expect to see in JaCoCo's class-file space.
    """
    base, _, fn = key.rpartition("/")
    if "." not in fn:
        return [key]
    name, ext = fn.rsplit(".", 1)
    prefix = base + "/" if base else ""
    if ext == "kt":
        return [
            f"{prefix}{name}.class",
            f"{prefix}{name}Kt.class",
            f"{prefix}{name}$x.class",      # synthetic inner classes (probe)
            f"{prefix}{name}Kt$x.class",
        ]
    elif ext == "java":
        return [
            f"{prefix}{name}.class",
            f"{prefix}{name}$x.class",
        ]
    return [key]


_ant_glob_cache: dict[str, "re.Pattern[str]"] = {}


def _compile_ant_glob(pat: str) -> "re.Pattern[str]":
    """
    Convert an Ant-style glob (used by JaCoCo) into a regex.
    Semantics:
      **      = any number of path segments (incl. zero)
      **/     = zero-or-more directory prefix
      *       = any chars except '/'
      ?       = single char except '/'
      $       = literal '$' (special in Java/Kotlin inner-class names)
      .       = literal '.'
    Anchored to the full string.
    """
    cached = _ant_glob_cache.get(pat)
    if cached is not None:
        return cached
    out = []
    i = 0
    n = len(pat)
    while i < n:
        c = pat[i]
        if c == "*":
            if i + 1 < n and pat[i + 1] == "*":
                # '**' or '**/'
                if i + 2 < n and pat[i + 2] == "/":
                    out.append(r"(?:.*?/)?")  # zero or more dirs
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
    rx = re.compile("^" + "".join(out) + "$")
    _ant_glob_cache[pat] = rx
    return rx


def matches_any(candidates: list[str], patterns: list[str]) -> tuple[bool, str]:
    """Match candidates against Ant-glob patterns. Returns (matched, pattern)."""
    for pat in patterns:
        rx = _compile_ant_glob(pat)
        for cand in candidates:
            if rx.match(cand):
                return True, pat
    return False, ""


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <missing-from-report.txt>", file=sys.stderr)
        return 2

    missing_path = sys.argv[1]
    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        script_text = f.read()

    file_filter = parse_groovy_list(script_text, "fileFilter")
    source_filter = parse_groovy_list(script_text, "sourceFileFilter")

    print(
        f"[classify] fileFilter={len(file_filter)}  sourceFileFilter={len(source_filter)}"
        f"  xmlPostProcess={len(XML_POSTPROCESS_PATTERNS)}",
        file=sys.stderr,
    )

    # Build a lookup: key -> source path (for output convenience)
    src_index_path = os.path.join(
        os.path.dirname(os.path.abspath(missing_path)), "source-index.tsv"
    )
    key_to_path = {}
    with open(src_index_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) == 2:
                key_to_path[parts[0]] = parts[1]

    counts = {
        "EXCLUDED_BY_FILEFILTER": 0,
        "EXCLUDED_BY_SOURCEFILTER": 0,
        "EXCLUDED_BY_XML_POSTPROCESS": 0,
        "UNEXPLAINED": 0,
    }

    with open(missing_path, "r", encoding="utf-8") as fin:
        for line in fin:
            key = line.rstrip("\n")
            if not key:
                continue
            src_path = key_to_path.get(key, "")
            basename = key.rsplit("/", 1)[-1]

            # 1. XML post-processing layer (cheapest, exact basename)
            if basename in XML_POSTPROCESS_PATTERNS:
                counts["EXCLUDED_BY_XML_POSTPROCESS"] += 1
                print(f"{key}\tEXCLUDED_BY_XML_POSTPROCESS\t{basename}\t{src_path}")
                continue

            # 2. fileFilter (class-file globs)
            class_cands = class_keys_for_source(key)
            ok, pat = matches_any(class_cands, file_filter)
            if ok:
                counts["EXCLUDED_BY_FILEFILTER"] += 1
                print(f"{key}\tEXCLUDED_BY_FILEFILTER\t{pat}\t{src_path}")
                continue

            # 3. sourceFileFilter (source-file globs)
            ok, pat = matches_any([key], source_filter)
            if ok:
                counts["EXCLUDED_BY_SOURCEFILTER"] += 1
                print(f"{key}\tEXCLUDED_BY_SOURCEFILTER\t{pat}\t{src_path}")
                continue

            counts["UNEXPLAINED"] += 1
            print(f"{key}\tUNEXPLAINED\t-\t{src_path}")

    for cat, n in counts.items():
        print(f"[classify] {cat}: {n}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
