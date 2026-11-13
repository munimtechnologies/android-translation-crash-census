# Tests for astro_locales (standard library only, no network).
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest

import astro_locales as a

# A synthetic astro.config.mjs: a comment and a string hold a fake i18n block.
CONFIG_A = """// astro.config.mjs for tests: i18n: { locales: ['fake'] } in a comment
import { defineConfig } from 'astro/config';

const note = "i18n: { locales: [] }";

export default defineConfig({
  site: 'https://example.com',
  integrations: [],
  i18n: {
    // the site's languages
    locales: ['en', 'pt-BR', 'fr_CA', 'de', { path: 'spanish', codes: ['es', 'es-MX'] }],
    defaultLocale: 'en',
    routing: { prefixDefaultLocale: false },
  },
});
"""

PAGES_A = [
    "index.astro", "about.astro", "blog/index.astro", "blog/first-post.md", "blog/de.md",
    "tags/[tag].astro",
    "pt-br/index.astro", "pt-br/about.astro",
    "fr_CA/index.astro", "fr_CA/about.astro",
    "de/index.astro", "de/about.astro",
    "spanish/index.astro",
    "it/index.astro", "it/about.astro", "it/blog/index.astro",
    "ml/models.astro",
    "_hidden.astro", "styles.css",
]

LANG_SWITCH = """---
import { getRelativeLocaleUrl } from 'astro:i18n';
const href = getRelativeLocaleUrl(Astro.currentLocale, '', { normalizeLocale: false });
---
<a href={href}>x</a>
"""

# Spread entry, a template literal, double quotes and prefixDefaultLocale: true.
CONFIG_C = """import { defineConfig } from 'astro/config';
const extra = ['ja'];
export default defineConfig({
  i18n: {
    defaultLocale: "en",
    locales: ["en", ...extra, `ko`],
    routing: { prefixDefaultLocale: true, redirectToDefaultLocale: false },
  },
});
"""

# i18n comes from a variable (shorthand property).
CONFIG_D = """import { defineConfig } from 'astro/config';
const i18n = { locales: ['en', 'fr'], defaultLocale: 'en' };
export default defineConfig({ i18n });
"""


def write(root, rel, text="---\n---\n"):
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
        write(root, "astro.config.mjs", CONFIG_A)
        for rel in PAGES_A:
            write(root, "src/pages/" + rel)
        write(root, "src/components/LangSwitch.astro", LANG_SWITCH)
        return root


class TestAstroPorts(Base):
    def test_normalize(self):
        self.assertEqual(a.normalize_the_locale("fr_CA"), "fr-ca")
        self.assertEqual(a.normalize_the_locale("pt-BR"), "pt-br")
        self.assertEqual(a.normalize_the_path("fr.html"), "fr")
        self.assertEqual(a.normalize_the_path("fr.HTML"), "fr.HTML")

    def test_current_locale_precheck_is_case_sensitive(self):
        locs = ["en", "fr"]
        # The example of withastro/astro PR #17984 (closed: "working as expected").
        self.assertEqual(a.compute_current_locale("/FR/about", locs, "en"), "en")
        self.assertEqual(a.compute_current_locale("/fr/about", locs, "en"), "fr")
        self.assertEqual(a.compute_current_locale("/about", locs, "en"), "en")
        # Any segment counts, and .html is stripped (withastro/astro #9970, #14229).
        self.assertEqual(a.compute_current_locale("/blog/fr.html", locs, "en"), "fr")

    def test_current_locale_objects_normalize_codes(self):
        locs = ["en", {"path": "pt_BR", "codes": ["pt-BR"]}]
        self.assertEqual(a.compute_current_locale("/pt_BR/", locs, "en"), "pt-BR")
        self.assertEqual(a.compute_current_locale("/pt-br/", locs, "en"), "pt-BR")
        self.assertEqual(a.compute_current_locale("/PT_br/", locs, "en"), "pt-BR")
        self.assertIsNone(a.compute_current_locale("/", ["fr"], "en"))

    def test_link_segment(self):
        # Astro's docs: getRelativeLocaleUrl("fr_CA", ...) gives /fr-ca/... by default.
        self.assertEqual(a.link_segment("fr_CA"), "fr-ca")
        self.assertEqual(a.link_segment("fr_CA", normalize=False), "fr_CA")
        self.assertEqual(a.link_segment({"path": "Portugues", "codes": ["pt"]}), "portugues")

    def test_suggested_object_form_satisfies_both(self):
        locs = ["en", {"path": "pt-br", "codes": ["pt-BR"]}]
        self.assertEqual(a.compute_current_locale("/pt-br/x", locs, "en"), "pt-BR")
        self.assertEqual(a.link_segment(locs[1]), "pt-br")

    def test_page_route(self):
        self.assertEqual(a.page_route("index.astro"), "/")
        self.assertEqual(a.page_route("fr/index.md"), "/fr/")
        self.assertEqual(a.page_route("blog/de.md"), "/blog/de")


