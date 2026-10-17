#!/usr/bin/env python3
"""Tests for census_callsites.py. Run after fetch_code.py (needs census.py,
census_fixes.py, census_plurals.py and l10n_guard.py next to this file).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import csv
import os
import shutil
import tempfile
import unittest

import census
import census_callsites as cc

# No call in this file formats an id it doesn't name, so nothing is "stored".
JAVA = """package a;

class A {
    private final String couldNotScan;

    A(Activity activity) {
        couldNotScan = activity.getString(R.string.f_java);
    }

    void scanned(int failed) {
        toast(String.format(couldNotScan, failed));
        String text = String.format(getResources().getString(R.string.w_java), name);
        String pulse = String.format(Locale.getDefault(),
                context.getResources().getQuantityString(R.plurals.w_plural, n), 1.5f, n);
        Toast.makeText(this, R.string.n_toast, Toast.LENGTH_SHORT).show();
        String label = getString(R.string.n_plain);
        int id = one ? R.string.s_a : R.string.s_b;
        textView.setText(id);
        String name = prefs.getString(KEY_NAME, "");
        String other = prefs.getString(nameKey, null);
        VpnStatus.logInfo(R.string.h_java, proxyName);
        items.add(new Item(R.string.n_item, R.drawable.icon));
        String done = getString(R.string.f_direct, failed);
    }
}
"""

# getString(messageStringId, name) formats an id held in a variable.
KOTLIN = """package b

