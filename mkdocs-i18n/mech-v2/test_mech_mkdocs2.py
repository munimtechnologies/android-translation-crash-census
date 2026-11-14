# Unit tests for mech_mkdocs2.py (no network, no MkDocs needed).
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import os
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mech_mkdocs2 as mm  # noqa: E402


def site(exit_code, hits, markers, log=""):
    full = {m: [] for m in markers}
    full.update(hits)
    return {"exit": exit_code, "hits": full, "files": [], "log": log}


BASE_S = {"MARKSEN": ["index.html"], "MARKSFR": ["fr/index.html"],
          "MARKGUIDE": ["guide/index.html"]}
ALL_S = dict(BASE_S)
ALL_S.update({"MARKMAC": ["setup.mac/index.html"], "MARKMINJS": ["assets/jquery.min.js"],
              "MARKESM": ["assets/app.esm.js"], "MARKMINCSS": ["assets/theme.min.css"]})
N_HITS = dict(ALL_S)
N_HITS["MARKNODEJS"] = ["node.js/index.html"]
BASE_F = {"MARKFEN": ["index.html"], "MARKFFR": ["fr/index.html"],
          "MARKFXTRA": ["javascripts/extra.js"]}
ALL_F = dict(BASE_F)
ALL_F.update({"MARKIMG": ["img/diagram.svg"], "MARKFCSS": ["css/extra.css"]})
PA = {"mkdocs": "1.6.1", "mkdocs-static-i18n": "1.3.1", "ast": False, "min": False, "js": True}
PB = {"mkdocs": "1.6.1", "mkdocs-static-i18n": "1.3.1", "ast": True, "min": True, "js": True}
KEYS = ("KP", "KA", "KB", "K0", "KFA", "KFB", "B1", "B2", "C1", "C2", "R1", "R2", "R3", "R4",
        "R5", "R6", "S2")


def good():
    return (PA, PB, site(0, ALL_S, mm.MARKERS_S), site(0, BASE_S, mm.MARKERS_S),
            site(0, N_HITS, mm.MARKERS_S), site(0, ALL_F, mm.MARKERS_F),
            site(0, BASE_F, mm.MARKERS_F))


