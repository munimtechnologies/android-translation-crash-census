# Unit tests for docu_core (pure; no network). Made with AI agents by MV2 of Munim, Inc.
# Apache-2.0.
import unittest

import docu_core as dc

TS_CONFIG = """
import type {Config} from '@docusaurus/types';
// i18n was: locales: ['en', 'de']
const config: Config = {
  title: 'Site', // a title with 'quotes'
  url: 'https://example.com/a//b',
  i18n: {
    defaultLocale: 'en',
    locales: ['en', "zh-CN", `pt-BR`,], /* 'ja' later */
    localeConfigs: {
      'zh-CN': {label: 'Chinese', htmlLang: 'zh-CN'},
      ja: {path: 'japanese', label: 'JA'},
    },
  },
  presets: [['classic', {docs: {path: '../docs'}}]],
};
export default config;
"""


class ParseTest(unittest.TestCase):
    def test_ts_config(self):
        c = dc.parse_config(TS_CONFIG)
        self.assertEqual(c["status"], "ok", c["why"])
        self.assertEqual(c["default_locale"], "en")
        self.assertEqual(c["locales"], ["en", "zh-CN", "pt-BR"])
        self.assertEqual(c["paths"], {"ja": "japanese"})
        self.assertEqual(c["i18n_path"], "i18n")
        self.assertIn("'de'", c["comments"])
        self.assertIn("'ja' later", c["comments"])
        self.assertNotIn("'ja' later", c["code"])
        self.assertIn("https://example.com/a//b", c["code"])

    def test_default_when_no_i18n(self):
        c = dc.parse_config("module.exports = {title: 'x', url: 'https://x.org'};")
        self.assertEqual(c["status"], "default")
        self.assertEqual(c["locales"], ["en"])

    def test_i18n_in_comment_only_is_default(self):
        c = dc.parse_config("// i18n: {locales: ['en','fr']}\nmodule.exports = {title: 'x'};")
        self.assertEqual(c["status"], "default")

    def test_unparsed_cases(self):
        cases = [
            "const i18n = {defaultLocale: 'en', locales: ['en']};\nmodule.exports = {i18n};",
            "module.exports = {i18n: i18nConfig};",
            "module.exports = {i18n: {defaultLocale: 'en', locales}};",
            "module.exports = {i18n: {defaultLocale: 'en', locales: LOCALES}};",
            "module.exports = {i18n: {defaultLocale: 'en', locales: ['en', ...more]}};",
            "module.exports = {i18n: {defaultLocale: 'en', locales: ['en', `${x}`]}};",
            "module.exports = {i18n: {defaultLocale: 'en', locales: ['en'], ...extra}};",
            "module.exports = {i18n: {defaultLocale: 'en', locales: ['en'], path: '../x'}};",
        ]
        for t in cases:
            c = dc.parse_config(t)
            self.assertEqual(c["status"], "unparsed", t)
            self.assertTrue(c["why"], t)

    def test_i18n_path(self):
        c = dc.parse_config("module.exports={i18n:{defaultLocale:'fr',locales:['fr','en'],"
                            "path:'./translations/'}}")
        self.assertEqual(c["status"], "ok", c["why"])
        self.assertEqual(c["i18n_path"], "translations")
        self.assertEqual(c["default_locale"], "fr")

    def test_quoted_key(self):
        c = dc.parse_config('{"i18n": {"defaultLocale": "en", "locales": ["en", "ko"]}}')
        self.assertEqual(c["status"], "ok", c["why"])
        self.assertEqual(c["locales"], ["en", "ko"])

    def test_string_helpers(self):
        self.assertEqual(dc.string_literal("'a\\'b'"), "a'b")
        self.assertIsNone(dc.string_literal("'a' + 'b'"))
        self.assertEqual(dc.parse_string_array("[ 'a', \"b\" , ]"), ["a", "b"])
        self.assertIsNone(dc.parse_string_array("['a', b]"))


class ClassifyTest(unittest.TestCase):
    def setUp(self):
        self.cfg = dc.parse_config(TS_CONFIG)

    def test_classes(self):
        got = {(r["folder"], r["cls"], r["locale"])
               for r in dc.classify(self.cfg, ["en", "zh-cn", "pt_BR", "japanese", "de"])}
        self.assertEqual(got, {("en", "configured", "en"),
                               ("zh-cn", "mismatch", "zh-CN"),
                               ("pt_BR", "mismatch", "pt-BR"),
                               ("japanese", "orphan", ""),
                               ("de", "orphan", "")})

    def test_variant_dup_and_missing(self):
        got = {(r["folder"], r["cls"], r["locale"])
               for r in dc.classify(self.cfg, ["zh-CN", "zh-cn"])}
        self.assertEqual(got, {("zh-CN", "configured", "zh-CN"),
                               ("zh-cn", "variant-dup", "zh-CN"),
                               ("", "missing", "pt-BR")})

    def test_locale_config_path(self):
        cfg = dc.parse_config("module.exports={i18n:{defaultLocale:'en',locales:['en','ja'],"
                              "localeConfigs:{ja:{path:'japanese'}}}}")
        got = {(r["folder"], r["cls"]) for r in dc.classify(cfg, ["japanese", "ja"])}
        self.assertEqual(got, {("japanese", "configured"), ("ja", "orphan")})


class MiscTest(unittest.TestCase):
    def test_english_candidates(self):
        self.assertEqual(
            dc.english_candidates("website", "docusaurus-plugin-content-docs/current/a/b.md"),
            ["website/docs/a/b.md", "docs/a/b.md"])
        self.assertEqual(
            dc.english_candidates("", "docusaurus-plugin-content-docs/version-2.0/x.md"),
            ["versioned_docs/version-2.0/x.md"])
        self.assertEqual(dc.english_candidates("w", "docusaurus-plugin-content-pages/i.md"),
                         ["w/src/pages/i.md"])
        self.assertEqual(dc.english_candidates("", "docusaurus-plugin-content-blog/p.md"),
                         ["blog/p.md"])
        self.assertEqual(dc.english_candidates("", "docusaurus-theme-classic/navbar.json"), [])

    def test_cli_and_quotes(self):
        self.assertTrue(dc.cli_mentions(['"start:de": "docusaurus start --locale de"'], "de"))
        self.assertTrue(dc.cli_mentions(["npm run build -- --locale=de"], "de"))
        self.assertFalse(dc.cli_mentions(["docusaurus start --locale de-AT"], "de"))
        self.assertTrue(dc.quoted_in("// locales: ['en', 'de']", "de"))
        self.assertFalse(dc.quoted_in("// locales: ['en', 'de-AT']", "de"))
        self.assertEqual(dc.squash(" a\n b\t"), "ab")


if __name__ == "__main__":
    unittest.main()
