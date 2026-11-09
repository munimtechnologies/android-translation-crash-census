# Tests for lproj_census.py (ios-lproj census). Made with AI agents by MV2 of Munim, Inc.
# Licence: Apache-2.0.
import json
import os
import shutil
import subprocess
import tempfile
import unittest

import lproj_census as c

EN = ('"a" = "Open";\n"b" = "Close";\n"c" = "Save";\n"d" = "OK";\n"e" = "Cancel";\n'
      '"f" = "Delete";\n').encode("utf-8")
CZ = ('"a" = "Otevřít";\n"b" = "Zavřít";\n"c" = "Uložit";\n"d" = "OK";\n"e" = "Zrušit";\n'
      '"f" = "Smazat";\n').encode("utf-8")


def folder(folders, name):
    return next(f for f in folders if f["name"] == name)


class Names(unittest.TestCase):
    def test_primary(self):
        self.assertEqual(c.lproj_primary("pt-BR"), "pt")
        self.assertEqual(c.lproj_primary("zh_CN"), "zh")
        self.assertEqual(c.lproj_primary("zh-Hans"), "zh")
        self.assertEqual(c.lproj_primary("sr-Latn-RS"), "sr")
        self.assertEqual(c.lproj_primary("es-419"), "es")
        self.assertEqual(c.lproj_primary("English"), "en")
        self.assertEqual(c.lproj_primary("Base"), "base")
        self.assertEqual(c.lproj_primary("cz"), "cz")
        self.assertEqual(c.lproj_primary("CN"), "cn")
        self.assertIsNone(c.lproj_primary("Localizable"))

    def test_vendored(self):
        self.assertTrue(c.is_vendored("Pods/MJRefresh/MJRefresh.bundle/en.lproj"))
        self.assertTrue(c.is_vendored("Carthage/Checkouts/x/cn.lproj"))
        self.assertTrue(c.is_vendored("Frameworks/Foo.framework/cn.lproj"))
        self.assertFalse(c.is_vendored("App/Resources/cz.lproj"))

    def test_classify_and_summarize(self):
        paths = ["App/en.lproj/Localizable.strings", "App/cz.lproj/Localizable.strings",
                 "App/cz.lproj/Main.strings", "App/Base.lproj/Main.storyboard",
                 "Pods/Lib/Lib.bundle/cn.lproj/Lib.strings", "README.md",
                 "App/kr.lproj/Localizable.strings", "Settings.bundle/de.lproj/Root.strings"]
        folders = c.classify(paths)
        self.assertEqual([f["folder"] for f in folders],
                         ["App/Base.lproj", "App/cz.lproj", "App/en.lproj", "App/kr.lproj",
                          "Pods/Lib/Lib.bundle/cn.lproj", "Settings.bundle/de.lproj"])
        self.assertEqual([f["kind"] for f in folders],
                         ["", "country", "", "suspect", "country", ""])
        self.assertEqual(folder(folders, "cz")["files"],
                         ["App/cz.lproj/Localizable.strings", "App/cz.lproj/Main.strings"])
        langs, flagged = c.summarize(folders)
        self.assertEqual(langs, ["cz", "de", "en", "kr"])
        self.assertEqual([f["name"] for f in flagged], ["cz"])
        self.assertEqual(flagged[0]["fix"], "cs")
        self.assertFalse(flagged[0]["correct_present"])
        self.assertEqual(folder(folders, "kr")["fix"], "ko")
        vend = folder(folders, "cn")
        self.assertTrue(vend["vendored"])
        self.assertNotIn("fix", vend)
        self.assertTrue(c.translated(langs))
        self.assertFalse(c.translated(["en"]))
        self.assertFalse(c.translated([]))

    def test_hebrew_alias(self):
        folders = c.classify(["a/il.lproj/x.strings", "a/iw.lproj/x.strings"])
        _, flagged = c.summarize(folders)
        self.assertEqual(flagged[0]["fix"], "he")
        self.assertTrue(flagged[0]["correct_present"])


