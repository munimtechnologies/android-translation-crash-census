# Tests for sphinx_locales (standard library only, no network).
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

import sphinx_locales as s


def kinds(report):
    return [f["kind"] for f in report["findings"]]


def warning_kinds(report):
    return [w["kind"] for w in report["warnings"]]


class SiteCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="sphinx-locales-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def site(self, conf, files):
        for rel in files:
            path = os.path.join(self.root, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write('msgid ""\nmsgstr ""\n')
        with open(os.path.join(self.root, "conf.py"), "w", encoding="utf-8") as handle:
            handle.write(conf)
        return self.root


class ConfReading(SiteCase):
    def test_literals(self):
        d = self.site("language = 'pt_BR'\nlocale_dirs = ['locales']\n", [])
        conf = s.read_conf(d)
        self.assertTrue(conf["found"])
        self.assertTrue(conf["parsed"])
        self.assertEqual(conf["language"], "pt_BR")
        self.assertEqual(conf["locale_dirs"], ["locales"])
        self.assertTrue(conf["locale_dirs_set"])
        self.assertTrue(conf["gettext_auto_build"])

    def test_last_assignment_wins(self):
        d = self.site("language = 'de'\nif True:\n    language = 'fr'\n", [])
        self.assertEqual(s.read_conf(d)["language"], "fr")

    def test_rtd_env_language(self):
        conf = 'import os\nlanguage = os.environ.get("READTHEDOCS_LANGUAGE", "en")\n'
        d = self.site(conf, [])
        report = s.check(d)
        self.assertIsNone(report["conf"]["language"])
        self.assertIn("READTHEDOCS_LANGUAGE", report["conf"]["language_expr"])
        self.assertIn("language_from_rtd_env", warning_kinds(report))
        self.assertIn("no_language", warning_kinds(report))
        self.assertEqual(kinds(report), [])


class Mechanisms(SiteCase):
    def test_exact_folder_ok(self):
        d = self.site("language = 'pt_BR'\nlocale_dirs = ['locales']\n",
                      ["locales/pt_BR/LC_MESSAGES/index.po"])
        report = s.check(d)
        self.assertEqual(len(report["languages"]), 1)
        self.assertEqual(report["languages"][0]["status"], "ok")
        self.assertEqual(report["languages"][0]["exact_dirs"], ["locales/pt_BR"])
        self.assertEqual(kinds(report), [])

    def test_fallback_uncompiled(self):
        d = self.site("locale_dirs = ['locales']\n",
                      ["locales/pt/LC_MESSAGES/index.po",
                       "locales/pt/LC_MESSAGES/api/ref.po"])
        report = s.check(d, languages=["pt_BR"])
        result = report["languages"][0]
        self.assertIn("pt", result["lookup_order"])
        self.assertEqual(result["status"], "fallback_uncompiled")
        self.assertEqual(result["fallback_dirs"], ["locales/pt"])
        self.assertEqual(result["uncompiled_fallback_domains"], ["api/ref", "index"])
        self.assertEqual(kinds(report), ["fallback_uncompiled"])

    def test_fallback_with_committed_mo(self):
        d = self.site("locale_dirs = ['locales']\n",
                      ["locales/pt/LC_MESSAGES/index.po",
                       "locales/pt/LC_MESSAGES/index.mo"])
        report = s.check(d, languages=["pt_BR"])
        self.assertEqual(report["languages"][0]["status"], "fallback_mo")
        self.assertEqual(kinds(report), [])
        self.assertIn("fallback_mo", warning_kinds(report))

    def test_case_mismatch(self):
        d = self.site("locale_dirs = ['locales']\n",
                      ["locales/zh_cn/LC_MESSAGES/index.po"])
        report = s.check(d, languages=["zh_CN"])
        self.assertEqual(report["languages"][0]["status"], "missing")
        self.assertEqual(kinds(report), ["case_mismatch"])
        self.assertEqual(report["findings"][0]["path"], "locales/zh_cn")

    def test_separator_mismatch_both_ways(self):
        d = self.site("locale_dirs = ['locales']\n",
                      ["locales/pt-br/LC_MESSAGES/index.po"])
        self.assertEqual(kinds(s.check(d, languages=["pt_BR"])), ["separator_mismatch"])
        shutil.rmtree(os.path.join(d, "locales"))
        self.site("locale_dirs = ['locales']\n", ["locales/pt_BR/LC_MESSAGES/index.po"])
        report = s.check(d, languages=["pt-br"])
        self.assertEqual(report["languages"][0]["lookup_order"], ["pt-br"])
        self.assertEqual(kinds(report), ["separator_mismatch"])

    def test_duplicate_near_miss_is_only_a_warning(self):
        d = self.site("locale_dirs = ['locales']\n",
                      ["locales/pt_BR/LC_MESSAGES/index.po",
                       "locales/pt-br/LC_MESSAGES/index.po"])
        report = s.check(d, languages=["pt_BR"])
        self.assertEqual(report["languages"][0]["status"], "ok")
        self.assertEqual(kinds(report), [])
        self.assertIn("duplicate_separator_mismatch", warning_kinds(report))

    def test_rtd_language_is_mapped(self):
        d = self.site("locale_dirs = ['locales']\n",
                      ["locales/zh_Hant/LC_MESSAGES/index.po"])
        report = s.check(d, rtd_languages=["zh-tw"])
        self.assertEqual(report["languages"][0]["language"], "zh_TW")
        self.assertEqual(report["languages"][0]["requested_as"], "zh-tw (Read the Docs)")
        self.assertEqual(kinds(report), ["missing"])
        shutil.rmtree(os.path.join(d, "locales"))
        self.site("locale_dirs = ['locales']\n", ["locales/zh_TW/LC_MESSAGES/index.po"])
        report = s.check(d, rtd_languages=["zh-tw"])
        self.assertEqual(report["languages"][0]["status"], "ok")
        self.assertEqual(kinds(report), [])

    def test_locale_folder_without_locale_dirs(self):
        d = self.site("project = 'demo'\n", ["locale/de/LC_MESSAGES/index.po"])
        report = s.check(d, languages=["de"])
        self.assertEqual(report["locale_dirs"], ["locales"])
        self.assertEqual(report["locale_dirs_source"], "default")
        self.assertIn("locale_dirs_default_mismatch", kinds(report))

    def test_auto_build_off(self):
        d = self.site("language = 'fr'\ngettext_auto_build = False\n",
                      ["locales/fr/LC_MESSAGES/index.po"])
        report = s.check(d)
        self.assertFalse(report["conf"]["gettext_auto_build"])
        self.assertEqual(report["languages"][0]["status"], "auto_build_off")
        self.assertEqual(kinds(report), ["auto_build_off"])

    def test_po_outside_lc_messages(self):
        d = self.site("locale_dirs = ['locales']\n", ["locales/de/index.po"])
        report = s.check(d, languages=["de"])
        self.assertIn("no_lc_messages", kinds(report))

    def test_english_missing_is_not_a_finding(self):
        d = self.site("project = 'demo'\n", [])
        report = s.check(d, languages=["en"])
        self.assertEqual(report["languages"][0]["status"], "missing")
        self.assertEqual(kinds(report), [])


class Cli(SiteCase):
    def test_strict_exit_codes_and_json(self):
        d = self.site("locale_dirs = ['locales']\n", ["locales/pt/LC_MESSAGES/index.po"])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = s.main([d, "--language", "pt_BR", "--strict"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())["findings"][0]["kind"],
                         "fallback_uncompiled")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = s.main([d, "--language", "pt", "--strict"])
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
