"""Tests for zwsp_signature.py. MV2, Munim, Inc. Made with AI agents. Apache-2.0."""
import csv
import json
import os
import tempfile
import unittest

import zwsp_signature as zs

Z = chr(0x200B)
A = "https://example.org/a"
B = "https://example.org/b"
FIELDS = ["repo", "head", "platform", "res_dir", "locale_dir", "lang", "key", "index",
          "classes", "codepoints", "source", "target"]


def row(repo, platform, lang, key, target, classes="zwsp", codepoints="U+200B"):
    return {"repo": repo, "head": "0" * 40, "platform": platform, "res_dir": "app/src/main/res",
            "locale_dir": "values-" + lang, "lang": lang, "key": key, "index": "0",
            "classes": classes, "codepoints": codepoints, "source": "Hello world", "target": target}


ROWS = [
    row(A, "other", "it", "string:k1", "Ciao <U+200B><U+200B>mondo"),
    row(A, "other", "fr", "string:k1", "Salut <U+200B><U+200B>monde"),
    row(A, "other", "de", "string:k1", "Hallo <U+200B><U+200B>Welt"),
    row(B, "weblate", "es", "string:k2", "Hola<U+200B>"),
    row(B, "weblate", "es", "string:k3", "Ho<U+00AD>la <U+200B><U+200B>x", classes="zwsp;shy",
        codepoints="U+200B;U+00AD"),
]


class SignatureTest(unittest.TestCase):
    def test_decode(self):
        self.assertEqual(zs.decode("a<U+200B>b"), "a" + Z + "b")
        self.assertEqual(zs.decode("a<U+00AD>b"), "a" + chr(0xAD) + "b")

    def test_runs(self):
        self.assertEqual(zs.runs("x " + Z + Z + "word"), [(2, " ", "w")])
        self.assertEqual(zs.runs(Z + "a" + Z), [(1, "", "a"), (1, "a", "")])
        self.assertEqual(zs.runs("plain"), [])

    def test_kind(self):
        self.assertEqual(zs.kind((2, " ", "w")), "pair-after-space")
        self.assertEqual(zs.kind((2, "a", "b")), "pair-other")
        self.assertEqual(zs.kind((2, " ", ".")), "pair-other")
        self.assertEqual(zs.kind((1, "", "")), "single")
        self.assertEqual(zs.kind((5, "x", "")), "longer")

    def test_classify(self):
        self.assertEqual(zs.classify("Nekaj <U+200B><U+200B>je"), "pair-after-space")
        self.assertEqual(zs.classify("<U+200B>x"), "single")
        self.assertEqual(zs.classify("a <U+200B><U+200B>."), "pair-other")
        self.assertEqual(zs.classify("料理" + "<U+200B>" * 5), "longer")
        self.assertEqual(zs.classify("<U+200B>x y <U+200B><U+200B>z"), "pair-after-space")
        self.assertEqual(zs.classify("nothing here"), "none")

    def test_analyze(self):
        r = zs.analyze(ROWS)
        self.assertEqual(r["zwsp_only_rows"], 4)
        self.assertEqual(r["by_kind"], {"pair-after-space": 3, "single": 1})
        self.assertEqual(r["signature_rows"], 3)
        self.assertEqual(r["signature_share"], 0.75)
        self.assertEqual(r["by_platform"], {"other": {"pair-after-space": 3},
                                            "weblate": {"single": 1}})
        self.assertEqual(r["repos_with_zwsp"], 2)
        self.assertEqual(r["repos_with_signature"], 1)
        self.assertEqual(r["langs_with_signature"], 3)
        self.assertEqual(r["signature_rows_in_top_repo"], 3)
        self.assertEqual(r["top_repos"], [[A, 3, 3]])
        self.assertEqual(r["shared_keys_3plus_langs"], 1)
        self.assertEqual(r["shared_keys"], [[A, "string:k1", "de;fr;it"]])
        self.assertEqual(r["repo_counts"], [[A, 3, 3], [B, 0, 1]])
        self.assertEqual(r["lang_counts"], [["de", 1], ["fr", 1], ["it", 1]])
        self.assertEqual(len(r["examples"]), 3)

    def test_main_on_local_csv(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "hits.csv")
            with open(path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=FIELDS)
                w.writeheader()
                w.writerows(ROWS)
            out = os.path.join(d, "out")
            self.assertEqual(zs.main(["--hits", path, "--out-dir", out]), 0)
            with open(os.path.join(out, "summary.json"), encoding="utf-8") as f:
                s = json.load(f)
            self.assertEqual(s["zwsp_only_rows"], 4)
            self.assertEqual(s["version"], zs.__version__)
            self.assertEqual(len(s["hits_sha256"]), 64)
            with open(os.path.join(out, "by_repo.csv"), encoding="utf-8") as f:
                self.assertEqual(len(f.read().splitlines()), 3)
            with open(os.path.join(out, "shared_keys.csv"), encoding="utf-8") as f:
                self.assertEqual(len(f.read().splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