class B {
    fun show(folder: Boolean, name: String) {
        val messageStringId = if (folder) R.string.s_kt else R.string.s_kt2
        val text = requireContext().getString(messageStringId, name)
        showDialog(activity, title = R.string.n_title, message = R.string.h_named, messageArguments = arrayOf(name))
        Toast.makeText(context, R.string.n_toast_kt, Toast.LENGTH_SHORT).show()
        val ids = listOf(R.string.s_list, R.string.s_list2)
        textView.setText(R.string.n_set)
    }
}
"""

A_WANT = {"f_java": "fetched", "w_java": "wrapped", "h_java": "helper"}
A_PLURAL_WANT = {"w_plural": "wrapped"}
A_REFERENCED = ["n_toast", "n_plain", "s_a", "s_b", "n_item"]
B_WANT = {"s_kt": "stored", "s_kt2": "stored", "h_named": "helper", "n_title": "helper",
          "s_list": "stored", "s_list2": "stored"}
B_REFERENCED = ["n_toast_kt", "n_set"]


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


class CallsitesTest(unittest.TestCase):
    def setUp(self):
        self.a = tempfile.mkdtemp(prefix="callsites-a-")
        self.b = tempfile.mkdtemp(prefix="callsites-b-")
        write(os.path.join(self.a, "app", "src", "main", "java", "a", "A.java"), JAVA)
        write(os.path.join(self.b, "app", "src", "main", "java", "b", "B.kt"), KOTLIN)

    def tearDown(self):
        shutil.rmtree(self.a, ignore_errors=True)
        shutil.rmtree(self.b, ignore_errors=True)

    def test_split_args(self):
        text = 'f(a, g(b, c), "x,(y")'
        spans, close = cc._split_args(text, 1)
        self.assertEqual([text[s:e].strip() for s, e in spans], ["a", "g(b, c)", '"x,(y"'])
        self.assertEqual(close, len(text) - 1)
        self.assertEqual(cc._split_args("f()", 1), ([], 2))
        self.assertIsNone(cc._split_args("f(a, b", 1))

    def test_has_dynamic(self):
        self.assertFalse(cc.has_dynamic(JAVA))
        self.assertTrue(cc.has_dynamic(KOTLIN))
        yes = ["getQuantityString(titleRes, fileCount, fileCount, size)",
               "String.format(getText(id).toString(), x)",
               "res.getQuantityString(getAgoStringResID(), value0, value0)",
               "getString(chartConfig.title, value)",
               "String.format(Locale.US, getString(resId), x)"]
        no = ['prefs.getString(KEY_TITLE, "")', "prefs.getString(titleKey, null)",
              "cursor.getString(cursor.getColumnIndex(COL))", "stringResource(id = R.string.a, x)",
              "getString(R.string.a, x)", "getString(resId)", 'json.getString("title")',
              "getQuantityString(pluralId, n)"]
        for text in yes:
            self.assertTrue(cc.has_dynamic(text), text)
        for text in no:
            self.assertFalse(cc.has_dynamic(text), text)

    def test_candidates(self):
        names = {("string", n) for n in list(A_WANT) + A_REFERENCED}
        names.add(("plurals", "w_plural"))
        got = cc.candidates(self.a, names)
        want = dict((("string", n), w) for n, w in A_WANT.items())
        want[("plurals", "w_plural")] = "wrapped"
        self.assertEqual(got, want)
        names = {("string", n) for n in list(B_WANT) + B_REFERENCED}
        got = cc.candidates(self.b, names)
        self.assertEqual(got, dict((("string", n), w) for n, w in B_WANT.items()))

    def test_code_uses_through_census(self):
        cc.apply()
        cc.apply()  # twice is the same as once
        self.assertIs(census.code_uses, cc.code_uses)
        self.assertIn("candidate", census.USES)
        names = {("string", n) for n in list(A_WANT) + A_REFERENCED + ["f_direct"]}
        names.add(("plurals", "w_plural"))
        uses = census.code_uses(self.a, names)
        self.assertEqual(uses[("string", "f_direct")], "formatted")
        for n in A_WANT:
            self.assertEqual(uses[("string", n)], "candidate", n)
        self.assertEqual(uses[("plurals", "w_plural")], "candidate")
        for n in A_REFERENCED:
            self.assertEqual(uses[("string", n)], "referenced", n)
        self.assertEqual(cc._local.found[("string", "w_java")], "wrapped")

    def test_audit_file(self):
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, cc.AUDIT), encoding="utf-8", newline="") as f:
            audit = list(csv.DictReader(f))
        self.assertEqual(len(audit), 40)
        self.assertEqual(sum(a["verdict"] in cc.THROWS for a in audit), 34)
        self.assertEqual(sum(a["verdict"] in cc.NOT_FORMATTED for a in audit), 2)

    def test_audit_rows_and_predictions(self):
        audit = [{"repo": "o/r", "locale": "nl", "key": "a", "verdict": "crash"},
                 {"repo": "o/r", "locale": "nl", "key": "b", "verdict": "throws, caught"},
                 {"repo": "o/r", "locale": "fa", "key": "c", "verdict": "safe (not formatted)"},
                 {"repo": "o/gone", "locale": "fa", "key": "d", "verdict": "crash"}]
        findings = [
            {"repo": "https://github.com/O/R", "locale": "nl", "key": "a", "verdict": "crash",
             "use": "candidate", "callsite": "helper"},
            {"repo": "https://github.com/o/r", "locale": "nl", "key": "b", "verdict": "crash",
             "use": "formatted", "callsite": ""},
            {"repo": "https://github.com/o/r", "locale": "fa", "key": "c", "verdict": "crash",
             "use": "referenced", "callsite": ""}]
        rows = cc.audit_rows(findings, audit)
        self.assertEqual([r["found"] for r in rows], [True, True, True, False])
        self.assertEqual(rows[0]["callsite"], "helper")
        got = {p["id"]: p["held"] for p in cc.predictions(rows, {"referenced_names": 10,
                                                                 "candidate_names": 5})}
        self.assertEqual(got, {"C1": True, "C2": True, "C3": True})
        findings[1]["use"] = "referenced"
        findings[2]["use"] = "candidate"
        rows = cc.audit_rows(findings, audit)
        got = {p["id"]: p["held"] for p in cc.predictions(rows, {"referenced_names": 10,
                                                                 "candidate_names": 6})}
        self.assertEqual(got, {"C1": False, "C2": False, "C3": False})
        got = {p["id"]: p["held"] for p in cc.predictions([], {})}
        self.assertEqual(got, {"C1": False, "C2": None, "C3": None})


if __name__ == "__main__":
    unittest.main()
