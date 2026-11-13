# Tests for vitepress_locales (standard library only, no network).
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

import vitepress_locales as v

# A synthetic .vitepress/config.mts: comments and strings hold braces, colons and a fake
# `locales`, and the search box has its own nested `locales` that must be ignored.
CONFIG_A = """// .vitepress/config.mts for tests
import { defineConfig } from 'vitepress'

const note = "locales: { fake: {} }"
/* locales: { alsoFake: {} } */

export default defineConfig({
  title: 'Demo {site}',
  srcDir: 'docs',
  themeConfig: {
    search: {
      provider: 'local',
      options: {
        locales: {
          zh: { translations: { button: { buttonText: 'Search' } } },
        },
      },
    },
  },
  locales: {
    // English stays at the root
    root: { label: 'English', lang: 'en-US' },
    'zh-CN': { label: 'Chinese', lang: 'zh-CN', link: '/zh-CN/' },
    fr: { label: 'French', lang: 'fr' },
  },
})
"""

PAGES_A = [
    "index.md", "api.md", "guide/intro.md", "guide/setup.md", "blog/post.md",
    "zh-cn/index.md", "zh-cn/guide/intro.md", "zh-cn/guide/setup.md",
    "fr/index.md", "fr/guide/intro.md",
    "de/index.md", "de/guide/intro.md", "de/guide/setup.md",
    "ml/index.md", "ml/models.md",
    "it/index.md", "it/guide/intro.md", "it/config.ts",
]

# Locales built in .vitepress/config/index.ts from per-language files, as VitePress's own
# documentation does.
CONFIG_C_INDEX = """import { defineConfig } from 'vitepress'
import { en } from './en'
import { zh } from './zh'

export default defineConfig({
  locales: {
    root: { label: 'English', ...en },
    zh: { label: 'Chinese', ...zh },
  },
})
"""
CONFIG_C_ZH = """export const zh = { lang: 'zh-Hans', themeConfig: { nav: [] } }
"""

# Top-level locales come from a variable (shorthand); only the search box has a literal.
CONFIG_D = """const locales = { root: {}, ja: {} }
export default defineConfig({
  locales,
  themeConfig: { search: { options: { locales: { ja: {} } } } },
})
"""


def write(root, rel, text="# page\n"):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def site_a(self):
        root = os.path.join(self.tmp, "a")
        write(root, ".vitepress/config.mts", CONFIG_A)
        for rel in PAGES_A:
            write(root, "docs/" + rel)
        return root


class TestHelpers(Base):
    def test_mask_code_hides_braces_in_strings_and_comments(self):
        text = 'const a = "{"; // }\n/* { */ x = \'}\'; y = `${"}"}`'
        masked = v.mask_code(text)
        self.assertEqual(len(masked), len(text))
        self.assertNotIn("{", masked)
        self.assertNotIn("}", masked)
        self.assertEqual(masked.count("\n"), 1)
        self.assertTrue(masked.startswith("const a = "))

    def test_object_keys_shorthand_spread_computed(self):
        text = ("export default defineConfig({ locales: { root: { label: 'English' }, "
                "'pt-BR': ptConfig, ja, ...extra, [k]: v, } })")
        masked = v.mask_code(text)
        brace = v.find_locales_brace(masked)
        self.assertIsNotNone(brace)
        self.assertEqual(text[brace], "{")
        keys, unknown = v.object_keys(text, masked, brace)
        self.assertEqual(keys, ["root", "pt-BR", "ja"])
        self.assertTrue(unknown)

    def test_deep_locales_only_is_not_taken(self):
        masked = v.mask_code(CONFIG_D)
        self.assertIsNone(v.find_locales_brace(masked))

    def test_page_route_and_locale_for_page(self):
        self.assertEqual(v.page_route("index.md"), "/")
        self.assertEqual(v.page_route("guide/index.md"), "/guide/")
        self.assertEqual(v.page_route("zh/foo.md"), "/zh/foo")
        keys = ["root", "zh", "zh-TW"]
        self.assertEqual(v.locale_for_page("zh-TW/a.md", keys), "zh-TW")
        self.assertEqual(v.locale_for_page("zh/index.md", keys), "zh")
        self.assertEqual(v.locale_for_page("zh.md", keys), "root")
        self.assertEqual(v.locale_for_page("zh-tw/a.md", keys), "root")

    def test_looks_like_lang(self):
        for name in ("fr", "zh-Hant", "zh_Hant_TW", "pt-BR", "es-419", "fil", "zh-cn"):
            self.assertTrue(v.looks_like_lang(name), name)
        for name in ("api", "guide", "docs", "v2", "en-US-x", "blog"):
            self.assertFalse(v.looks_like_lang(name), name)


