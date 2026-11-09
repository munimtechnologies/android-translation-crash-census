# Tests for linguas_census.py (linguas census). Made with AI agents by MV2 of Munim, Inc.
# Licence: Apache-2.0.
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

import linguas_census as c

PO = '''# German translation.
msgid ""
msgstr ""
"Content-Type: text/plain; charset=UTF-8\\n"

#: src/a.c:1
msgid "Open"
msgstr "Öffnen"

#, fuzzy, c-format
msgid "Close"
msgstr "Schließen"

msgid "Save"
msgstr ""

msgctxt "menu"
msgid "Quit"
msgstr ""
"Beenden"

msgid "One file"
msgid_plural "%d files"
msgstr[0] ""
msgstr[1] "%d Dateien"

#~ msgid "Old"
#~ msgstr "Alt"
'''.encode("utf-8")

STUB = b'msgid ""\nmsgstr ""\n"Language: fr\\n"\n\nmsgid "Open"\nmsgstr ""\n\nmsgid "Close"\nmsgstr ""\n'


class Population(unittest.TestCase):
    def test_repo_url(self):
        u = c.repo_url
        self.assertEqual(u("https://github.com/GNOME/foo"), "https://github.com/GNOME/foo")
        self.assertEqual(u("https://github.com/owner/repo/tree/main/src"),
                         "https://github.com/owner/repo")
        self.assertEqual(u("https://www.github.com/Owner/Repo.git/"),
                         "https://github.com/Owner/Repo")
        self.assertEqual(u("https://gitlab.gnome.org/World/fractal"),
                         "https://gitlab.gnome.org/World/fractal")
        self.assertEqual(u("https://gitlab.gnome.org/World/Rust/thing/-/tree/main"),
                         "https://gitlab.gnome.org/World/Rust/thing")
        self.assertEqual(u("https://gitlab.com/group/proj/tree/master"),
                         "https://gitlab.com/group/proj")
        self.assertEqual(u("https://git.sr.ht/~user/repo/tree"), "https://git.sr.ht/~user/repo")
        self.assertEqual(u(" https://codeberg.org/a/b "), "https://codeberg.org/a/b")
        self.assertIsNone(u("https://github.com/owner"))
        self.assertIsNone(u("https://gitlab.com/onlygroup/-/tree/x"))
        self.assertIsNone(u("https://example.org/app"))
        self.assertIsNone(u("ftp://github.com/a/b"))
        self.assertIsNone(u(None))
        self.assertIsNone(u(""))

    def test_app_repo_and_group(self):
        self.assertEqual(c.app_repo({"urls": {"vcs_browser": None,
                                              "homepage": "https://github.com/a/b"}}),
                         ("https://github.com/a/b", "homepage"))
        self.assertEqual(c.app_repo({"urls": {"vcs_browser": "https://gitlab.gnome.org/World/x",
                                              "homepage": "https://github.com/a/b"}}),
                         ("https://gitlab.gnome.org/World/x", "vcs_browser"))
        self.assertEqual(c.app_repo({"urls": {"homepage": "https://a.org"}}), (None, ""))
        self.assertEqual(c.app_repo({}), (None, ""))
        self.assertEqual(c.app_repo({"urls": None}), (None, ""))
        g = c.translate_group
        self.assertEqual(g({"urls": {"translate": "https://l10n.gnome.org/module/fractal/"}}),
                         "gnome")
        self.assertEqual(g({"urls": {"translate": "https://hosted.weblate.org/projects/x/"}}),
                         "weblate")
        self.assertEqual(g({"urls": {"translate": "https://crowdin.com/project/x"}}), "crowdin")
        self.assertEqual(g({"urls": {"translate": "https://example.org/help"}}), "other")
        self.assertEqual(g({"urls": {"translate": None}}), "none")
        self.assertEqual(g({}), "none")

    def test_population(self):
        apps = {
            "b.App": {"urls": {"vcs_browser": "https://github.com/O/R",
                               "translate": "https://hosted.weblate.org/x"}},
            "a.App": {"urls": {"homepage": "https://github.com/o/r"}},
            "c.App": None,
            "d.App": {"urls": {"homepage": "https://d.org/x"}},
            "e.App": {"urls": {"vcs_browser": "https://gitlab.gnome.org/GNOME/e",
                               "translate": "https://l10n.gnome.org/module/e/"}},
        }
        repos, stats = c.population(apps)
        self.assertEqual(repos, [
            {"repo": "https://github.com/o/r", "apps": ["a.App", "b.App"], "source": "homepage",
             "group": "weblate"},
            {"repo": "https://gitlab.gnome.org/GNOME/e", "apps": ["e.App"],
             "source": "vcs_browser", "group": "gnome"}])
        self.assertEqual((stats["apps_listed"], stats["apps_fetched"], stats["apps_with_repo"]),
                         (5, 4, 3))
        self.assertEqual(stats["by_source"], {"homepage": 1, "vcs_browser": 2})
        self.assertEqual(stats["unrecognised_hosts"], {"d.org": 1})


