# Unit tests for mech_hugo.py (no network, no Hugo needed).
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mech_hugo as mh  # noqa: E402


def site(exit_code, hits, any_hits=None, top=None, log=""):
    return {"exit": exit_code, "html_hits": hits, "any_hits": any_hits or {},
            "top": top or [], "log": log}


GOOD_A = {
    "MARKAFR": [["fr/posts/hello/index.html", "fr"]],
    "MARKAEN": [["posts/hello/index.html", "en"]],
    "MARKCFR": [["fr/notes/hello/index.html", "fr"]],
    "MARKADE": [["posts/hello.de/index.html", "en"]],
    "MARKAPTUNDER": [["posts/hello.pt_br/index.html", "en"]],
    "MARKAPTDASH": [["pt-br/posts/hello/index.html", "pt-br"]],
    "MARKCDE": [],
}


class Tests(unittest.TestCase):
    def test_expected_sha(self):
        text = "abc123  hugo_0.169.0_linux-amd64.tar.gz\nffff  other.tar.gz\n"
        self.assertEqual(mh.expected_sha(text, "hugo_0.169.0_linux-amd64.tar.gz"), "abc123")
        self.assertIsNone(mh.expected_sha(text, "missing.tar.gz"))
        self.assertEqual(mh.expected_sha("DEAD *x.tgz\n", "x.tgz"), "dead")

    def test_lang_of(self):
        self.assertEqual(mh.lang_of('<p class="lang">LANG=pt-br</p>'), "pt-br")
        self.assertEqual(mh.lang_of("<p>no marker</p>"), "")

    def test_silent(self):
        self.assertTrue(mh.silent_about_de("Start building sites\n | EN | FR | PT-BR\n"))
        self.assertTrue(mh.silent_about_de("WARN default language is en"))
        self.assertFalse(mh.silent_about_de("WARN content/posts/hello.de.md: unknown"))
        self.assertFalse(mh.silent_about_de('WARN language "de" not configured'))

    def test_verdicts_all_held(self):
        a = site(0, GOOD_A, {"MARKAES": []}, ["index.html", "fr", "pt-br", "posts"])
        b = site(0, {"MARKBFR": [["fr/posts/hello/index.html", "fr"]]}, {"MARKBDE": []},
                 ["fr", "posts"])
        v = mh.verdicts(a, b)
        for k in ("K", "K3", "KC", "D", "L1", "L2", "C1", "L3", "S", "KB", "O1"):
            self.assertEqual(v[k], "HELD", k)

    def test_verdicts_failures(self):
        hits = dict(GOOD_A)
        hits["MARKADE"] = [["de/posts/hello/index.html", "de"]]
        hits["MARKCDE"] = [["notes/hello/index.de/index.html", "en"]]
        hits["MARKAPTDASH"] = [["posts/hello.pt-br/index.html", "en"]]
        a = site(0, hits, {"MARKAES": ["es/index.html"]}, ["de", "es", "fr"],
                 log="WARN hello.de.md")
        b = site(0, {"MARKBFR": [["fr/posts/hello/index.html", "fr"]]},
                 {"MARKBDE": ["de/posts/hello/index.html"]}, ["de", "fr"])
        v = mh.verdicts(a, b)
        self.assertEqual(v["K"], "HELD")
        for k in ("D", "L1", "C1", "L3", "S", "O1"):
            self.assertEqual(v[k], "FAILED", k)
        self.assertEqual(v["L2"], "HELD")

    def test_verdicts_controls_fail(self):
        a = site(1, {})
        v = mh.verdicts(a, None)
        self.assertEqual(v["K"], "FAILED")
        self.assertTrue(v["L1"].startswith("NOT TESTABLE"))
        self.assertEqual(v["KB"], "FAILED")
        self.assertTrue(v["O1"].startswith("NOT TESTABLE"))

    def test_scan(self):
        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, "fr", "posts"))
            with open(os.path.join(d, "fr", "posts", "index.html"), "w") as fh:
                fh.write('<p class="lang">LANG=fr</p> MARKAFR')
            with open(os.path.join(d, "index.xml"), "w") as fh:
                fh.write("MARKAFR MARKADE")
            hh, ah, top = mh.scan(d, ["MARKAFR", "MARKADE"])
            self.assertEqual(hh["MARKAFR"], [["fr/posts/index.html", "fr"]])
            self.assertEqual(hh["MARKADE"], [])
            self.assertEqual(ah["MARKAFR"], ["fr/posts/index.html", "index.xml"])
            self.assertEqual(ah["MARKADE"], ["index.xml"])
            self.assertEqual(top, ["fr", "index.xml"])
        finally:
            shutil.rmtree(d)

    def test_sites_well_formed(self):
        for files in (mh.SITE_A, mh.SITE_B):
            self.assertIn("hugo.toml", files)
            self.assertIn("layouts/single.html", files)
            for rel, text in files.items():
                self.assertTrue(text.endswith("\n"), rel)
        self.assertIn("[languages.pt-BR]", mh.SITE_A["hugo.toml"])
        self.assertNotIn("languages.de", mh.SITE_A["hugo.toml"])
        self.assertNotIn("content/de", mh.SITE_B["hugo.toml"])


if __name__ == "__main__":
    unittest.main()
