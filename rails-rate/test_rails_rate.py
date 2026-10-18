#!/usr/bin/env python3
"""Offline tests for rails_rate.py.

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import os
import shutil
import tempfile
import unittest

import rails_rate as rr

GITMODULES = ('[submodule "apps/lobsters"]\n\tpath = apps/lobsters\n'
              '\turl = git@github.com:jcs/lobsters.git\n'
              '[submodule "apps/chatwoot"]\n\tpath = apps/chatwoot\n'
              '\turl = https://github.com/chatwoot/chatwoot\n\tignore = dirty\n'
              '[submodule "apps/worldcubeassociation.org"]\n'
              '\tpath = apps/worldcubeassociation.org\n'
              '\turl = git@github.com:thewca/worldcubeassociation.org.git\n')
LOCALES = {
    "en.yml": 'en:\n  hello: "Hello %{name}"\n  items:\n    one: "1 item"\n'
              '    other: "%{count} items"\n',
    "ja.yml": 'ja:\n  hello: "こんにちは ％{name}"\n  items:\n    other: "%{count}件"\n',
    "broken.yml": "en:\n\tbad: x\n",
    "defaults.yml": "defaults:\n  x: 1\n",
    "notes.txt": "not yaml",
    os.path.join("sub", "devise.ru.yml"): 'ru:\n  items:\n    few: "%{count} штуки"\n'
                                          '    many: "штук"\n',
}


class PopulationTest(unittest.TestCase):
    def test_https_url(self):
        self.assertEqual(rr.https_url("git@github.com:jcs/lobsters.git"),
                         "https://github.com/jcs/lobsters")
        self.assertEqual(rr.https_url("https://github.com/chatwoot/chatwoot"),
                         "https://github.com/chatwoot/chatwoot")
        self.assertEqual(rr.https_url("git@github.com:thewca/worldcubeassociation.org.git"),
                         "https://github.com/thewca/worldcubeassociation.org")

    def test_parse_gitmodules(self):
        self.assertEqual(rr.parse_gitmodules(GITMODULES), {
            "apps/lobsters": "https://github.com/jcs/lobsters",
            "apps/chatwoot": "https://github.com/chatwoot/chatwoot",
            "apps/worldcubeassociation.org": "https://github.com/thewca/worldcubeassociation.org"})

    def test_parse_ls_tree(self):
        text = ("160000 commit 0123abc\tapps/lobsters\n100644 blob 4567def\tREADME.md\n"
                "040000 tree 89abcde\tbin\n")
        self.assertEqual(rr.parse_ls_tree(text), {"apps/lobsters": "0123abc"})

    def test_analyse_without_url(self):
        record, files, stats, rows = rr.analyse(
            {"path": "apps/x", "url": "", "commit": "abc"},
            os.path.join(tempfile.gettempdir(), "rails-rate-test-none"), 10)
        self.assertEqual(record["fetched"], 0)
        self.assertIn("no url", record["error"])
        self.assertEqual((files, stats, rows), ([], [], []))


class RulesTest(unittest.TestCase):
    def test_names_ascii_only(self):
        self.assertEqual(rr.names("%{名前} %{count} %%{x} %<n>d 100%%"), {"count", "n"})

    def test_language(self):
        self.assertEqual(rr.language("zh-CN"), "zh")
        self.assertEqual(rr.language("pt_BR"), "pt")
        self.assertTrue(rr.in_group("zh-TW"))
        self.assertTrue(rr.in_group("ckb"))
        self.assertFalse(rr.in_group("ku"))
        self.assertFalse(rr.in_group("ru"))

    def test_kinds(self):
        cases = [("date", "on %{date}", "el % {date}", ("spaced", "% {date}")),
                 ("date", "on %{date}", "el %{ date }", ("spaced", "%{ date }")),
                 ("issue_link", "see %{issue_link}", "veja #{issue_link}",
                  ("ruby-hash", "#{issue_link}")),
                 ("name", "Hi %{name}", "Hola {name}", ("no-percent", "{name}")),
                 ("name", "Hi %{name}", "Hola ${name}", ("other-syntax", "${name}")),
                 ("name", "Hi %{name}", "Hola %{nombre}", ("renamed", "%{nombre}")),
                 ("name", "Hi %{name}", "Hola %{名前}", ("renamed", "%{名前}")),
                 ("name", "Hi %{name}", "Hola", ("dropped", "")),
                 ("count", "%{count} items", "%｛count｝件", ("lookalike-brace", "%｛count｝")),
                 ("count", "%{count} items", "٪ {count} عناصر", ("lookalike-percent", "٪ {count}"))]
        for name, source, target, want in cases:
            self.assertEqual(rr.kind(name, source, target), want, target)

    def test_lookalike_error(self):
        self.assertEqual(rr.check_pair("%{count} items", "％{count}件", "other"), [
            {"level": "error", "code": "lookalike-percent", "kind": "lookalike-percent",
             "name": "count", "seen": "％{count}"}])

    def test_lookalike_warning_when_ascii_present(self):
        problems = rr.check_pair("%{n} x", "%{n} ％{n}")
        self.assertEqual([(p["level"], p["code"]) for p in problems],
                         [("warning", "lookalike-percent")])

    def test_plural_one_may_drop(self):
        problems = rr.check_pair("%{count} items", "один", "one")
        self.assertEqual([(p["level"], p["code"], p["kind"]) for p in problems],
                         [("warning", "placeholder-missing", "dropped")])
        problems = rr.check_pair("%{count} items", "штук", "many")
        self.assertEqual([(p["level"], p["code"]) for p in problems],
                         [("error", "placeholder-missing")])

    def test_extra(self):
        self.assertEqual(rr.check_pair("1 item", "%{count} 件", "one"), [])
        self.assertEqual([(p["level"], p["code"], p["name"])
                          for p in rr.check_pair("Saved", "%{name} を保存")],
                         [("warning", "placeholder-extra", "name")])

    def test_empty(self):
        self.assertEqual(rr.check_pair("Hi %{name}", "  "), [])

    def test_pairs(self):
        src = {"a": "x", "b.other": "%{count}", "b.one": "1", "d": ["list"]}
        tgt = {"a": "y", "b.few": "%{count}", "c": "z", "d": ["liste"]}
        self.assertEqual(rr.pairs(src, tgt), [("a", "x", "y", None),
                                              ("b.few", "%{count}", "%{count}", "few")])

    def test_fisher(self):
        self.assertAlmostEqual(rr.fisher_greater(3, 97, 0, 100), 970200 / 7880400, places=6)
        self.assertEqual(rr.fisher_greater(0, 10, 0, 10), 1.0)
        self.assertAlmostEqual(rr.fisher_greater(0, 10, 3, 7), 1.0, places=9)


class LocalesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        for name, text in LOCALES.items():
            path = os.path.join(self.root, "config", "locales", name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(text)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def test_load_and_compare(self):
        merged, files, collisions = rr.load_locales(self.root, "apps/x")
        self.assertEqual([f["file"] for f in files], [
            "config/locales/broken.yml", "config/locales/defaults.yml", "config/locales/en.yml",
            "config/locales/ja.yml", "config/locales/sub/devise.ru.yml"])
        self.assertEqual([f["loaded"] for f in files], [0, 1, 1, 1, 1])
        self.assertTrue(files[0]["error"])
        self.assertEqual(files[1]["locales"], "")
        self.assertEqual(sorted(merged), ["en", "ja", "ru"])
        self.assertEqual(collisions, 0)

        ja, ja_rows = rr.locale_stats("apps/x", "abc", "ja", merged["en"], merged["ja"])
        self.assertEqual((ja["strings"], ja["placeholder_strings"], ja["error_strings"],
                          ja["lookalike_errors"], ja["lookalike_error_strings"], ja["group"]),
                         (2, 2, 1, 1, 1, 1))
        self.assertEqual([(r["key"], r["code"], r["seen"]) for r in ja_rows],
                         [("hello", "lookalike-percent", "％{name}")])

        ru, ru_rows = rr.locale_stats("apps/x", "abc", "ru", merged["en"], merged["ru"])
        self.assertEqual((ru["strings"], ru["missing_errors"], ru["group"]), (2, 1, 0))
        self.assertEqual([(r["key"], r["quantity"], r["kind"]) for r in ru_rows],
                         [("items.many", "many", "dropped")])

        checks = rr.predictions([{"fetched": 1}], files, [ja, ru], ja_rows + ru_rows)
        self.assertEqual([c[0] for c in checks], ["P1", "P2", "P3", "P4", "P5", "P6", "P7"])
        held = {c[0]: c[2] for c in checks}
        self.assertFalse(held["P1"])   # 1 of 2 locales
        self.assertTrue(held["P2"])
        self.assertTrue(held["P3"])    # 1 of 2 vs 0 of 1
        self.assertFalse(held["P4"])   # 1 vs 1
        self.assertFalse(held["P5"])   # 4 of 5
        self.assertFalse(held["P6"])
        self.assertFalse(held["P7"])   # dropped 1, lookalike-percent 1


if __name__ == "__main__":
    unittest.main()
