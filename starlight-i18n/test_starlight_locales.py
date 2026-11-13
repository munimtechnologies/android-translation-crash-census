# Tests for starlight_locales. Standard library only.
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

import starlight_locales as sl

PAGE = "---\ntitle: Page\n---\nText\n"
CONTENT = ("import { defineCollection } from 'astro:content';\n"
           "import { docsLoader, i18nLoader } from '@astrojs/starlight/loaders';\n"
           "import { docsSchema, i18nSchema } from '@astrojs/starlight/schema';\n"
           "export const collections = {\n"
           "  docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),\n"
           "  i18n: defineCollection({ loader: i18nLoader(), schema: i18nSchema() }),\n"
           "};\n")
CONTENT_DOCS_ONLY = ("import { defineCollection } from 'astro:content';\n"
                     "import { docsLoader } from '@astrojs/starlight/loaders';\n"
                     "import { docsSchema } from '@astrojs/starlight/schema';\n"
                     "export const collections = {\n"
                     "  docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),\n"
                     "};\n")
CONTENT_CUSTOM_ID = ("import { defineCollection } from 'astro:content';\n"
                     "import { docsLoader } from '@astrojs/starlight/loaders';\n"
                     "import { docsSchema } from '@astrojs/starlight/schema';\n"
                     "export const collections = {\n"
                     "  docs: defineCollection({\n"
                     "    loader: docsLoader({ generateId: ({ entry }) => entry }),\n"
                     "    schema: docsSchema(),\n"
                     "  }),\n"
                     "};\n")


def astro_config(locales, extra=""):
    return ("import { defineConfig } from 'astro/config';\n"
            "import starlight from '@astrojs/starlight';\n"
            "export default defineConfig({\n"
            "  integrations: [\n"
            "    starlight({\n"
            "      title: 'Docs',\n" + extra +
            "      locales: {\n" + locales + "      },\n"
            "    }),\n"
            "  ],\n"
            "});\n")


