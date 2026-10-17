"""Tests for np_order.py (no network). Apache-2.0. MV2 of Munim, Inc., made with AI agents."""

import unittest

import np_order as n

BY_LANGUAGE = (
    "scope,group,kind,valid,reordered,reorder_rate,unsafe,unsafe_share,numbered_in_order,repos,"
    "repos_with_reorder,repo_mean_rate,ci_low,ci_high,unique_valid,unique_reorder_rate,other\n"
    "all,,numbered,100,5,0.05,0,0.0,95,10,3,0.04,0.01,0.09,90,0.05,0\n"
    "lang:ja,SOV,numbered,400,80,0.2,0,0.0,320,30,12,0.15,0.1,0.3,350,0.21,1\n"
    "lang:ja,SOV,unnumbered_same,40,0,0.0,0,0.0,0,5,0,0.0,,,40,0.0,0\n"
    "lang:aa,unassigned,numbered,2,0,0.0,0,,2,1,0,0.0,,,1,0.0,0\n"
)
SIL_ISO = ("Id\tPart2b\tPart2t\tPart1\tScope\tLanguage_Type\tRef_Name\tComment\n"
           "jpn\tjpn\tjpn\tja\tI\tL\tJapanese\t\n"
           "fas\tper\tfas\tfa\tM\tL\tPersian\t\n"
           "ara\tara\tara\tar\tM\tL\tArabic\t\n")
SIL_MACRO = "M_Id\tI_Id\tI_Status\nfas\tpes\tA\nfas\tprs\tA\nara\tarz\tA\nara\tapc\tA\nara\txxx\tR\n"
WALS_LANGUAGES = (
    "ID,Name,Macroarea,Latitude,Longitude,Glottocode,ISO639P3code,Family,Subfamily,Genus,GenusIcon,"
    "ISO_codes,Samples_100,Samples_200,Country_ID,Source,Parent_ID\n"
    "jpn,Japanese,Eurasia,35,135,nucl1643,jpn,Japanese,,Japanese,,jpn,true,true,JP,x,g\n"
    "prs,Persian,Eurasia,32,54,west2369,pes,Indo-European,,Iranian,,pes,true,true,IR,x,g\n"
    "aeg,Arabic (Egyptian),Africa,30,31,egyp1253,arz,Afro-Asiatic,,Semitic,,arz,true,true,EG,x,g\n"
    "ale,Arabic (Levantine),Eurasia,33,36,nort3139,apc,Afro-Asiatic,,Semitic,,apc,false,false,SY,x,g\n"
)
WALS_CODES = ("ID,Parameter_ID,Name,Description,Number,icon\n"
              "81A-1,81A,SOV,x,1,\n81A-2,81A,SVO,x,2,\n81A-3,81A,VSO,x,3,\n"
              "86A-1,86A,Genitive-Noun,x,1,\n86A-2,86A,Noun-Genitive,x,2,\n86A-3,86A,No dominant order,x,3,\n")
WALS_VALUES = ("ID,Language_ID,Parameter_ID,Value,Code_ID,Comment,Source,Example_ID\n"
               "81A-jpn,jpn,81A,1,81A-1,,s,\n86A-jpn,jpn,86A,1,86A-1,,s,\n"
               "81A-prs,prs,81A,1,81A-1,,s,\n86A-prs,prs,86A,2,86A-2,,s,\n"
               "81A-aeg,aeg,81A,2,81A-2,,s,\n86A-aeg,aeg,86A,2,86A-2,,s,\n"
               "81A-ale,ale,81A,3,81A-3,,s,\n86A-ale,ale,86A,2,86A-2,,s,\n"
               "84A-jpn,jpn,84A,1,84A-1,,s,\n")