class Files(unittest.TestCase):
    def test_language_like(self):
        for s in ("de", "pt_BR", "sr@latin", "zh_Hans", "es_419", "ca@valencia", "ckb", "pt-BR"):
            self.assertTrue(c.language_like(s), s)
        for s in ("en@quot", "en@boldquot", "messages", "x", "de.utf8"):
            self.assertFalse(c.language_like(s), s)

    def test_vendored(self):
        self.assertTrue(c.is_vendored("subprojects/lib/po"))
        self.assertTrue(c.is_vendored("third_party/x/po"))
        self.assertFalse(c.is_vendored("po"))
        self.assertFalse(c.is_vendored(""))

    def test_po_dirs(self):
        paths = ["po/LINGUAS", "po/de.po", "po/fr.po", "po/app.pot", "po/meson.build",
                 "help/LINGUAS", "help/de/de.po", "subprojects/lib/po/LINGUAS",
                 "subprojects/lib/po/de.po", "LINGUAS", "README.md", "x/LINGUAS", "x/.po"]
        self.assertEqual(c.po_dirs(paths), {"po": {"de": "po/de.po", "fr": "po/fr.po"}})
        self.assertEqual(c.po_dirs(["LINGUAS", "it.po"]), {"": {"it": "it.po"}})

    def test_linguas_parsers(self):
        text = "# comment\nde fr  # French\n\n  pt_BR\n"
        self.assertEqual(c.gnu_linguas(text), ["de", "fr", "pt_BR"])
        self.assertEqual(c.meson_linguas(text), ["de", "fr", "#", "French", "pt_BR"])

    def test_configure_paths(self):
        self.assertEqual(c.configure_paths("po", {"configure.ac", "po/LINGUAS"}),
                         ["configure.ac"])
        self.assertEqual(c.configure_paths("sub/po", {"sub/configure.in", "configure.ac"}),
                         ["sub/configure.in", "configure.ac"])
        self.assertEqual(c.configure_paths("po", set()), [])

    def test_build_kind(self):
        b = c.build_kind
        self.assertEqual(b("i18n.gettext(meson.project_name(),\n  preset: 'glib'\n)\n", []),
                         "meson")
        self.assertEqual(b("i18n.gettext('app', languages: ['de'])", []), "meson-explicit")
        self.assertEqual(b(None, ["AC_INIT([x])\nAM_GNU_GETTEXT([external])\n"]), "autotools")
        self.assertEqual(b(None, ["IT_PROG_INTLTOOL([0.35.0])"]), "autotools")
        self.assertEqual(b("install_data('x')", ["AC_INIT([x])"]), "other")
        self.assertEqual(b("x = ngettext('a')", []), "other")
        self.assertEqual(b(None, []), "other")

    def test_compare(self):
        po = {"de": "po/de.po", "fr": "po/fr.po", "pt-BR": "po/pt-BR.po",
              "en@quot": "po/en@quot.po", "it": "po/it.po"}
        self.assertEqual(c.compare(po, ["de", "pt_BR", "es", "de"]),
                         (["fr", "it", "pt-BR"], ["es", "pt_BR"], ["pt-BR"]))
        self.assertEqual(c.compare({"de": "po/de.po"}, ["de"]), ([], [], []))

    def test_po_stats(self):
        st = c.po_stats(PO)
        self.assertEqual(st, {"entries": 5, "translated": 3, "fuzzy": 1})
        self.assertEqual(c.substantive(st), "yes")
        stub = c.po_stats(STUB)
        self.assertEqual(stub, {"entries": 2, "translated": 0, "fuzzy": 0})
        self.assertEqual(c.substantive(stub), "no")
        self.assertEqual(c.substantive(c.po_stats(b"")), "unknown")
        self.assertEqual(c.substantive(None), "unknown")
        crlf = b'\xef\xbb\xbfmsgid "A"\r\nmsgstr "B"\r\nmsgid "C"\r\nmsgstr ""\r\n'
        self.assertEqual(c.po_stats(crlf), {"entries": 2, "translated": 1, "fuzzy": 0})


def res(i, group, dirs, status="ok"):
    return {"repo": "https://github.com/o/r%d" % i, "group": group, "status": status,
            "commit": "c%d" % i, "apps": [], "dirs": list(dirs)}


def dr(build, dropped=(), phantom=(), subs=()):
    files = [{"stem": s, "path": "po/%s.po" % s, "entries": 10,
              "translated": 8 if sub == "yes" else 1 if sub == "no" else None,
              "fuzzy": 0, "substantive": sub} for s, sub in zip(dropped, subs)]
    return {"dir": "po", "build": build, "n_po": 3, "linguas_read": True, "n_listed": 3,
            "dropped": list(dropped), "phantom": list(phantom), "variants": [], "files": files}