class Contents(unittest.TestCase):
    def test_parse_strings_utf16(self):
        text = ('/* comment "x" = "y"; */\n"hello" = "Привет";\n// line "a" = "b";\n'
                '"url" = "see https://example.com";\n"q" = "say \\"hi\\"";\n')
        self.assertEqual(c.parse_strings(text.encode("utf-16")),
                         {"hello": "Привет", "url": "see https://example.com",
                          "q": 'say \\"hi\\"'})

    def test_parse_strings_encodings(self):
        self.assertEqual(c.parse_strings(b'\xef\xbb\xbf"k" = "v";'), {"k": "v"})
        self.assertEqual(c.parse_strings('"k" = "v";'.encode("utf-16-le")), {"k": "v"})
        self.assertEqual(c.parse_strings(b"not a strings file"), {})

    def test_scripts(self):
        self.assertEqual(c.scripts_of("Привет"), {"Cyrillic"})
        self.assertEqual(c.scripts_of("設定"), {"Han"})
        self.assertEqual(c.scripts_of("せってい"), {"Kana"})
        self.assertEqual(c.scripts_of("ｱ"), {"Kana"})
        self.assertEqual(c.scripts_of("설정"), {"Hangul"})
        self.assertEqual(c.scripts_of("Hello 123"), {"Latin"})
        self.assertEqual(c.scripts_of("%@ 1"), set())

    def test_content_against_reference(self):
        files = {"App/en.lproj/Localizable.strings": EN, "App/cz.lproj/Localizable.strings": CZ}
        folders = c.classify(sorted(files))
        got = c.folder_content(folder(folders, "cz"), files.get, folders)
        self.assertEqual(got["ref_folder"], "App/en.lproj")
        self.assertEqual((got["strings_files"], got["values"], got["shared_keys"],
                          got["differing"]), (1, 6, 6, 5))
        self.assertEqual(got["holds_translation"], "yes")

    def test_english_copy(self):
        files = {"App/en.lproj/Localizable.strings": EN, "App/ua.lproj/Localizable.strings": EN}
        folders = c.classify(sorted(files))
        got = c.folder_content(folder(folders, "ua"), files.get, folders)
        self.assertEqual((got["shared_keys"], got["differing"]), (6, 0))
        self.assertEqual(got["holds_translation"], "no")

    def test_script_fallback(self):
        jp = '"1" = "設定";"2" = "閉じる";"3" = "保存";"4" = "削除";"5" = "キャンセル";'
        files = {"X/jp.lproj/Main.strings": jp.encode("utf-8")}
        folders = c.classify(sorted(files))
        got = c.folder_content(folder(folders, "jp"), files.get, folders)
        self.assertEqual(got["ref_folder"], "")
        self.assertEqual((got["with_letters"], got["expected_script"]), (5, 5))
        self.assertEqual(got["holds_translation"], "yes")

    def test_unknown(self):
        files = {"X/cz.lproj/Main.strings": b'"1" = "Ano"; "2" = "Ne"; "3" = "Zrušit";'}
        folders = c.classify(sorted(files))
        got = c.folder_content(folder(folders, "cz"), files.get, folders)
        self.assertEqual(got["holds_translation"], "unknown")

    def test_pbx_info(self):
        pbx = ['knownRegions = (\n\ten,\n\tBase,\n\tcz,\n\t"zh-Hans",\n);\n'
               'path = cz.lproj/Localizable.strings;']
        self.assertEqual(c.pbx_info("cz", pbx), ("yes", "yes"))
        self.assertEqual(c.pbx_info("zh-Hans", pbx), ("no", "yes"))
        self.assertEqual(c.pbx_info("ua", pbx), ("no", "no"))
        self.assertEqual(c.pbx_info("cz", []), ("no pbxproj", "no pbxproj"))

    def test_code_mentions(self):
        code = [("A.swift", 'Bundle.main.path(forResource: "cz", ofType: "lproj")'),
                ("B.m", '@"czech"'), ("C.swift", 'let p = "cz.lproj"')]
        self.assertEqual(c.code_mentions("cz", code), ["A.swift", "C.swift"])

    def test_xcstrings(self):
        doc = {"sourceLanguage": "en", "strings": {
            "Hi": {"localizations": {"de": {}, "cz": {}}}, "Bye": {},
            "X": {"localizations": {"ua": {}}}}}
        self.assertEqual(c.xcstrings_languages(json.dumps(doc).encode("utf-8")),
                         ["cz", "de", "ua"])
        self.assertIsNone(c.xcstrings_languages(b"not json"))
        self.assertIsNone(c.xcstrings_languages(b'{"a": 1}'))


class Population(unittest.TestCase):
    def test_population(self):
        doc = {"projects": [{"source": "https://github.com/Foo/Bar"},
                            {"source": "https://github.com/foo/bar/"},
                            {"source": "https://github.com/a/b.git"},
                            {"source": "https://gitlab.com/x/y"},
                            {"source": "https://github.com/c/d/tree/master/app"},
                            {"title": "no source"}, "junk"]}
        self.assertEqual(c.population(doc), ["https://github.com/a/b", "https://github.com/c/d",
                                             "https://github.com/Foo/Bar"])


def repo(i, langs, folders=()):
    return {"repo": "https://github.com/o/r%d" % i, "status": "ok", "commit": "c%d" % i,
            "languages": langs, "folders": list(folders), "names": [], "xcstrings": []}


def cf(name, present, holds, vendored=False):
    return {"folder": "App/%s.lproj" % name, "name": name, "primary": name, "kind": "country",
            "vendored": vendored, "correct_present": present, "holds_translation": holds}