class ReadTests(unittest.TestCase):
    def test_rates_numbered_language_rows_only(self):
        r = n.read_rates(BY_LANGUAGE)
        self.assertEqual(sorted(r), ["aa", "ja"])
        self.assertEqual(r["ja"]["valid"], 400)
        self.assertAlmostEqual(r["ja"]["rate"], 0.2)
        self.assertAlmostEqual(r["ja"]["unique_rate"], 0.21)

    def test_sil_skips_retired_members(self):
        part1, members = n.read_sil(SIL_ISO, SIL_MACRO)
        self.assertEqual(part1["ja"], "jpn")
        self.assertEqual(members["ara"], ["arz", "apc"])

    def test_candidates_tiers(self):
        part1, members = n.read_sil(SIL_ISO, SIL_MACRO)
        self.assertEqual(n.candidates("ja", part1, members), [["jpn"], []])
        self.assertEqual(n.candidates("fa", part1, members), [["pes"], ["fas"], ["pes", "prs"]])
        self.assertEqual(n.candidates("ckb", part1, members), [["ckb"], []])
        self.assertEqual(n.candidates("zz", part1, members), [])


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.part1, self.members = n.read_sil(SIL_ISO, SIL_MACRO)
        self.by_iso, self.values = n.read_wals(WALS_LANGUAGES, WALS_CODES, WALS_VALUES)

    def look(self, lang, feature):
        return n.feature_value(n.candidates(lang, self.part1, self.members), self.by_iso, self.values, feature)

    def test_direct_and_main_variety(self):
        self.assertEqual(self.look("ja", "86A"), ("Genitive-Noun", ["jpn"]))
        self.assertEqual(self.look("fa", "86A"), ("Noun-Genitive", ["prs"]))
        self.assertEqual(self.look("fa", "81A")[0], "SOV")

    def test_macro_members_agree_or_conflict(self):
        self.assertEqual(self.look("ar", "86A"), ("Noun-Genitive", ["aeg", "ale"]))
        self.assertEqual(self.look("ar", "81A")[0], "conflict")

    def test_unknown_language_and_feature(self):
        self.assertEqual(self.look("zz", "86A"), (None, []))
        self.assertEqual(self.look("ja", "90A"), (None, []))

    def test_side(self):
        self.assertEqual(n.side("SOV", "81A"), 1)
        self.assertEqual(n.side("VSO", "81A"), 0)
        self.assertIsNone(n.side("No dominant order", "81A"))
        self.assertIsNone(n.side("conflict", "86A"))
        self.assertIsNone(n.side(None, "86A"))


class StatsTests(unittest.TestCase):
    def test_auc(self):
        self.assertEqual(n.auc([(1, 0.3), (1, 0.2), (0, 0.1), (0, 0.0)]), 1.0)
        self.assertEqual(n.auc([(1, 0.1), (0, 0.1)]), 0.5)
        self.assertEqual(n.auc([(1, 0.0), (0, 0.2)]), 0.0)
        self.assertIsNone(n.auc([(1, 0.1)]))

    def rows(self):
        # 86A splits rates perfectly; 81A does not.
        data = [("a", 0.30, 1, 1, 1, 1), ("b", 0.25, 1, 0, 1, 0), ("c", 0.20, 1, 1, 0, 1),
                ("d", 0.05, 0, 1, 0, 0), ("e", 0.02, 0, 0, 0, 1), ("f", 0.01, 0, 0, 1, 0),
                ("g", 0.03, 0, 1, None, 0)]
        return [{"lang": l, "rate": r, "86A": g, "81A": v, "85A": p, "87A": a, "90A": None}
                for l, r, g, v, p, a in data]

    def test_compare(self):
        c = n.compare(self.rows(), "86A", "81A", draws=200)
        self.assertEqual(c["languages"], 7)
        self.assertEqual(c["auc"][0], 1.0)
        self.assertLess(c["auc"][1], 1.0)
        self.assertTrue(c["testable"])
        self.assertLessEqual(c["diff_ci95"][0], c["diff_ci95"][1])

    def test_compare_not_testable(self):
        c = n.compare(self.rows()[:3], "86A", "81A", draws=50)
        self.assertFalse(c["testable"])
        self.assertEqual(c["diff_ci95"], [None, None])

    def test_predictions_shape(self):
        preds = n.predictions(self.rows())
        self.assertEqual([p[0] for p in preds], ["P1", "P2", "P3", "P4", "P5"])
        self.assertTrue(preds[0][2])
        # Only two SOV genitive-noun languages (a, c): P3 is not testable.
        self.assertIsNone(preds[2][2])
        self.assertEqual(n.verdict(None), "NOT TESTABLE")

    def test_seen_languages_left_out_of_p4(self):
        rows = self.rows() + [{"lang": "zh", "rate": 0.9, "86A": 1, "81A": 0, "85A": None,
                               "87A": None, "90A": None}]
        m = n.median_split(rows, "86A", lambda r: r["81A"] == 0 and r["lang"] not in n.SEEN)
        self.assertNotIn("zh", m["positive"])


if __name__ == "__main__":
    unittest.main()
