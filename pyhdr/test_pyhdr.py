#!/usr/bin/env python3
"""Tests for pyhdr_census.py: the pure-Python rule py_load_problem() and, when GNU msgfmt is
installed, its agreement with CPython's gettext.GNUTranslations on the same synthetic files.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import os
import shutil
import tempfile
import unittest

import pyhdr_census as c

ENTRY = 'msgid "Open"\nmsgstr "Abrir"\n'
GOOD_CT = "Content-Type: text/plain; charset=UTF-8"
GOOD_PF = "Plural-Forms: nplurals=2; plural=(n != 1);"
E_ACUTE = chr(0xE9)
I_ACUTE = chr(0xED)


def po(header_lines, body=ENTRY, fuzzy_header=False, encoding="utf-8"):
    out = []
    if fuzzy_header:
        out.append("#, fuzzy")
    out.append('msgid ""')
    out.append('msgstr ""')
    for h in header_lines:
        out.append('"%s\\n"' % h)
    out.append("")
    out.append(body)
    return ("\n".join(out) + "\n").encode(encoding)


CASES = {
    "valid": po([GOOD_CT, GOOD_PF]),
    "valid-one-form": po([GOOD_CT, "Plural-Forms: nplurals=1; plural=0;"]),
    "no-header": ENTRY.encode("utf-8"),
    "empty-header": b'msgid ""\nmsgstr ""\n\n' + ENTRY.encode("utf-8"),
    "karbi-style": po([GOOD_CT, "Plural-Forms: n=2 ; ( n != 1 )"]),
    "template-expression": po([GOOD_CT, "Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;"]),
    "charset-placeholder": po(["Content-Type: text/plain; charset=CHARSET", GOOD_PF]),
    "no-charset": po(["Content-Type: text/plain", GOOD_PF]),
    "latin1-header": po(["Last-Translator: Jos" + E_ACUTE + " <j@example.org>",
                         "Content-Type: text/plain; charset=ISO-8859-1", GOOD_PF],
                        encoding="latin-1"),
    "fuzzy-header-template": po([GOOD_CT, "Plural-Forms: nplurals=INTEGER; plural=EXPRESSION;"],
                                fuzzy_header=True),
    "ascii-text-fuzzy": po(["Content-Type: text/plain; charset=ASCII", GOOD_PF],
                           body='#, fuzzy\nmsgid "Open"\nmsgstr "Abr' + I_ACUTE + '"\n'),
    "ascii-text": po(["Content-Type: text/plain; charset=ASCII", GOOD_PF],
                     body='msgid "Open"\nmsgstr "Abr' + I_ACUTE + '"\n'),
}

EXPECTED = {
    "valid": None,
    "valid-one-form": None,
    "no-header": None,
    "empty-header": None,
    "karbi-style": "plural-forms-syntax",
    "template-expression": "plural-forms-expression",
    "charset-placeholder": "unknown-charset",
    "no-charset": "content-type-no-charset",
    "latin1-header": "header-not-utf8",
    "fuzzy-header-template": "plural-forms-expression",
    "ascii-text-fuzzy": None,
    "ascii-text": "text-not-in-charset",
}


class ParseTest(unittest.TestCase):
    def test_entries(self):
        text = ('msgid ""\nmsgstr ""\n"A: b\\n"\n\n'
                '#, fuzzy, c-format\nmsgctxt "menu"\nmsgid "Open %s"\nmsgstr ""\n"Abrir %s"\n\n'
                'msgid "one"\nmsgid_plural "many"\nmsgstr[0] "uno"\nmsgstr[1] "muchos"\n\n'
                '#~ msgid "old"\n#~ msgstr "viejo"\n')
        es = c.parse_po(text)
        self.assertEqual(len(es), 4)
        self.assertEqual(es[0]["id"], "")
        self.assertEqual(es[0]["strs"][0], "A: b\n")
        self.assertEqual((es[1]["ctxt"], es[1]["id"], es[1]["strs"][0], es[1]["fuzzy"]),
                         ("menu", "Open %s", "Abrir %s", True))
        self.assertEqual((es[2]["id_plural"], es[2]["strs"]), ("many", {0: "uno", 1: "muchos"}))
        self.assertFalse(es[2]["fuzzy"])
        self.assertTrue(es[3]["obsolete"])


class RuleTest(unittest.TestCase):
    def test_cases(self):
        for name, data in sorted(CASES.items()):
            got = c.py_load_problem(data)
            self.assertEqual(got[0] if got else None, EXPECTED[name], name)

    def test_detail_quotes_the_header(self):
        code, detail = c.py_load_problem(CASES["karbi-style"])
        self.assertEqual(code, "plural-forms-syntax")
        self.assertIn("n=2 ; ( n != 1 )", detail)


@unittest.skipUnless(shutil.which("msgfmt"), "needs GNU msgfmt")
class GroundTruthTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def truth(self, name):
        path = os.path.join(self.tmp, name + ".po")
        with open(path, "wb") as fh:
            fh.write(CASES[name])
        return c.ground_truth(path, os.path.join(self.tmp, name + ".mo"))

    def test_valid_file_compiles_and_loads(self):
        gt = self.truth("valid")
        self.assertEqual((gt["msgfmt"], gt["load"]), ("ok", "ok"), gt)

    def test_rule_agrees_with_cpython(self):
        compiled = 0
        for name in sorted(CASES):
            gt = self.truth(name)
            if gt["msgfmt"] != "ok":
                continue
            compiled += 1
            rule = c.py_load_problem(CASES[name])
            self.assertEqual(rule is None, gt["load"] == "ok", (name, rule, gt))
        self.assertGreaterEqual(compiled, 6)


if __name__ == "__main__":
    unittest.main()
