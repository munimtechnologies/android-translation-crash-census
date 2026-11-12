# Unit tests for mech_mkdocs.py (no network, no MkDocs needed).
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mech_mkdocs as mm  # noqa: E402


def site(exit_code, hits, markers, log="", texts=None):
    full = {m: [] for m in markers}
    full.update(hits)
    return {"exit": exit_code, "hits": full, "files": [], "log": log, "texts": texts or {}}


GOOD_S = {
    "MARKSEN": ["index.html"],
    "MARKSFR": ["fr/index.html"],
    "MARKJSX": ["node.jsx/index.html"],
    "MARKREL": ["release_17.1/index.html"],
    "MARKPTUNDER": ["fr/guide.pt_br/index.html", "guide.pt_br/index.html"],
}
GOOD_N = {"MARKNODEJS": ["node.js/index.html"], "MARKSOCKETIO": ["socket.io/index.html"],
          "MARKESJS": ["assets/widget.es.js"], "MARKDE": ["guide.de/index.html"]}
WARN = ("INFO    -  Cleaning site directory\n"
        "WARNING -  Doc file 'guide.md' contains a link 'socket.io.md', but the target is not "
        "found among documentation files.\n")
GOOD_F = {"MARKFEN": ["index.html"], "MARKFFR": ["fr/index.html"],
          "MARKFXTRA": ["javascripts/extra.js"]}
F_TEXTS = {"index.html": '<script src="js/custom.js"></script>'}


class Tests(unittest.TestCase):
    def test_markers_not_prefixes(self):
        for group in (mm.MARKERS_S, mm.MARKERS_F, mm.MARKERS_S + mm.MARKERS_F):
            for a in group:
                for b in group:
                    if a != b:
                        self.assertNotIn(a, b, (a, b))

    def test_every_marker_is_in_its_site(self):
        for files, markers in ((mm.SITE_S, mm.MARKERS_S), (mm.SITE_N, mm.MARKERS_S),
                               (mm.SITE_F, mm.MARKERS_F)):
            body = "".join(files.values())
            for m in markers:
                self.assertEqual(body.count(m), 1, m)

    def test_sites_well_formed(self):
        self.assertIn("docs_structure: suffix", mm.SITE_S["mkdocs.yml"])
        self.assertIn("plugins: []", mm.SITE_N["mkdocs.yml"])
        self.assertNotIn("i18n", mm.SITE_N["mkdocs.yml"])
        self.assertIn("docs_structure: folder", mm.SITE_F["mkdocs.yml"])
        for files in (mm.SITE_S, mm.SITE_N, mm.SITE_F):
            for rel, text in files.items():
                self.assertTrue(text.endswith("\n"), rel)
                self.assertTrue(rel == "mkdocs.yml" or rel.startswith("docs/"), rel)
            for line in files["mkdocs.yml"].splitlines():
                self.assertNotIn("\t", line)
        for lang in ("locale: de", "locale: pt"):
            self.assertNotIn(lang, mm.SITE_S["mkdocs.yml"])

    def test_verdicts_all_held(self):
        s = site(0, GOOD_S, mm.MARKERS_S, log=WARN)
        n = site(0, GOOD_N, mm.MARKERS_S)
        f = site(0, GOOD_F, mm.MARKERS_F, texts=F_TEXTS)
        v = mm.verdicts(s, n, f)
        for k in ("K", "KX", "K0", "D1", "D2", "A1", "D3", "D4", "L1", "W", "S", "KF", "F1",
                  "F2"):
            self.assertEqual(v[k], "HELD", k)

    def test_verdicts_failures(self):
        hits = dict(GOOD_S)
        hits["MARKNODEJS"] = ["node/index.html"]
        hits["MARKSOCKETIO"] = ["socket.io/index.html"]
        hits["MARKESJS"] = ["assets/widget.es.js"]
        hits["MARKDE"] = ["de/guide/index.html"]
        hits["MARKPTDASH"] = ["pt-BR/guide/index.html"]
        hits["MARKPTUNDER"] = ["pt_br/guide/index.html"]
        s = site(0, hits, mm.MARKERS_S, log="INFO - Ignore js None node.js.md\n")
        n = site(0, GOOD_N, mm.MARKERS_S)
        fh = dict(GOOD_F)
        fh["MARKFJS"] = ["js/custom.js"]
        f = site(0, fh, mm.MARKERS_F, texts={"index.html": "<p>no script</p>"})
        v = mm.verdicts(s, n, f)
        self.assertEqual(v["K"], "HELD")
        for k in ("D1", "D2", "A1", "D3", "D4", "L1", "W", "S", "F1", "F2"):
            self.assertEqual(v[k], "FAILED", k)

    def test_controls_fail(self):
        s = site(1, {}, mm.MARKERS_S)
        n = site(0, GOOD_N, mm.MARKERS_S)
        f = site(1, {}, mm.MARKERS_F)
        v = mm.verdicts(s, n, f)
        self.assertEqual(v["K"], "FAILED")
        self.assertEqual(v["KX"], "FAILED")
        self.assertEqual(v["KF"], "FAILED")
        self.assertTrue(v["D1"].startswith("NOT TESTABLE"))
        self.assertTrue(v["F1"].startswith("NOT TESTABLE"))

    def test_no_plugin_control_needed(self):
        s = site(0, GOOD_S, mm.MARKERS_S, log=WARN)
        n = site(0, {}, mm.MARKERS_S)
        v = mm.verdicts(s, n, site(0, GOOD_F, mm.MARKERS_F, texts=F_TEXTS))
        self.assertEqual(v["K0"], "FAILED")
        self.assertTrue(v["D1"].startswith("NOT TESTABLE"))
        self.assertEqual(v["F1"], "HELD")

    def test_scan_and_keep_texts(self):
        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, "fr"))
            with open(os.path.join(d, "fr", "index.html"), "w") as fh:
                fh.write("MARKSFR")
            with open(os.path.join(d, "index.html"), "w") as fh:
                fh.write("MARKSEN js/custom.js")
            hits, allf = mm.scan(d, ["MARKSEN", "MARKSFR", "MARKDE"])
            self.assertEqual(hits["MARKSEN"], ["index.html"])
            self.assertEqual(hits["MARKSFR"], ["fr/index.html"])
            self.assertEqual(hits["MARKDE"], [])
            self.assertEqual(allf, ["fr/index.html", "index.html"])
            st = {}
            mm.keep_texts(st, d, ["index.html", "missing.html"])
            self.assertEqual(mm.open_text(st, "index.html"), "MARKSEN js/custom.js")
            self.assertEqual(mm.open_text(st, "missing.html"), "")
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