class SiteTest(unittest.TestCase):
    def make_site(self, files):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel, content in files.items():
            path = os.path.join(tmp, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        return tmp

    def docs(self, *rels):
        return dict(("src/content/docs/" + r, PAGE) for r in rels)

    def site(self, locales, docs, extra="", content=CONTENT, more=None):
        files = {"astro.config.mjs": astro_config(locales, extra),
                 "src/content.config.ts": content}
        files.update(self.docs(*docs))
        files.update(more or {})
        return self.make_site(files)

    @staticmethod
    def by_dir(report):
        return dict((d["dir"], d) for d in report["dirs"])


class TestHelpers(unittest.TestCase):
    def test_slug_segment(self):
        self.assertEqual(sl.slug_segment("pt-BR"), "pt-br")
        self.assertEqual(sl.slug_segment("Node.js"), "nodejs")
        self.assertEqual(sl.slug_segment("My Folder"), "my-folder")
        self.assertEqual(sl.slug_segment("pt_BR"), "pt_br")

    def test_rel_to_id(self):
        self.assertEqual(sl.rel_to_id("pt-BR/Guides/Intro.mdx"), "pt-br/guides/intro")
        self.assertEqual(sl.rel_to_id("de/index.md"), "de")
        self.assertEqual(sl.rel_to_id("index.md"), "index")

    def test_normalize_lang(self):
        self.assertEqual(sl.normalize_lang("pt-br"), "pt-BR")
        self.assertEqual(sl.normalize_lang("zh-Hant-tw"), "zh-Hant-TW")
        self.assertEqual(sl.normalize_lang("en"), "en")
        self.assertEqual(sl.normalize_lang("es-419"), "es-419")

    def test_is_rtl(self):
        self.assertTrue(sl.is_rtl("ar"))
        self.assertTrue(sl.is_rtl("fa-IR"))
        self.assertTrue(sl.is_rtl("pa-Arab"))
        self.assertFalse(sl.is_rtl("ar-Latn"))
        self.assertFalse(sl.is_rtl("uz"))
        self.assertFalse(sl.is_rtl("en"))

    def test_looks_like_lang(self):
        self.assertTrue(sl.looks_like_lang("de"))
        self.assertTrue(sl.looks_like_lang("zh-hans"))
        self.assertTrue(sl.looks_like_lang("pt_br"))
        self.assertFalse(sl.looks_like_lang("guide"))
        self.assertFalse(sl.looks_like_lang("xx"))


class TestConfig(SiteTest):
    def test_const_locales_spread_and_scoped_default(self):
        text = ("import { defineConfig } from 'astro/config';\n"
                "import starlight from '@astrojs/starlight';\n"
                "// starlight({ locales: { zz: {} } })\n"
                "const locales = {\n"
                "  root: { label: 'English', lang: 'en' }, // a comment with } brace\n"
                "  'zh-cn': { label: 'Chinese { simplified }', lang: 'zh-CN' },\n"
                "  ...extra,\n"
                "};\n"
                "export default defineConfig({\n"
                "  i18n: { defaultLocale: 'xx', locales: ['en', 'fr'] },\n"
                "  integrations: [\n"
                "    other({ locales: { qq: { label: 'Q' } } }),\n"
                "    starlight({\n"
                "      title: 'Docs',\n"
                "      defaultLocale: 'root',\n"
                "      locales,\n"
                "    }),\n"
                "  ],\n"
                "});\n")
        root = self.make_site({"astro.config.mjs": text})
        info = sl.read_config(root)
        self.assertEqual(list(info["entries"]), ["root", "zh-cn"])
        self.assertTrue(info["unknown"])
        self.assertEqual(info["entries"]["zh-cn"]["lang"], "zh-CN")
        self.assertEqual(info["entries"]["root"]["lang"], "en")
        self.assertEqual(info["default_locale"], "root")

    def test_named_locales_variable(self):
        text = ("import starlight from '@astrojs/starlight';\n"
                "const myLocales: Record<string, object> = {\n"
                "  root: { label: 'English', lang: 'en' },\n"
                "  ar: { label: 'Arabic', dir: 'rtl' },\n"
                "};\n"
                "export default { integrations: [starlight({ locales: myLocales })] };\n")
        root = self.make_site({"astro.config.ts": text})
        info = sl.read_config(root)
        self.assertEqual(list(info["entries"]), ["root", "ar"])
        self.assertFalse(info["unknown"])
        self.assertEqual(info["entries"]["ar"]["dir"], "rtl")

    def test_no_config(self):
        root = self.make_site({"README.md": "x"})
        self.assertIsNone(sl.analyse_site(root))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(sl.main([root]), 2)

    def test_list_pages_skips_and_frontmatter_slug(self):
        root = self.make_site({
            "src/content/docs/_partial.md": PAGE,
            "src/content/docs/.hidden/x.md": PAGE,
            "src/content/docs/notes.txt": "x",
            "src/content/docs/de/x.md": "---\ntitle: X\nslug: guide/x\n---\nText\n",
            "src/content/docs/Guides/Intro.mdx": PAGE,
        })
        pages = sl.list_pages(os.path.join(root, "src", "content", "docs"))
        self.assertEqual([(p["rel"], p["id"]) for p in pages],
                         [("Guides/Intro.mdx", "guides/intro"), ("de/x.md", "guide/x")])


class TestFolders(SiteTest):
    def test_unlisted_folder_served_as_root(self):
        root = self.site("        root: { label: 'English', lang: 'en' },\n"
                         "        fr: { label: 'Francais' },\n",
                         ["index.md", "guide/a.md", "guide/b.md", "fr/index.md",
                          "fr/guide/a.md", "de/index.md", "de/guide/a.md", "de/guide/b.md"])
        rep = sl.analyse_site(root)
        dirs = self.by_dir(rep)
        self.assertEqual(rep["locales"], ["root", "fr"])
        self.assertEqual(dirs["de"]["status"], "unlisted")
        self.assertEqual(dirs["de"]["mirrored_pages"], 3)
        self.assertEqual(dirs["de"]["served_as"], "root")
        self.assertEqual(dirs["fr"]["status"], "listed")
        self.assertEqual(dirs["fr"]["served_as"], "fr")
        self.assertNotIn("guide", dirs)
        self.assertEqual(rep["empty_locales"], [])
        self.assertEqual(rep["findings_by_kind"], {"unlisted": 1})
        self.assertEqual(rep["findings"], 1)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(sl.main([root, "--strict"]), 1)
        self.assertEqual(json.loads(out.getvalue())["findings"], 1)

    def test_uppercase_key_never_matches(self):
        root = self.site("        root: { label: 'English', lang: 'en' },\n"
                         "        'pt-BR': { label: 'Portugues', lang: 'pt-BR' },\n",
                         ["index.md", "guide/a.md", "pt-BR/index.md", "pt-BR/guide/a.md"])
        rep = sl.analyse_site(root)
        d = self.by_dir(rep)["pt-BR"]
        self.assertEqual(d["status"], "key_case")
        self.assertEqual(d["id_segment"], "pt-br")
        self.assertEqual(d["near_key"], "pt-BR")
        self.assertEqual(d["served_as"], "root")
        self.assertEqual(rep["empty_locales"], ["pt-BR"])
        self.assertEqual(rep["findings_by_kind"], {"key_case": 1})

    def test_uppercase_key_with_custom_generate_id(self):
        root = self.site("        root: { label: 'English', lang: 'en' },\n"
                         "        'pt-BR': { label: 'Portugues', lang: 'pt-BR' },\n",
                         ["index.md", "pt-BR/index.md"], content=CONTENT_CUSTOM_ID)
        rep = sl.analyse_site(root)
        self.assertTrue(rep["custom_generate_id"])
        self.assertEqual(self.by_dir(rep)["pt-BR"]["status"], "key_case_custom_ids")
        self.assertEqual(rep["findings"], 0)
        self.assertTrue(any("generateId" in w for w in rep["warnings"]))

    def test_separator_mismatch(self):
        root = self.site("        root: { label: 'English', lang: 'en' },\n"
                         "        'pt-br': { label: 'Portugues', lang: 'pt-BR' },\n",
                         ["index.md", "pt_BR/index.md", "pt_BR/guide/a.md"])
        rep = sl.analyse_site(root)
        d = self.by_dir(rep)["pt_BR"]
        self.assertEqual(d["status"], "separator_mismatch")
        self.assertEqual(d["near_key"], "pt-br")
        self.assertEqual(rep["empty_locales"], ["pt-br"])
        self.assertEqual(rep["findings"], 1)

    def test_uppercase_folder_lowercase_key_is_fine(self):
        root = self.site("        root: { label: 'English', lang: 'en' },\n"
                         "        'pt-br': { label: 'Portugues', lang: 'pt-BR' },\n",
                         ["index.md", "pt-BR/index.md"])
        rep = sl.analyse_site(root)
        self.assertEqual(self.by_dir(rep)["pt-BR"]["status"], "listed")
        self.assertEqual(rep["findings"], 0)

    def test_no_root_serves_unlisted_as_default_locale(self):
        root = self.site("        en: { label: 'English' },\n"
                         "        fr: { label: 'Francais' },\n",
                         ["en/index.md", "en/guide/a.md", "en/guide/b.md", "fr/index.md",
                          "es/index.md", "es/guide/a.md", "es/guide/b.md"],
                         extra="      defaultLocale: 'en',\n")
        rep = sl.analyse_site(root)
        dirs = self.by_dir(rep)
        self.assertEqual(rep["default_locale"], "en")
        self.assertEqual(dirs["es"]["status"], "unlisted")
        self.assertEqual(dirs["es"]["served_as"], "en")
        self.assertEqual(dirs["en"]["status"], "listed")
        self.assertEqual(rep["findings"], 1)

    def test_lang_like_folder_not_mirrored(self):
        root = self.site("        root: { label: 'English', lang: 'en' },\n"
                         "        fr: { label: 'Francais' },\n",
                         ["index.md", "guide/a.md", "it/notes.md"])
        rep = sl.analyse_site(root)
        self.assertEqual(self.by_dir(rep)["it"]["status"], "lang_like_not_mirrored")
        self.assertEqual(rep["findings"], 0)
        self.assertEqual(rep["empty_locales"], ["fr"])

    def test_single_language_site(self):
        files = {"astro.config.mjs": ("import starlight from '@astrojs/starlight';\n"
                                      "export default { integrations: [starlight({ "
                                      "title: 'Docs' })] };\n"),
                 "src/content.config.ts": CONTENT}
        files.update(self.docs("index.md", "guide/a.md", "de/index.md", "de/guide/a.md"))
        root = self.make_site(files)
        rep = sl.analyse_site(root)
        self.assertFalse(rep["multilingual"])
        self.assertEqual(rep["locales"], [])
        self.assertEqual(self.by_dir(rep)["de"]["status"], "unlisted")
        self.assertEqual(self.by_dir(rep)["de"]["served_as"], "root")
        self.assertTrue(any("one language" in w for w in rep["warnings"]))


class TestDirAndUi(SiteTest):
    def test_rtl_without_dir(self):
        root = self.site("        root: { label: 'English', lang: 'en' },\n"
                         "        ar: { label: 'Arabic' },\n"
                         "        he: { label: 'Hebrew', dir: 'rtl' },\n"
                         "        fa: { label: 'Farsi', lang: 'fa-IR' },\n"
                         "        'ar-latn': { label: 'Arabizi', lang: 'ar-Latn' },\n"
                         "        ur: { label: 'Urdu', lang: urduTag },\n"
                         "        uz: { label: 'Uzbek' },\n",
                         ["index.md"])
        rep = sl.analyse_site(root)
        self.assertEqual([r["locale"] for r in rep["rtl_without_dir"]], ["ar", "fa"])
        self.assertEqual(rep["rtl_without_dir"][0]["dir"], "ltr (default)")
        self.assertEqual(rep["locale_settings"]["ur"]["unknown"], ["lang"])
        self.assertEqual(rep["findings_by_kind"], {"rtl_without_dir": 2})

    def test_ui_files(self):
        more = dict(("src/content/i18n/" + n, "{}\n") for n in (
            "en.json", "pt-br.json", "zh-CN.json", "pt.json", "es.json", "ja.json",
            "de_DE.json", "_draft.json"))
        root = self.site("        root: { label: 'English', lang: 'en' },\n"
                         "        'pt-br': { label: 'Portugues', lang: 'pt-BR' },\n"
                         "        'zh-cn': { label: 'Chinese', lang: 'zh-CN' },\n"
                         "        es: { label: 'Espanol' },\n"
                         "        'de-de': { label: 'Deutsch', lang: 'de-DE' },\n",
                         ["index.md"], more=more)
        rep = sl.analyse_site(root)
        got = dict((u["file"], (u["status"], u["lang"])) for u in rep["ui_files"])
        self.assertEqual(got, {
            "en.json": ("used", "en"),
            "pt-br.json": ("case_mismatch", "pt-BR"),
            "zh-CN.json": ("used", "zh-CN"),
            "pt.json": ("base_only", "pt-BR"),
            "es.json": ("used", "es"),
            "ja.json": ("unused", None),
            "de_DE.json": ("separator_mismatch", "de-DE"),
        })
        self.assertEqual(rep["findings_by_kind"], {"ui_case_mismatch": 1,
                                                   "ui_separator_mismatch": 1,
                                                   "ui_base_only": 1})
        self.assertEqual(rep["findings"], 3)
        self.assertFalse(any("i18n collection" in w for w in rep["warnings"]))

    def test_ui_files_without_i18n_collection(self):
        root = self.site("        root: { label: 'English', lang: 'en' },\n"
                         "        fr: { label: 'Francais' },\n",
                         ["index.md"], content=CONTENT_DOCS_ONLY,
                         more={"src/content/i18n/fr.json": "{}\n"})
        rep = sl.analyse_site(root)
        self.assertEqual(rep["ui_files"][0]["status"], "used")
        self.assertTrue(any("no i18n collection" in w for w in rep["warnings"]))

    def test_locales_override(self):
        root = self.site("        root: { label: 'English', lang: 'en' },\n",
                         ["index.md", "guide/a.md", "guide/b.md", "ar/guide/a.md",
                          "ar/guide/b.md"])
        rep = sl.analyse_site(root, locales="root=en,ar=ar=rtl")
        self.assertEqual(rep["locales_from"], "--locales")
        self.assertEqual(self.by_dir(rep)["ar"]["status"], "listed")
        self.assertEqual(rep["rtl_without_dir"], [])
        self.assertEqual(rep["findings"], 0)


if __name__ == "__main__":
    unittest.main()
