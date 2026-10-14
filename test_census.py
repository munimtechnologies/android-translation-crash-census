import contextlib
import csv
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import census as c  # noqa: E402

EN = '''<?xml version="1.0" encoding="utf-8"?>
<resources xmlns:xliff="urn:oasis:names:tc:xliff:document:1.2">
    <string name="done">%1$d%% done</string>
    <string name="raw" formatted="false">%s and %d</string>
    <string name="who">Shared by <xliff:g id="name">%1$s</xliff:g></string>
    <string name="saved">Saved</string>
    <string name="size">%1$s of %2$.1f MB</string>
    <plurals name="left"><item quantity="one">One left</item><item quantity="other">%d left</item></plurals>
    <plurals name="got"><item quantity="one">File from %1$s</item><item quantity="other">%2$d of %3$d files from %1$s</item></plurals>
    <string-array name="units"><item>%d km</item></string-array>
</resources>
'''

FR = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="done">%1$d % terminé</string>
    <string name="raw">%s et %</string>
    <string name="who">Partagé par %2$s \\uD83D\\uDE00</string>
    <string name="saved">Enregistré</string>
    <string name="size">%1$s sur %2$d Mo</string>
    <plurals name="left"><item quantity="one">Il en reste un</item><item quantity="many">%d restants</item><item quantity="other">%d %restants</item></plurals>
    <plurals name="got"><item quantity="one">Fichier %2$d sur %3$d de %1$s</item><item quantity="other">%2$d sur %3$d fichiers de %1$s</item></plurals>
    <string-array name="units"><item>%d % km</item></string-array>
</resources>
'''

SR = '''<resources><string name="who">Delio %1$s</string></resources>'''

KT = '''package org.example

