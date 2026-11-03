#!/usr/bin/env python3
# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Runs the pre-registered zh_vocab.py 0.1.0 unchanged, with a CSV writer that can't crash on
half an emoji.

zh_vocab.py 0.1.0 decodes Android escapes one UTF-16 half at a time, so an emoji written as two
escapes becomes two lone surrogates in the decoded text. Its first full run (zh-vocab-v1, 2 Nov
2026) stopped with UnicodeEncodeError when it tried to write such a string into flagged.csv,
after about 4,500 of 4,693 repositories, so it never wrote summary.json or sample.csv.

Lone surrogates are not Han characters and never match a phrase-table key, so the scan, the
counts, the verdicts and the sample drawn are not affected by them. This wrapper changes only the
CSV writer zh_vocab uses: before a row is written, each text value has its surrogate pairs joined
into the character they encode, and any half left over replaced with U+FFFD. Nothing else in
zh_vocab.py is touched, and its SHA-256 is recorded in summary.json ("runner").

The deviation is described in DEVIATIONS.md, which must be public before this runs.

Made with AI agents by MV2 of Munim, Inc. Standard library only.
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import time
import types
import urllib.request

import zh_vocab

EXPECTED_VERSION = "0.1.0"
WRAPPER_VERSION = "0.1.0"
DEVIATIONS_URL = zh_vocab.BASE + "zh-vocab/DEVIATIONS.md"
DEVIATIONS_MARK = "zh-vocab DEVIATION 1"


def clean_text(value):
    """Join surrogate pairs into one character and replace lone halves with U+FFFD."""
    if not isinstance(value, str):
        return value
    return value.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


class SafeDictWriter(csv.DictWriter):
    """csv.DictWriter that cleans every text value first (see clean_text)."""

    def writerow(self, rowdict):
        return super().writerow({k: clean_text(v) for k, v in rowdict.items()})

    def writerows(self, rowdicts):
        for r in rowdicts:
            self.writerow(r)


def safe_csv_module():
    m = types.ModuleType("csv_safe")
    for name in dir(csv):
        if not name.startswith("__"):
            setattr(m, name, getattr(csv, name))
    m.DictWriter = SafeDictWriter
    return m


def install():
    """Point zh_vocab's `csv` at the safe module. Returns zh_vocab."""
    zh_vocab.csv = safe_csv_module()
    return zh_vocab


def wait_for_deviations(minutes):
    end = time.time() + minutes * 60
    while True:
        try:
            with urllib.request.urlopen(DEVIATIONS_URL, timeout=60) as r:
                text = r.read().decode("utf-8")
            if DEVIATIONS_MARK in text:
                return hashlib.sha256(text.encode("utf-8")).hexdigest()
        except OSError:
            pass
        if time.time() > end:
            return None
        time.sleep(60)


def file_sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--deviations-wait-minutes", type=float, default=60)
    ap.add_argument("--skip-deviations-check", action="store_true")
    known, rest = ap.parse_known_args(argv)
    if zh_vocab.VERSION != EXPECTED_VERSION:
        print("zh_vocab.py is %s, not the pre-registered %s; stopping"
              % (zh_vocab.VERSION, EXPECTED_VERSION), file=sys.stderr)
        return 7
    dev_sha = None
    if not known.skip_deviations_check:
        dev_sha = wait_for_deviations(known.deviations_wait_minutes)
        if not dev_sha:
            print("DEVIATIONS.md not public; stopping before reading any repository",
                  file=sys.stderr)
            return 4
    runner = {"wrapper": "run_zh_vocab.py", "wrapper_version": WRAPPER_VERSION,
              "zh_vocab_version": zh_vocab.VERSION,
              "zh_vocab_sha256": file_sha(zh_vocab.__file__),
              "wrapper_sha256": file_sha(os.path.abspath(__file__)),
              "deviations_sha256": dev_sha,
              "change": "CSV text values: surrogate pairs joined, lone halves replaced with U+FFFD"}
    os.makedirs(known.out_dir, exist_ok=True)
    with open(os.path.join(known.out_dir, "runner.json"), "w", encoding="utf-8") as f:
        json.dump(runner, f, indent=1, sort_keys=True)
    print("runner", json.dumps(runner), flush=True)
    install()
    rc = zh_vocab.main(["--out-dir", known.out_dir] + rest)
    path = os.path.join(known.out_dir, "summary.json")
    if rc == 0 and os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            summary = json.load(f)
        summary["runner"] = runner
        with open(path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=1, sort_keys=True)
    return rc


if __name__ == "__main__":
    sys.exit(main())