class Grading(unittest.TestCase):
    def results(self):
        rs = [res(1, "gnome", [dr("meson", ["fr"], subs=["yes"])])]
        rs += [res(2 + i, "gnome", [dr("meson")]) for i in range(19)]
        rs += [res(100, "weblate", [dr("meson", ["it"], subs=["yes"])]),
               res(101, "weblate", [dr("autotools", ["es"], subs=["yes"])]),
               res(102, "none", [dr("meson", ["pl"], subs=["no"])]),
               res(103, "none", [dr("meson", ["uk"], subs=["unknown"])]),
               res(104, "weblate", [dr("meson", phantom=["xx"])])]
        rs += [res(200 + i, "none", [dr("meson")]) for i in range(15)]
        rs += [res(300 + i, "none", [dr("other", ["de"])]) for i in range(5)]
        rs += [res(400 + i, "none", []) for i in range(10)]
        rs += [res(500 + i, "none", [], status="error: x") for i in range(2)]
        return rs

    def test_grade(self):
        with mock.patch.object(c, "GATE_READ", 50), mock.patch.object(c, "GATE_GOVERNED", 40):
            v, counts, flagged = c.grade(self.results())
        self.assertEqual(v, {"G": "PASSED", "P1": "HELD", "P2": "HELD", "P3": "HELD",
                             "P4": "HELD"})
        self.assertEqual((counts["read"], counts["governed_repos"], counts["flagged_repos"]),
                         (55, 40, 5))
        self.assertEqual(counts["flagged_share_pct"], 12.5)
        self.assertEqual(counts["governed_by_build"], {"meson": 39, "autotools": 1})
        self.assertEqual((counts["dropped_files"], counts["content_known"],
                          counts["content_substantive"]), (5, 4, 3))
        self.assertEqual(counts["dropped_translated_messages"], 8 + 8 + 8 + 1)
        self.assertEqual((counts["gnome_governed"], counts["gnome_flagged"],
                          counts["other_governed"], counts["other_flagged"]), (20, 1, 20, 4))
        self.assertEqual((counts["meson_dropped_repos"], counts["meson_phantom_repos"]), (4, 1))
        rows = c.sample_rows(flagged)
        self.assertEqual(sorted(r["sample"] for r in rows), [1, 2, 3, 4, 5])
        self.assertEqual({r["po_file"] for r in rows},
                         {"po/fr.po", "po/it.po", "po/es.po", "po/pl.po", "po/uk.po"})
        ex = c.exploratory(self.results())
        self.assertEqual(ex["by_translate_group"]["gnome"], {"governed": 20, "flagged": 1})
        self.assertEqual(ex["dirs_by_build"]["other"],
                         {"dirs": 5, "with_dropped": 5, "with_phantom": 0})
        self.assertEqual(ex["repos_with_linguas_dir"], 45)

    def test_gate(self):
        v, _, _ = c.grade(self.results())
        self.assertEqual(v["G"], "FAILED (55 read, 40 with a governed LINGUAS directory)")
        self.assertEqual(v["P1"], "NOT TESTABLE (gate)")

    def test_p1_too_high_and_p3_failed(self):
        rs = [res(i, "gnome", [dr("meson", ["fr"], subs=["no"])]) for i in range(20)]
        rs += [res(100 + i, "none", [dr("meson")]) for i in range(20)]
        with mock.patch.object(c, "GATE_READ", 1), mock.patch.object(c, "GATE_GOVERNED", 1):
            v, counts, _ = c.grade(rs)
        self.assertEqual(counts["flagged_repos"], 20)
        self.assertEqual(v["P1"], "FAILED")
        self.assertEqual(v["P2"], "FAILED")
        self.assertEqual(v["P3"], "FAILED")
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
        files = {
            "po/LINGUAS": b"# languages\nde\n",
            "po/meson.build": b"i18n.gettext(meson.project_name(), preset: 'glib')\n",
            "po/de.po": PO,
            "po/fr.po": STUB,
            "po/app.pot": b'msgid ""\nmsgstr ""\n',
            "help/LINGUAS": b"de\n",
            "help/de/de.po": PO,
            "subprojects/lib/po/LINGUAS": b"\n",
            "subprojects/lib/po/es.po": PO,
            "data/po/LINGUAS": b"es\n",
            "data/po/es.po": PO,
            "data/po/it.po": PO,
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
        r = c.analyse({"repo": "file://" + src, "group": "none", "apps": ["x.App"]}, work)
        self.assertEqual(r["status"], "ok", r["status"])
        self.assertEqual(r["n_paths"], 13)
        self.assertEqual(r["n_linguas_dirs"], 2)
        self.assertEqual([x["dir"] for x in r["dirs"]], ["data/po", "po"])
        other, meson = r["dirs"]
        self.assertEqual((other["build"], other["dropped"], other["files"]), ("other", ["it"], []))
        self.assertEqual((meson["build"], meson["n_po"], meson["n_listed"]), ("meson", 2, 1))
        self.assertEqual((meson["dropped"], meson["phantom"]), (["fr"], []))
        self.assertEqual(meson["files"], [{"stem": "fr", "path": "po/fr.po", "entries": 2,
                                           "translated": 0, "fuzzy": 0, "substantive": "no"}])
        json.dumps(r, ensure_ascii=False)


if __name__ == "__main__":
    unittest.main()