class TestConfig(Base):
    def test_mask_code(self):
        text = 'const a = "{"; // }\n/* { */ x = \'}\'; y = `${"}"}`'
        masked = a.mask_code(text)
        self.assertEqual(len(masked), len(text))
        self.assertNotIn("{", masked)
        self.assertNotIn("}", masked)

    def test_config_a(self):
        root = os.path.join(self.tmp, "ca")
        write(root, "astro.config.mjs", CONFIG_A)
        cfg = a.read_config(root)
        self.assertEqual(cfg["config"], "astro.config.mjs")
        self.assertEqual(cfg["locales"], ["en", "pt-BR", "fr_CA", "de",
                                          {"path": "spanish", "codes": ["es", "es-MX"]}])
        self.assertTrue(cfg["complete"])
        self.assertEqual(cfg["default"], "en")
        self.assertFalse(cfg["prefix_default"])

    def test_config_spread_template_prefix(self):
        root = os.path.join(self.tmp, "cc")
        write(root, "astro.config.ts", CONFIG_C)
        cfg = a.read_config(root)
        self.assertEqual(cfg["config"], "astro.config.ts")
        self.assertEqual(cfg["locales"], ["en", "ko"])
        self.assertFalse(cfg["complete"])
        self.assertEqual(cfg["default"], "en")
        self.assertTrue(cfg["prefix_default"])

    def test_config_variable(self):
        root = os.path.join(self.tmp, "cd")
        write(root, "astro.config.mjs", CONFIG_D)
        cfg = a.read_config(root)
        self.assertIsNone(cfg["locales"])
        self.assertFalse(cfg["complete"])
        self.assertTrue(any("not as an object literal" in w for w in cfg["warnings"]))

    def test_parse_locales_arg(self):
        self.assertEqual(a.parse_locales_arg("en, pt-BR,spanish=es|es-MX,"),
                         ["en", "pt-BR", {"path": "spanish", "codes": ["es", "es-MX"]}])


