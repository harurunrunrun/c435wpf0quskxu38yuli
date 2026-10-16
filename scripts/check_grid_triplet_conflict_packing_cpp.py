#!/usr/bin/env python3
"""Compile the published triplet packing implementation and test an endpoint oracle."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--article', type=Path)
    parser.add_argument('--tests', type=Path)
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent
    article = args.article or directory.parent / 'src/content/docs/techniques/grid-triplet-conflict-packing.mdx'
    tests = args.tests or directory / 'grid_triplet_conflict_packing_tests.cpp'
    compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
    if not compiler:
        raise RuntimeError('A C++20 compiler is required')
    fences = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', article.read_text(), re.M | re.S)
    if len(fences) != 1:
        raise ValueError('Expected one complete published C++ implementation')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-triplet-packing-run-') as work:
        source = Path(work) / 'test.cpp'
        executable = Path(work) / 'test'
        source.write_text(fences[0] + '\n' + tests.read_text())
        flags = ['-std=c++20', '-Wall', '-Wextra', '-Werror', '-pedantic']
        flags += ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer'] if args.sanitize else ['-O2']
        subprocess.run([compiler, *flags, str(source), '-o', str(executable)], check=True, timeout=90)
        environment = os.environ.copy()
        if args.sanitize:
            # LeakSanitizer is unsupported in the workspace's traced process.
            environment['ASAN_OPTIONS'] = 'detect_leaks=0'
        subprocess.run([str(executable), work], check=True, timeout=180, env=environment)


if __name__ == '__main__':
    main()
