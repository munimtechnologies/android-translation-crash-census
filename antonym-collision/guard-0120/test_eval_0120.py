"""Offline tests for eval_0120.py's helpers (no network, no guard build).

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import io
import json
import tarfile
import types
import unittest

import eval_0120 as e

PROJECTS = {p["name"]: p for p in e.OLD + e.NEW}


def stub_guard():
    """Just enough of l10n_guard 0.12.0 for scan(): flat catalogs, and the
    pair "Show" / "Hide" when both keys exist."""
    def pairs(src):
        return [("hide", "show")] if "hide" in src and "show" in src else []

    def collisions(src, tgt):
        out = []
        for k1, k2 in pairs(src):
            v1, v2 = (tgt.get(k1) or "").strip(), (tgt.get(k2) or "").strip()
            if v1 and v1 == v2 and v1.casefold() not in (src[k1].casefold(), src[k2].casefold()):
                out.append({"code": "antonym-collision", "key": k1, "other_key": k2})
        return out

    return types.SimpleNamespace(flatten=lambda d: dict(d), antonym_pairs=pairs,
                                 _antonym_collisions=collisions,
                                 check_catalog=lambda s, t: [{"code": "empty", "key": "x"}] + collisions(s, t))


class LayoutTest(unittest.TestCase):
    def test_new_projects(self):
        cases = [
            ("excalidraw", "packages/excalidraw/locales/en.json", ("", "en")),
            ("excalidraw", "packages/excalidraw/locales/kab-KAB.json", ("", "kab-KAB")),
            ("excalidraw", "packages/excalidraw/locales/percentages.json", None),
            ("immich", "i18n/zh_Hans.json", ("", "zh_Hans")),
            ("immich", "i18n/sr_Cyrl.json", ("", "sr_Cyrl")),
            ("immich", "web/src/i18n/en.json", None),
            ("lobe-chat", "locales/en-US/chat.json", ("chat", "en-US")),
            ("lobe-chat", "locales/ar/desktop-onboarding.json", ("desktop-onboarding", "ar")),
            ("lobe-chat", "packages/x/locales/en-US/chat.json", None),
            ("element-web", "apps/web/src/i18n/strings/en_EN.json", ("", "en_EN")),
            ("element-web", "apps/web/src/i18n/strings/zh_Hant.json", ("", "zh_Hant")),
            ("jitsi-meet", "lang/main.json", ("", "en")),
            ("jitsi-meet", "lang/main-pt-BR.json", ("", "pt-BR")),
            ("jitsi-meet", "lang/main-dsb.json", ("", "dsb")),
            ("jitsi-meet", "lang/languages.json", None),
            ("jitsi-meet", "lang/translation-languages.json", None),
        ]
        for name, path, want in cases:
            self.assertEqual(e.locale_file(PROJECTS[name], path), want, (name, path))

    def test_old_projects_match_the_scan(self):
        noco = PROJECTS["nocobase"]
        self.assertEqual(e.locale_file(noco, "packages/core/client/src/locale/de-DE.json"),
                         ("packages/core/client/src/locale", "de-DE"))
        self.assertEqual(e.locale_file(noco, "locales/id-ID.json"), ("locales", "id-ID"))
        self.assertIsNone(e.locale_file(noco, "packages/x/node_modules/y/locale/de.json"))
        self.assertIsNone(e.locale_file(noco, "packages/x/blocales/de.json"))
        self.assertIsNone(e.locale_file(noco, "packages/x/locale/de/index.json"))
        masto = PROJECTS["mastodon"]
        self.assertEqual(e.locale_file(masto, "app/javascript/mastodon/locales/it.json"),
                         ("app/javascript/mastodon/locales", "it"))
        self.assertIsNone(e.locale_file(masto, "app/javascript/mastodon/locales/x/it.json"))


class UsageTest(unittest.TestCase):
    def test_literals(self):
        found = e.literals("t('video.mute'); _t(\"action|unmute\"); x = `labels.hide`; y = `a.${b}`;")
        self.assertIn("video.mute", found)
        self.assertIn("action|unmute", found)
        self.assertIn("labels.hide", found)
        self.assertNotIn("a.${b}", found)

    def test_candidates(self):
        self.assertIn("action|mute", e.key_candidates("action.mute"))
        self.assertIn("items", e.key_candidates("items_other"))
        self.assertIn("count|items", e.key_candidates("count.items.one"))
        self.assertIn("chat:mute", e.key_candidates("mute", "chat"))
        self.assertTrue(e.used("action.mute", "", {"action|mute"}))
        self.assertFalse(e.used("action.mute", "", {"action.unmute"}))


class ScanTest(unittest.TestCase):
    def test_counts_and_rows(self):
        files = {"": {
            "en": json.dumps({"show": "Show", "hide": "Hide"}).encode(),
            "fr": json.dumps({"show": "Masquer", "hide": "Masquer"}).encode(),
            "pt": json.dumps({"show": "Show", "hide": "Show"}).encode(),
            "de": json.dumps({"show": "Anzeigen", "hide": "Ausblenden"}).encode(),
            "it": json.dumps({"show": "Mostra"}).encode(),
            "en_GB": json.dumps({"show": "Hide", "hide": "Hide"}).encode(),
            "xx": b"not json",
        }}
        res = e.scan(stub_guard(), PROJECTS["immich"], files)
        self.assertEqual(res["groups"], 1)
        self.assertEqual(res["locale_files"], 4)       # fr pt de it; en_GB skipped, xx unparsed
        self.assertEqual(res["unparsed"], ["/xx"])
        self.assertEqual(res["comparisons"], 3)        # it lacks one key
        self.assertEqual(res["copies"], 1)
        self.assertEqual([(r["locale"], r["key1"], r["key2"], r["value"]) for r in res["rows"]],
                         [("fr", "hide", "show", "Masquer")])
        self.assertTrue(res["consistent"])

    def test_no_reference(self):
        res = e.scan(stub_guard(), PROJECTS["immich"], {"": {"fr": b"{}"}})
        self.assertEqual(res["no_reference"], [""])
        self.assertEqual(res["groups"], 0)

    def test_old_projects_keep_english_variants(self):
        files = {"d": {"en-US": json.dumps({"show": "Show", "hide": "Hide"}).encode(),
                       "en-GB": json.dumps({"show": "Hidden", "hide": "Hidden"}).encode()}}
        res = e.scan(stub_guard(), PROJECTS["nocobase"], files)
        self.assertEqual(res["locale_files"], 1)
        self.assertEqual(len(res["rows"]), 1)


class TarTest(unittest.TestCase):
    def test_read_project(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            for path, data in (("repo-abc/i18n/en.json", b'{"a": "Show"}'),
                               ("repo-abc/web/src/x.svelte", b"$t('a') $t('b_one')"),
                               ("repo-abc/node_modules/z/y.js", b"'zz'"),
                               ("repo-abc/i18n/README.md", b"x")):
                info = tarfile.TarInfo(path)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
        buf.seek(0)
        files, found = e.read_project(PROJECTS["immich"], buf, True)
        self.assertEqual(sorted(files[""]), ["en"])
        self.assertEqual(found, {"a", "b_one"})


class SampleTest(unittest.TestCase):
    def test_seeded(self):
        rows = [{"project": "p", "group": "", "locale": "l%03d" % i, "key1": "a", "key2": "b"}
                for i in range(100)]
        first, second = e.sample(rows), e.sample(list(reversed(rows)))
        self.assertEqual(len(first), 60)
        self.assertEqual(first, second)
        self.assertEqual(e.sample(rows[:5]), rows[:5])


if __name__ == "__main__":
    unittest.main()
