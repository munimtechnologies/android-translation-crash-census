"""Offline tests for eval_holdout2.py (no network). The tests that need the
released guard load it from $GUARD_PATH (default /out/guard/l10n_guard.py,
where the job's first step puts it) and are skipped when it is absent.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import io
import json
import os
import tarfile
import unittest

import eval_holdout2 as e

GUARD_PATH = os.environ.get("GUARD_PATH", "/out/guard/l10n_guard.py")
P = {p["name"]: p for p in e.PROJECTS}


def tarball(members, comment):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.PAX_FORMAT,
                      pax_headers={"comment": comment}) as tar:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    buf.seek(0)
    return buf


class LayoutTest(unittest.TestCase):
    def test_locale_files(self):
        cases = [
            ("jellyfin-web", "src/strings/fr.json", "fr"),
            ("jellyfin-web", "src/strings/es_419.json", "es_419"),
            ("jellyfin-web", "src/strings/en-us.json", "en-us"),
            ("uptime-kuma", "src/lang/ca@valencia.json", "ca@valencia"),
            ("uptime-kuma", "src/lang/sr-latn.json", "sr-latn"),
            ("uptime-kuma", "src/lang/README.md", None),
            ("rocket-chat", "packages/i18n/src/locales/pt-BR.i18n.json", "pt-BR"),
            ("rocket-chat", "packages/i18n/src/locales/pt-BR.json", None),
            ("mattermost", "webapp/channels/src/i18n/zh-TW.json", "zh-TW"),
            ("mattermost", "webapp/channels/src/i18n/i18n.ts", None),
            ("bitwarden-web", "apps/web/src/locales/pt_BR/messages.json", "pt_BR"),
            ("bitwarden-web", "apps/browser/src/_locales/de/messages.json", None),
            ("uptime-kuma", "node_modules/x/src/lang/fr.json", None),
        ]
        for name, path, lang in cases:
            self.assertEqual(e.locale_file(P[name], path), lang, path)

    def test_skipped(self):
        self.assertTrue(e.skipped(P["jellyfin-web"], "en-us"))
        self.assertTrue(e.skipped(P["jellyfin-web"], "en_US"))
        self.assertTrue(e.skipped(P["uptime-kuma"], "enm"))
        self.assertFalse(e.skipped(P["uptime-kuma"], "fr-FR"))

    def test_identical_files(self):
        files = {"en": b"x", "fr": b"a", "fr-FR": b"a", "de": b"b"}
        self.assertEqual(e.identical_files(P["uptime-kuma"], files), [["fr", "fr-FR"]])


class KeyTest(unittest.TestCase):
    def test_candidates(self):
        self.assertTrue({"foo.message", "foo", "foo|message"} <= e.key_candidates("foo.message"))
        self.assertTrue({"a.b_one", "a.b", "a|b", "a|b_one"} <= e.key_candidates("a.b_one"))
        self.assertEqual(e.key_candidates("Upload_file"), {"Upload_file"})

    def test_used(self):
        self.assertTrue(e.used("foo.message", {"foo"}))
        self.assertTrue(e.used("Upload_file", {"Upload_file", "x"}))
        self.assertFalse(e.used("Upload_file", {"upload_file"}))


class ReadTest(unittest.TestCase):
    def test_read_project(self):
        members = [("kuma-abc/src/lang/en.json", b'{"a": "Mute"}'),
                   ("kuma-abc/src/lang/fr.json", b'{"a": "Muet"}'),
                   ("kuma-abc/src/app.js", b"$t('a'); x(\"Upload_file\")"),
                   ("kuma-abc/node_modules/m/i.js", b"'hidden'")]
        files, found, commit = e.read_project(P["uptime-kuma"], tarball(members, "abc123"))
        self.assertEqual(sorted(files), ["en", "fr"])
        self.assertEqual(files["fr"], b'{"a": "Muet"}')
        self.assertIn("a", found)
        self.assertIn("Upload_file", found)
        self.assertNotIn("hidden", found)
        self.assertEqual(commit, "abc123")


class SampleTest(unittest.TestCase):
    def rows(self, n):
        return [{"project": "p%d" % (i % 3), "locale": "l%02d" % i, "key1": "k", "key2": "j"} for i in range(n)]

    def test_small_is_all_sorted(self):
        rows = self.rows(10)
        out = e.sample(list(reversed(rows)), 60, 1)
        self.assertEqual(len(out), 10)
        self.assertEqual(out, sorted(rows, key=lambda r: (r["project"], r["locale"])))

    def test_large_is_seeded(self):
        rows = self.rows(100)
        a, b = e.sample(rows, 60, e.SEED_MAIN), e.sample(list(reversed(rows)), 60, e.SEED_MAIN)
        self.assertEqual(len(a), 60)
        self.assertEqual(a, b)
        self.assertNotEqual(a, e.sample(rows, 60, e.SEED_UPLOAD))

    def test_classes(self):
        self.assertTrue(e.is_upload({"classes": "UPLOAD"}))
        self.assertFalse(e.is_upload({"classes": "SHOW+UPLOAD"}))
        self.assertTrue(e.french_or_arabic({"locale": "fr-CA"}))
        self.assertTrue(e.french_or_arabic({"locale": "ar_SA"}))
        self.assertFalse(e.french_or_arabic({"locale": "fa"}))


@unittest.skipUnless(os.path.exists(GUARD_PATH), "released guard not fetched")
class GuardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = e.load_guard(GUARD_PATH)

    def test_version(self):
        self.assertEqual(self.g.__version__, e.GUARD_VERSION)

    def test_flip_classes(self):
        self.assertEqual(e.flip_classes(self.g, "Upload failed", "Download failed"), "UPLOAD")
        self.assertEqual(e.flip_classes(self.g, "Collapse", "Expand"), "EXPAND")
        self.assertEqual(e.flip_classes(self.g, "Unmute", "Mute"), "MUTE")

    def test_scan(self):
        en = {"a": "Upload failed", "b": "Download failed", "c": "Mute", "d": "Unmute", "e": "Show", "f": "Hide"}
        fr = {"a": "Échec du téléchargement", "b": "Échec du téléchargement", "c": "Muet", "d": "Muet",
              "e": "Afficher", "f": "Masquer"}
        files = {"en": json.dumps(en).encode("utf-8"), "fr": json.dumps(fr, ensure_ascii=False).encode("utf-8"),
                 "en_GB": b"{}", "de": b"not json"}
        res = e.scan(self.g, P["uptime-kuma"], files)
        self.assertEqual(res["reference"], "en")
        self.assertEqual(res["locale_files"], 1)
        self.assertEqual(res["unparsed"], ["de"])
        self.assertEqual(res["pairs"], 3)
        self.assertEqual(res["comparisons"], 3)
        self.assertTrue(res["consistent"])
        got = sorted((r["key1"], r["key2"], r["classes"], r["value"]) for r in res["rows"])
        self.assertEqual(got, [("a", "b", "UPLOAD", "Échec du téléchargement"), ("c", "d", "MUTE", "Muet")])


if __name__ == "__main__":
    unittest.main()