class Grading(unittest.TestCase):
    def results(self):
        rs = [repo(i, ["de", "en"]) for i in range(296)]
        rs += [repo(1000 + i, ["en"]) for i in range(700)]
        rs.append(repo(2001, ["cz", "en"], [cf("cz", False, "yes")]))
        rs.append(repo(2002, ["cn", "en"], [cf("cn", False, "yes")]))
        rs.append(repo(2003, ["cn", "en", "zh"], [cf("cn", True, "no")]))
        rs.append(repo(2004, ["en", "ua"], [cf("ua", False, "unknown"),
                                            cf("jp", None, None, vendored=True)]))
        rs += [dict(repo(3000 + i, []), status="error: x") for i in range(5)]
        return rs

    def test_grade(self):
        v, counts, flagged = c.grade(self.results())
        self.assertEqual(v["G"], "PASSED")
        self.assertEqual(v["P1"], "HELD")
        self.assertEqual(v["P2"], "HELD")
        self.assertEqual(v["P3"], "HELD")
        self.assertEqual(v["P4"], "NOT TESTABLE (3 folders with known content)")
        self.assertEqual((counts["read"], counts["translated"], counts["flagged_repos"],
                          counts["unreachable_repos"], counts["flagged_folders"]),
                         (1000, 300, 4, 3, 4))
        self.assertEqual(counts["folders_by_code"], {"cn": 2, "cz": 1, "ua": 1})
        self.assertEqual(counts["flagged_share_pct"], 1.33)
        rows = c.sample_rows(flagged)
        self.assertEqual(sorted(r["sample"] for r in rows), [1, 2, 3, 4])
        self.assertEqual({r["repo"] for r in rows}, {r["repo"] for r in flagged})
        ex = c.exploratory(self.results())
        self.assertEqual((ex["vendored_country_folders"], ex["vendored_country_repos"]), (1, 1))
        self.assertEqual(ex["vendored_codes"], {"jp": 1})

    def test_gate(self):
        v, _, _ = c.grade([repo(i, ["de", "en"]) for i in range(10)])
        self.assertEqual(v["G"], "FAILED (10 read, 10 with translations)")
        self.assertEqual(v["P1"], "NOT TESTABLE (gate)")

    def test_p1_too_high(self):
        rs = [repo(i, ["de", "en"]) for i in range(280)]
        rs += [repo(500 + i, ["cz", "en"], [cf("cz", False, "yes")]) for i in range(20)]
        rs += [repo(1000 + i, ["en"]) for i in range(700)]
        v, counts, _ = c.grade(rs)
        self.assertEqual(counts["flagged_repos"], 20)
        self.assertEqual(v["P1"], "FAILED")
        self.assertEqual(v["P4"], "HELD")


class EndToEnd(unittest.TestCase):
    ENV = {"GIT_CONFIG_COUNT": "1", "GIT_CONFIG_KEY_0": "protocol.file.allow",
           "GIT_CONFIG_VALUE_0": "always"}

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.saved = {k: os.environ.get(k) for k in self.ENV}
        os.environ.update(self.ENV)

    def tearDown(self):
        for k, val in self.saved.items():
            if val is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = val
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_analyse_local_repo(self):
        if shutil.which("git") is None:
            self.skipTest("git not installed")
        src = os.path.join(self.tmp, "src")
        catalog = {"sourceLanguage": "en", "strings": {
            "Hi": {"localizations": {"de": {}, "cz": {}}}}}
        files = {
            "App/en.lproj/Localizable.strings": EN,
            "App/cz.lproj/Localizable.strings": CZ,
            "App/Base.lproj/Main.storyboard": b"<document/>",
            "App/App.xcodeproj/project.pbxproj": (b"knownRegions = (\n en,\n Base,\n cz,\n);\n"
                                                  b"path = cz.lproj/Localizable.strings;\n"),
            "App/Lang.swift": b'let code = "cz"\n',
            "Pods/X/X.bundle/cn.lproj/X.strings": b'"a" = "b";\n',
            "App/Local.xcstrings": json.dumps(catalog).encode("utf-8"),
            "README.md": b"hi\n",
        }
        for p, data in files.items():
            fp = os.path.join(src, *p.split("/"))
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "wb") as fh:
                fh.write(data)

        def run(*args):
            subprocess.run(["git", "-C", src] + list(args), check=True, capture_output=True)

        subprocess.run(["git", "init", "--quiet", src], check=True, capture_output=True)
        run("config", "uploadpack.allowFilter", "true")
        run("config", "uploadpack.allowAnySHA1InWant", "true")
        run("add", "-A")
        run("-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "--quiet", "-m", "x")
        work = os.path.join(self.tmp, "work")
        os.makedirs(work)
        r = c.analyse("file://" + src, work)
        self.assertEqual(r["status"], "ok", r["status"])
        self.assertEqual(r["n_paths"], 8)
        self.assertEqual(r["n_lproj"], 4)
        self.assertEqual(r["languages"], ["cz", "en"])
        self.assertEqual(r["names"], ["Base", "cz", "en"])
        self.assertEqual([f["name"] for f in r["folders"]], ["cz", "cn"])
        cz = r["folders"][0]
        self.assertNotIn("files", cz)
        self.assertEqual(cz["n_files"], 1)
        self.assertFalse(cz["correct_present"])
        self.assertEqual(cz["holds_translation"], "yes")
        self.assertEqual((cz["in_pbxproj"], cz["known_region"]), ("yes", "yes"))
        self.assertEqual(cz["code_mentions"], ["App/Lang.swift"])
        self.assertTrue(r["folders"][1]["vendored"])
        self.assertEqual(r["xcstrings"], [{"file": "App/Local.xcstrings",
                                           "languages": ["cz", "de"]}])
        json.dumps(r, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