class A : Activity() {
    fun show(n: Int, a: String, b: Double) {
        title = getString(R.string.done, n)
        Toast.makeText(this, R.string.who, Toast.LENGTH_SHORT).show()
        label.text = String.format(Locale.getDefault(), getString(R.string.size), a, b)
        other.text = resources.getQuantityString(R.plurals.left, n)
    }
}
'''

JAVA = '''class B {
    String s(Context c, int n) { return c.getString(R.string.who).toString(); }
    String t(Context c, int n) { return String.format("%s", c.getString(R.string.gone)); }
    String u(Context c, int n) { return c.getResources().getQuantityString(com.x.R.plurals.files, n, n); }
}
'''


def _write(folder, name, text):
    path = os.path.join(folder, *name.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def _app(d):
    _write(d, "app/src/main/res/values/strings.xml", EN)
    _write(d, "app/src/main/res/values-fr/strings.xml", FR)
    _write(d, "app/src/main/res/values-b+sr+Latn/strings.xml", SR)
    _write(d, "app/src/main/res/values-night/colors.xml", "<resources/>")
    _write(d, "app/src/main/res/values-car/strings.xml", FR)
    _write(d, "app/src/main/res/values-de/broken.xml", "<resources><string name=")
    _write(d, "app/src/main/java/org/example/A.kt", KT)
    return d


class Index(unittest.TestCase):
    def test_v2_and_v1(self):
        v2 = {"repo": {}, "packages": {"org.a": {"metadata": {
            "name": {"en-US": "A"}, "sourceCode": "https://github.com/x/a", "lastUpdated": 5}}}}
        self.assertEqual(c.parse_index(v2), [{"package": "org.a", "name": "A",
                                              "source": "https://github.com/x/a", "updated": 5}])
        v1 = {"repo": {}, "packages": {}, "apps": [{"packageName": "org.b", "name": "B",
                                                    "sourceCode": "https://gitlab.com/g/b"}]}
        self.assertEqual(c.parse_index(v1), [{"package": "org.b", "name": "B",
                                              "source": "https://gitlab.com/g/b", "updated": 0}])

    def test_repo_of(self):
        self.assertEqual(c.repo_of("https://github.com/Owner/App/tree/main/android"),
                         ("https://github.com/Owner/App.git", "https://github.com/Owner/App",
                          "github.com"))
        self.assertEqual(c.repo_of("https://gitlab.com/group/sub/app/-/tree/master")[1],
                         "https://gitlab.com/group/sub/app")
        self.assertEqual(c.repo_of("https://codeberg.org/o/r.git")[0], "https://codeberg.org/o/r.git")
        self.assertIsNone(c.repo_of("https://github.com/onlyowner"))
        self.assertIsNone(c.repo_of(""))
        self.assertEqual(c.blob_url("https://github.com/o/r", "github.com", "abc", "a/b.xml"),
                         "https://github.com/o/r/blob/abc/a/b.xml")


class Scan(unittest.TestCase):
    def test_scan_tree(self):
        with tempfile.TemporaryDirectory() as d:
            pairs, stats = c.scan_tree(_app(d))
        self.assertEqual(stats["res_dirs"], 1)
        self.assertEqual(stats["locales"], 2)  # fr and b+sr+Latn; de is unreadable, car isn't a locale
        self.assertEqual(stats["bad_xml"], 1)
        found = sorted((p["locale"], p["key"], p["static"]) for p in pairs)
        # Plural forms are checked against the source form with the most
        # arguments: left[one] is now formatted, got[one] may use %2$d and %3$d.
        self.assertEqual(found, [("b+sr+Latn", "who", "ok"),
                                 ("fr", "done", "crash"),
                                 ("fr", "got[one]", "ok"),
                                 ("fr", "got[other]", "ok"),
                                 ("fr", "left[many]", "ok"),
                                 ("fr", "left[one]", "ok"),
                                 ("fr", "left[other]", "crash"),
                                 ("fr", "size", "crash"),
                                 ("fr", "who", "crash")])
        size = [p for p in pairs if p["key"] == "size"][0]
        self.assertEqual(size["types"], "S,D")
        self.assertEqual(size["file"], "values-fr/strings.xml")
        self.assertEqual(size["res"], "app/src/main/res")
        got = [p for p in pairs if p["key"] == "got[one]"][0]
        self.assertEqual((got["source_key"], got["types"]), ("got[other]", "S,I,I"))
        self.assertEqual([p for p in pairs if p["key"] == "left[many]"][0]["source_key"],
                         "left[other]")
        who = [p for p in pairs if p["key"] == "who" and p["locale"] == "fr"][0]
        self.assertEqual(who["source"], "Shared by %1$s")
        self.assertEqual(who["target"], "Partagé par %2$s \U0001F600")
        self.assertEqual(c._b64("\ud83d"), "Pw==")  # a lone surrogate travels as "?"

    def test_code_uses(self):
        with tempfile.TemporaryDirectory() as d:
            _write(d, "app/src/main/java/A.kt", KT)
            _write(d, "lib/src/main/java/B.java", JAVA)
            uses = c.code_uses(d, {("string", "done"), ("string", "who"), ("string", "size"),
                                   ("plurals", "left"), ("string", "gone"),
                                   ("plurals", "files"), ("string", "never")})
        self.assertEqual(uses, {
            ("string", "done"): "formatted",      # getString(id, n)
            ("string", "size"): "formatted",      # String.format(Locale, getString(id), ...)
            ("plurals", "files"): "formatted",    # getQuantityString(id, n, n)
            ("string", "who"): "referenced",      # Toast and getString(id) only
            ("plurals", "left"): "referenced",    # getQuantityString(id, n) doesn't format
            ("string", "gone"): "referenced",     # an argument to format, not the format
            ("string", "never"): "unreferenced"})

    def test_verdict(self):
        self.assertEqual(c.verdict(None), ("no-jvm", ""))
        self.assertEqual(c.verdict(["OK", "UnknownFormatConversionException", "OK",
                                    "UnknownFormatConversionException"]),
                         ("crash", "UnknownFormatConversionException"))
        self.assertEqual(c.verdict(["OK", "IllegalFormatConversionException", "OK", "OK"]),
                         ("crash-if-text", "IllegalFormatConversionException"))
        self.assertEqual(c.verdict(["MissingFormatArgumentException", "OK", "OK", "OK"])[0],
                         "source-fails")
        self.assertEqual(c.verdict(["OK", "OK", "OK", "OK"]), ("ok", ""))


class Local(unittest.TestCase):
    def test_local_run_writes_outputs(self):
        with tempfile.TemporaryDirectory() as d:
            root = _app(os.path.join(d, "app"))
            out = os.path.join(d, "out")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(c.main(["--local", root, "--out-dir", out,
                                         "--data-dir", os.path.join(d, "data")]), 0)
            with open(os.path.join(out, "summary.json"), encoding="utf-8") as f:
                summary = json.load(f)
            with open(os.path.join(out, "findings.csv"), encoding="utf-8", newline="") as f:
                findings = list(csv.DictReader(f))
            with open(os.path.join(out, "report.md"), encoding="utf-8") as f:
                self.assertIn("Translation-crash census", f.read())
        self.assertEqual(summary["formatted_translation_pairs"], 9)
        self.assertEqual(summary["repos_with_formatted_translations"], 1)
        # The four static crashes, with how A.kt uses each string.
        self.assertEqual({(r["locale"], r["key"]): r["use"] for r in findings},
                         {("fr", "done"): "formatted", ("fr", "size"): "formatted",
                          ("fr", "who"): "referenced", ("fr", "left[other]"): "referenced"})
        self.assertIn("source form", summary["plural_rule"])
        if summary["jvm"]:
            # The real Formatter agrees on all four, and the self-check passed.
            self.assertEqual(summary["verdicts"].get("crash"), 4)
            self.assertEqual(summary["static_crash_precision"], 1.0)
            self.assertEqual(summary["crash_by_code_use"],
                             {"formatted": 2, "referenced": 2, "unreferenced": 0, "unknown": 0})
            self.assertEqual(summary["repos_with_formatted_crash"], 1)
            self.assertTrue(all(x["expected"] == x["got"] for x in summary["jvm_selfcheck"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