class TestSites(Base):
    def test_site_a(self):
        root = self.site_a()
        r = v.analyse_site(root)
        self.assertEqual(r["config"], ".vitepress/config.mts")
        self.assertEqual(r["locales"], ["root", "zh-CN", "fr"])
        self.assertTrue(r["keys_complete"])
        self.assertEqual(r["src_dir"], "docs")
        self.assertEqual(r["pages"], 17)
        by_dir = dict((d["dir"], d) for d in r["dirs"])
        self.assertEqual(sorted(by_dir), ["de", "fr", "it", "ml", "zh-cn"])
        self.assertEqual(by_dir["fr"]["status"], "listed")
        self.assertEqual(by_dir["fr"]["served_as"], "fr")
        self.assertEqual(by_dir["zh-cn"]["status"], "case_mismatch")
        self.assertEqual(by_dir["zh-cn"]["near_key"], "zh-CN")
        self.assertEqual(by_dir["zh-cn"]["served_as"], "root")
        self.assertEqual(by_dir["de"]["status"], "unlisted")
        self.assertEqual(by_dir["de"]["mirrored_pages"], 3)
        self.assertEqual(by_dir["de"]["served_as"], "root")
        self.assertEqual(by_dir["it"]["status"], "unlisted_dir_config")
        self.assertEqual(by_dir["ml"]["status"], "lang_like_not_mirrored")
        self.assertEqual(by_dir["ml"]["mirrored_pages"], 1)
        self.assertEqual(r["empty_locales"], ["zh-CN"])
        self.assertEqual(r["findings"], 2)

    def test_separator_mismatch_and_locales_override(self):
        root = os.path.join(self.tmp, "b")
        write(root, ".vitepress/config.js", "export default { title: 'x' }\n")
        for rel in ("index.md", "a.md", "b.md", "pt_BR/index.md", "pt_BR/a.md", "pt_BR/b.md"):
            write(root, rel)
        r = v.analyse_site(root)
        self.assertEqual(r["locales"], [])
        self.assertTrue(r["keys_complete"])
        self.assertEqual([d["status"] for d in r["dirs"]], ["unlisted"])
        self.assertEqual(r["findings"], 1)
        r = v.analyse_site(root, locales="root,pt-BR")
        self.assertEqual(r["locales_from"], "--locales")
        self.assertEqual(r["dirs"][0]["status"], "separator_mismatch")
        self.assertEqual(r["dirs"][0]["near_key"], "pt-BR")
        self.assertEqual(r["dirs"][0]["served_as"], "root")
        self.assertEqual(r["empty_locales"], ["pt-BR"])

    def test_config_folder_index(self):
        root = os.path.join(self.tmp, "c")
        write(root, ".vitepress/config/index.ts", CONFIG_C_INDEX)
        write(root, ".vitepress/config/zh.ts", CONFIG_C_ZH)
        write(root, "index.md")
        r = v.analyse_site(root)
        self.assertEqual(r["config"], ".vitepress/config/index.ts")
        self.assertEqual(r["locales"], ["root", "zh"])
        self.assertTrue(r["keys_complete"])
        self.assertEqual(r["empty_locales"], ["zh"])

    def test_locales_from_variable_is_incomplete(self):
        root = os.path.join(self.tmp, "d")
        write(root, ".vitepress/config.ts", CONFIG_D)
        write(root, "index.md")
        r = v.analyse_site(root)
        self.assertEqual(r["locales"], [])
        self.assertFalse(r["keys_complete"])

    def test_cli(self):
        root = self.site_a()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = v.main([root, "--strict"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(buf.getvalue())["findings"], 2)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(v.main([root]), 0)
            self.assertEqual(v.main([os.path.join(self.tmp, "nothing-here")]), 2)


if __name__ == "__main__":
    unittest.main()
