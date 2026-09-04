#!/usr/bin/env python3
"""Remove only temp-v2 PDF render caches under tmp/pdfs."""

from __future__ import annotations

import argparse
import shutil

from stats import ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    cache = (ROOT / "tmp" / "pdfs").resolve()
    expected = (ROOT.resolve() / "tmp" / "pdfs")
    if cache != expected:
        raise ValueError(f"refusing unexpected cache path: {cache}")
    files = sum(path.is_file() for path in cache.rglob("*")) if cache.exists() else 0
    print(f"cache={cache.relative_to(ROOT)} files={files} mode={'apply' if args.apply else 'dry-run'}")
    if args.apply and cache.exists():
        shutil.rmtree(cache)
    finder_metadata = ROOT / "tmp" / ".DS_Store"
    if args.apply and finder_metadata.is_file():
        finder_metadata.unlink()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
