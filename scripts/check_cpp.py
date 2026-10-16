#!/usr/bin/env python3
"""Compile each authored C++ fence independently; never write into the source tree."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


SITE = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^```(cpp|c\+\+)([^\n]*)\n(.*?)^```\s*$", re.M | re.S)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    parser.add_argument("--jobs", type=int, default=min(4, os.cpu_count() or 1))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    snippets = []
    articles = sorted(article for article in (SITE / "src/content/docs").rglob("*") if article.suffix in {".md", ".mdx"})
    for article in articles:
        content = article.read_text(encoding="utf8")
        for index, match in enumerate(FENCE.finditer(content), 1):
            line = content.count("\n", 0, match.start()) + 1
            label = f"{article.relative_to(SITE)}:{line} (snippet {index})"
            if "schematic" in match.group(2) or "pseudocode" in match.group(2):
                print(f"ERROR {label}: schematic examples must use a text fence, not cpp", file=sys.stderr)
                return 1
            snippets.append((label, match.group(3)))
    if not snippets:
        print("ERROR: no C++ snippets found", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix="flowchartcp-cpp-") as directory:
        def check(item):
            index, (label, code) = item
            source = Path(directory) / f"snippet-{index}.cpp"
            source.write_text(code, encoding="utf8")
            try:
                result = subprocess.run([args.compiler, "-std=c++20", "-Wall", "-Wextra", "-Werror", "-I", str(SITE / "vendor/ac-library"), "-fsyntax-only", str(source)], capture_output=True, text=True, timeout=60)
                return label, result.returncode, result.stderr
            except subprocess.TimeoutExpired:
                return label, 1, "Compilation exceeded 60 seconds."
        with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            results = list(pool.map(check, enumerate(snippets)))
        failures = [(label, output) for label, code, output in results if code]
        for label, output in failures:
            print(f"ERROR {label}\n{output}", file=sys.stderr)
        if failures:
            print(f"C++ check failed: {len(failures)} / {len(snippets)} snippets", file=sys.stderr)
            return 1
    print(f"Compiled {len(snippets)} independent C++20 snippets. Source files unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