class Tests(unittest.TestCase):
    def test_markers_not_substrings(self):
        group = mm.MARKERS_S + mm.MARKERS_F
        self.assertEqual(len(group), len(set(group)))
        for a in group:
            for b in group:
                if a != b:
                    self.assertNotIn(a, b, (a, b))

    def test_every_marker_once_in_its_site(self):
        for files, markers in ((mm.SITE_S, mm.MARKERS_S), (mm.SITE_N, mm.MARKERS_S),
                               (mm.SITE_F, mm.MARKERS_F)):
            body = "".join(files.values())
            for m in markers:
                self.assertEqual(body.count(m), 1, m)

    def test_sites_well_formed(self):
        self.assertIn("docs_structure: suffix", mm.SITE_S["mkdocs.yml"])
        self.assertIn("docs_structure: folder", mm.SITE_F["mkdocs.yml"])
        self.assertIn("plugins: []", mm.SITE_N["mkdocs.yml"])
        self.assertNotIn("i18n", mm.SITE_N["mkdocs.yml"])
        for files in (mm.SITE_S, mm.SITE_N, mm.SITE_F):
            for rel, text in files.items():
                self.assertTrue(text.endswith("\n"), rel)
                self.assertTrue(rel == "mkdocs.yml" or rel.startswith("docs/"), rel)
                self.assertNotIn("\t", text)
        for rel in ("docs/assets/jquery.min.js", "docs/assets/app.esm.js",
                    "docs/assets/theme.min.css", "docs/setup.mac.md"):
            self.assertIn(rel, mm.SITE_S)
        for rel in ("docs/img/diagram.svg", "docs/css/extra.css", "docs/api/index.md"):
            self.assertIn(rel, mm.SITE_F)
        self.assertIn("assets/jquery.min.js", mm.SITE_S["mkdocs.yml"])
        self.assertIn("assets/theme.min.css", mm.SITE_S["mkdocs.yml"])
        self.assertIn("css/extra.css", mm.SITE_F["mkdocs.yml"])

    def test_all_held(self):
        v = mm.verdicts(*good())
        for k in KEYS:
            self.assertEqual(v[k], "HELD", k)

    def test_pr_publishes_everything_fails_r(self):
        pa, pb, sa, _sb, n, fa, _fb = good()
        v = mm.verdicts(pa, pb, sa, site(0, ALL_S, mm.MARKERS_S), n, fa,
                        site(0, ALL_F, mm.MARKERS_F))
        for k in ("R1", "R2", "R3", "R4", "R5", "R6"):
            self.assertEqual(v[k], "FAILED", k)
        self.assertEqual(v["B1"], "HELD")

    def test_baseline_drops_fails_b(self):
        pa, pb, _sa, sb, n, _fa, fb = good()
        v = mm.verdicts(pa, pb, site(0, BASE_S, mm.MARKERS_S), sb, n,
                        site(0, BASE_F, mm.MARKERS_F), fb)
        self.assertEqual(v["B1"], "FAILED")
        self.assertEqual(v["B2"], "FAILED")

    def test_nodejs_and_js_folder_published_fail_c(self):
        pa, pb, sa, sb, n, fa, fb = good()
        sb2 = site(0, dict(BASE_S, MARKNODEJS=["node.js/index.html"]), mm.MARKERS_S)
        fa2 = site(0, dict(ALL_F, MARKFJS=["js/custom.js"]), mm.MARKERS_F)
        v = mm.verdicts(pa, pb, sa, sb2, n, fa2, fb)
        self.assertEqual(v["C1"], "FAILED")
        self.assertEqual(v["C2"], "FAILED")

    def test_probe_control(self):
        pa, pb, sa, sb, n, fa, fb = good()
        v = mm.verdicts(pa, dict(PB, ast=False), sa, sb, n, fa, fb)
        self.assertEqual(v["KP"], "FAILED")
        for k in ("R1", "R5", "S2"):
            self.assertTrue(v[k].startswith("NOT TESTABLE"), k)
        self.assertEqual(v["B1"], "HELD")

    def test_build_failure_controls(self):
        pa, pb, sa, sb, n, fa, fb = good()
        v = mm.verdicts(pa, pb, sa, site(1, {}, mm.MARKERS_S), n, fa, site(1, {}, mm.MARKERS_F))
        self.assertEqual(v["KB"], "FAILED")
        self.assertEqual(v["KFB"], "FAILED")
        for k in ("C1", "C2", "R1", "R4", "R5", "R6", "S2"):
            self.assertTrue(v[k].startswith("NOT TESTABLE"), k)
        self.assertEqual(v["B1"], "HELD")
        self.assertEqual(v["B2"], "HELD")

    def test_no_plugin_control(self):
        pa, pb, sa, sb, _n, fa, fb = good()
        v = mm.verdicts(pa, pb, sa, sb, site(0, BASE_S, mm.MARKERS_S), fa, fb)
        self.assertEqual(v["K0"], "FAILED")
        self.assertTrue(v["B1"].startswith("NOT TESTABLE"))
        self.assertTrue(v["R1"].startswith("NOT TESTABLE"))
        self.assertEqual(v["R5"], "HELD")

    def test_silence(self):
        pa, pb, sa, _sb, n, fa, fb = good()
        loud = site(0, BASE_S, mm.MARKERS_S,
                    log="INFO - Skipping 'assets/jquery.min.js' (language min not built)\n")
        v = mm.verdicts(pa, pb, sa, loud, n, fa, fb)
        self.assertEqual(v["S2"], "FAILED")

    def test_scan(self):
        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, "img"))
            with open(os.path.join(d, "img", "diagram.svg"), "w") as fh:
                fh.write("<svg><!-- MARKIMG --></svg>")
            with open(os.path.join(d, "index.html"), "w") as fh:
                fh.write("MARKFEN")
            hits, allf = mm.scan(d, ["MARKIMG", "MARKFEN", "MARKFCSS"])
            self.assertEqual(hits["MARKIMG"], ["img/diagram.svg"])
            self.assertEqual(hits["MARKFEN"], ["index.html"])
            self.assertEqual(hits["MARKFCSS"], [])
            self.assertEqual(allf, ["img/diagram.svg", "index.html"])
        finally:
            shutil.rmtree(d)


if __name__ == "__main__":
    unittest.main()
