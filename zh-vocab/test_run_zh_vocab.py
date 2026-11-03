# Copyright 2026 MV2, Munim, Inc.
# SPDX-License-Identifier: Apache-2.0
"""Tests for run_zh_vocab.py (no network). Made with AI agents."""
import csv
import os
import shutil
import tempfile
import unittest

import run_zh_vocab as w
import zh_vocab as z

HIGH, LOW, REPL = chr(0xD83D), chr(0xDE00), chr(0xFFFD)
EMOJI = chr(0x1F600)


def has_surrogate(text):
    return any(0xD800 <= ord(c) <= 0xDFFF for c in text)


def write(path, body):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n' + body + "</resources>\n")


class TestClean(unittest.TestCase):
    def test_pair_joined(self):
        self.assertEqual(w.clean_text("a" + HIGH + LOW + "b"), "a" + EMOJI + "b")

    def test_lone_half_replaced(self):
        for s in ("a" + HIGH + "b", "a" + LOW + "b", "a" + HIGH, LOW + "b"):
            out = w.clean_text(s)
            self.assertFalse(has_surrogate(out))
            self.assertIn(REPL, out)
            out.encode("utf-8")

    def test_plain_unchanged(self):
        for s in ("", "軟件，用戶", "Default " + EMOJI, "預設"):
            self.assertEqual(w.clean_text(s), s)
        self.assertIs(w.clean_text(True), True)
        self.assertEqual(w.clean_text(3), 3)


class TestWrapper(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        res = os.path.join(self.root, "app", "res")
        esc = "\\" + "uD83D" + "\\" + "uDE00"
        write(os.path.join(res, "values", "strings.xml"),
              '<string name="a">Software</string>\n')
        write(os.path.join(res, "values-zh-rTW", "strings.xml"),
              '<string name="a">' + esc + '軟件</string>\n')

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def flagged_row(self):
        p = z.Phrases(z.parse_dict("軟件\t軟體\n", single=False))
        r = z.scan_strings(self.root, p, {}, set())
        self.assertEqual(r["flagged"]["tw"], 1)
        row = dict(r["rows"][0], repo="R", head="H")
        self.assertTrue(has_surrogate(row["text"]))   # the bug's input, reproduced
        return row

    def test_plain_writer_crashes(self):
        row = self.flagged_row()
        path = os.path.join(self.root, "plain.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            dw = csv.DictWriter(f, fieldnames=z.ROW_COLS)
            with self.assertRaises(UnicodeEncodeError):
                dw.writerow(row)

    def test_safe_writer_writes(self):
        row = self.flagged_row()
        path = os.path.join(self.root, "safe.csv")
        with open(path, "w", encoding="utf-8", newline="") as f:
            dw = w.SafeDictWriter(f, fieldnames=z.ROW_COLS)
            dw.writeheader()
            dw.writerow(row)
        with open(path, encoding="utf-8", newline="") as f:
            back = list(csv.DictReader(f))
        self.assertEqual(len(back), 1)
        self.assertEqual(back[0]["text"], EMOJI + "軟件")
        self.assertEqual(back[0]["terms"], "軟件")
        self.assertEqual(back[0]["key"], "string:a")

    def test_install(self):
        self.assertEqual(z.VERSION, w.EXPECTED_VERSION)
        w.install()
        self.assertIs(z.csv.DictWriter, w.SafeDictWriter)
        self.assertIs(z.csv.QUOTE_MINIMAL, csv.QUOTE_MINIMAL)


if __name__ == "__main__":
    unittest.main()