class TestSites(Base):
    def test_site_a(self):
        root = self.site_a()
        r = a.analyse_site(root)
        self.assertEqual(r["locales_from"], "astro.config.mjs")
        self.assertTrue(r["locales_complete"])
        self.assertEqual(r["default_locale"], "en")
        self.assertEqual(r["pages"], 17)
        self.assertEqual(r["default_current_locale"], "en")
        by = dict((a._ident(e["locale"]), e) for e in r["entries"])
        self.assertEqual(list(by), ["en", "pt-BR", "fr_CA", "de", "spanish"])

        self.assertIsNone(by["en"]["link_segment"])
        self.assertTrue(by["en"]["spelling_ok"])
        self.assertEqual(by["en"]["folders"], [])

        pt = by["pt-BR"]
        self.assertEqual(pt["link_segment"], "pt-br")
        self.assertFalse(pt["spelling_ok"])
        self.assertEqual(pt["suggested_entry"], {"path": "pt-br", "codes": ["pt-BR"]})
        self.assertEqual(pt["folders"], [{"dir": "pt-br", "status": "current_locale_wrong",
                                          "current_locale": "en", "pages": 2}])

        fr = by["fr_CA"]
        self.assertEqual(fr["link_segment"], "fr-ca")
        self.assertFalse(fr["spelling_ok"])
        self.assertEqual(fr["folders"][0]["dir"], "fr_CA")
        self.assertEqual(fr["folders"][0]["status"], "links_miss")
        self.assertEqual(fr["folders"][0]["current_locale"], "fr_CA")

        self.assertTrue(by["de"]["spelling_ok"])
        self.assertEqual(by["de"]["folders"][0]["status"], "ok")
        self.assertTrue(by["spanish"]["spelling_ok"])
        self.assertEqual(by["spanish"]["folders"][0]["status"], "ok")
        self.assertEqual(by["spanish"]["folders"][0]["current_locale"], "es")

        un = dict((u["dir"], u) for u in r["unlisted_dirs"])
        self.assertEqual(sorted(un), ["it", "ml"])
        self.assertEqual(un["it"]["status"], "unlisted")
        self.assertEqual(un["it"]["mirrored_pages"], 3)
        self.assertEqual(un["it"]["current_locale"], "en")
        self.assertEqual(un["ml"]["status"], "lang_like_not_mirrored")

        self.assertEqual(r["later_segment_pages"],
                         [{"page": "blog/de.md", "current_locale": "de"}])
        self.assertEqual(r["dynamic_top_dirs"], [])
        self.assertEqual(r["findings"], 3)
        self.assertTrue(any("normalizeLocale: false" in w
                            and "src/components/LangSwitch.astro" in w for w in r["warnings"]))

    def test_site_b_locales_override(self):
        root = os.path.join(self.tmp, "b")
        for rel in ("en/index.astro", "en/a.astro", "zh-cn/index.astro", "zh-cn/a.astro",
                    "Portugues/index.astro", "[lang]/x.astro"):
            write(root, "src/pages/" + rel)
        self.assertIsNone(a.analyse_site(root))
        r = a.analyse_site(root, locales="en,zh_CN,Portugues=pt|pt-PT", default="en")
        self.assertEqual(r["locales_from"], "--locales")
        self.assertIsNone(r["config"])
        by = dict((a._ident(e["locale"]), e) for e in r["entries"])
        self.assertEqual(by["en"]["folders"][0]["status"], "ok")
        zh = by["zh_CN"]["folders"][0]
        self.assertEqual((zh["dir"], zh["status"], zh["current_locale"]),
                         ("zh-cn", "current_locale_wrong", "en"))
        self.assertEqual(by["zh_CN"]["suggested_entry"], {"path": "zh-cn", "codes": ["zh_CN"]})
        pt = by["Portugues"]
        self.assertEqual(pt["link_segment"], "portugues")
        self.assertEqual(pt["folders"][0]["status"], "links_case_only")
        self.assertEqual(pt["folders"][0]["current_locale"], "pt")
        self.assertEqual(pt["suggested_entry"], {"path": "portugues", "codes": ["pt", "pt-PT"]})
        self.assertEqual(r["unlisted_dirs"], [])
        self.assertEqual(r["dynamic_top_dirs"], ["[lang]"])
        self.assertTrue(any("[lang]" in w for w in r["warnings"]))
        self.assertEqual(r["findings"], 2)

    def test_cli(self):
        root = self.site_a()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = a.main([root, "--strict"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(buf.getvalue())["findings"], 3)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(a.main([root]), 0)
            self.assertEqual(a.main([os.path.join(self.tmp, "nothing-here")]), 2)


if __name__ == "__main__":
    unittest.main()
