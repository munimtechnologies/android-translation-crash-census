# Tests for weblate_linux.py (no network, no gettext tools). Apache-2.0.
# Made with AI agents by MV2 of Munim, Inc.
import copy
import unittest

import weblate_linux as w

SAMPLE = '''
LEGACY_CODES = {
    "zh_Hans": "zh_CN",
    "zh_Hant": "zh_TW",
}
LINUX_CODES: dict[str, str] = {
    "sr_Latn": "sr",
    "sr_Cyrl": "sr@cyrillic",
    "uz_Latn": "uz@latin",
    "be_Latn": "be@latin",
}


class Fmt:
    @classmethod
    def get_language_linux(cls, code):
        return LINUX_CODES.get(code, cls.get_language_legacy(code))
'''

GOOD = {
    "weblate/serbian": {"sr_RS.UTF-8": "sr_Latn", "sr_RS.UTF-8@latin": "sr_Latn",
                        "sr_ME.UTF-8": "sr_Latn"},
    "weblate/uzbek": {"uz_UZ.UTF-8": "uz", "uz_UZ.UTF-8@cyrillic": "uz"},
    "weblate/belarusian": {"be_BY.UTF-8": "be", "be_BY.UTF-8@latin": "be_Latn"},
    "weblate/chinese": {"zh_CN.UTF-8": "zh_Hans", "zh_TW.UTF-8": "zh_Hant"},
    "fix/serbian": {"sr_RS.UTF-8": "sr_Cyrl", "sr_RS.UTF-8@latin": "sr_Latn",
                    "sr_ME.UTF-8": "sr_Cyrl"},
    "fix/uzbek": {"uz_UZ.UTF-8": "uz_Latn", "uz_UZ.UTF-8@cyrillic": "uz"},
    "fix/belarusian": {"be_BY.UTF-8": "be", "be_BY.UTF-8@latin": "be_Latn"},
    "fix/chinese": {"zh_CN.UTF-8": "zh_Hans", "zh_TW.UTF-8": "zh_Hant"},
}


def setup_case():
    tables = w.read_tables(SAMPLE)["tables"]
    scripts = dict(w.EXPECT_SCRIPT)
    locales = {name: True for _, name in w.LOCALEDEF}
    look = {"errors": [], "c": copy.deepcopy(GOOD), "py": copy.deepcopy(GOOD)}
    return tables, scripts, locales, look


class ReadTables(unittest.TestCase):
    def test_tables_and_functions(self):
        r = w.read_tables(SAMPLE)
        self.assertEqual(r["tables"]["LINUX_CODES"]["sr_Latn"], "sr")
        self.assertEqual(r["tables"]["LEGACY_CODES"]["zh_Hant"], "zh_TW")
        self.assertIn("LINUX_CODES.get", r["functions"]["get_language_linux"])

    def test_non_literal_table(self):
        r = w.read_tables("LINUX_CODES = make()\n")
        self.assertIsNone(r["tables"]["LINUX_CODES"])


class Names(unittest.TestCase):
    def test_linux_name(self):
        t = w.read_tables(SAMPLE)["tables"]
        self.assertEqual(w.linux_name("sr_Latn", t), "sr")
        self.assertEqual(w.linux_name("sr_Cyrl", t), "sr@cyrillic")
        self.assertEqual(w.linux_name("zh_Hans", t), "zh_CN")
        self.assertEqual(w.linux_name("uz", t), "uz")
        self.assertEqual(w.linux_name("pt-BR", t), "pt_BR")

    def test_style_name(self):
        t = w.read_tables(SAMPLE)["tables"]
        self.assertEqual(w.style_name("fix", "sr_Latn", t), "sr@latin")
        self.assertEqual(w.style_name("weblate", "uz_Latn", t), "uz@latin")

    def test_fix_names_distinct(self):
        for _, members in w.TREES:
            names = [w.FIX[c] for c, _ in members]
            self.assertEqual(len(set(names)), len(names))


class Helpers(unittest.TestCase):
    def test_script_of(self):
        cyr = "".join(chr(c) for c in (0x43F, 0x43E, 0x43D, 0x435, 0x434, 0x435, 0x459, 0x430,
                                         0x43A))
        self.assertEqual(w.script_of(cyr), "Cyrl")
        self.assertEqual(w.script_of("ponedeljak"), "Latn")
        self.assertEqual(w.script_of(chr(0x661F) + chr(0x671F) + chr(0x4E00)), "Hani")
        self.assertEqual(w.script_of(""), "")
        self.assertEqual(w.script_of("123 -"), "")

    def test_reached(self):
        self.assertEqual(w.reached("X-sr_Latn", ["sr_Cyrl", "sr_Latn"]), "sr_Latn")
        self.assertEqual(w.reached("Hello", ["sr_Latn"]), "")
        self.assertEqual(w.reached("X-zz", ["sr_Latn"]), "")

    def test_parse_back(self):
        aliases = {"sr@cyrillic": "sr_Cyrl", "sr@latin": "sr_Latn"}
        codes = ["sr", "sr_Cyrl", "sr_Latn"]
        self.assertEqual(w.parse_back("sr", aliases, codes), "sr")
        self.assertEqual(w.parse_back("sr@cyrillic", aliases, codes), "sr_Cyrl")
        self.assertIsNone(w.parse_back("xx", aliases, codes))

    def test_round_trip(self):
        t = w.read_tables(SAMPLE)["tables"]
        aliases = {"sr@cyrillic": "sr_Cyrl", "uz@latin": "uz_Latn", "be@latin": "be_Latn",
                   "zh_cn": "zh_Hans", "zh_tw": "zh_Hant"}
        codes = ["sr", "sr_Cyrl", "sr_Latn", "uz_Latn", "be_Latn", "zh_Hans", "zh_Hant"]
        rows = {r["code"]: r for r in w.round_trip(t, aliases, codes)}
        self.assertEqual(rows["sr_Latn"]["round_trip"], "no")
        self.assertEqual(rows["sr_Latn"]["parsed_back"], "sr")
        self.assertEqual(rows["sr_Cyrl"]["round_trip"], "yes")
        self.assertEqual(rows["zh_Hans"]["round_trip"], "yes")

    def test_csv_parsers(self):
        self.assertEqual(w.parse_csv_map("alias,language\nSR@Latin,sr_Latn\n")["sr@latin"],
                         "sr_Latn")
        self.assertEqual(w.parse_codes("code,name\nsr,Serbian\nsr_Latn,Serbian (Latin)\n"),
                         ["sr", "sr_Latn"])


class Grade(unittest.TestCase):
    def test_all_hold(self):
        v = w.grade(*setup_case())
        for k in ("T", "S", "W1", "W2", "W3", "K", "F", "W1py", "W2py", "W3py", "Kpy", "Fpy"):
            self.assertEqual(v[k], "HELD", k)

    def test_w1_w2_fail(self):
        tables, scripts, locales, look = setup_case()
        look["c"]["weblate/serbian"]["sr_RS.UTF-8"] = "sr_Cyrl"
        v = w.grade(tables, scripts, locales, look)
        self.assertEqual(v["W1"], "FAILED")
        self.assertEqual(v["W2"], "FAILED")
        self.assertEqual(v["W1py"], "HELD")

    def test_w3_fail(self):
        tables, scripts, locales, look = setup_case()
        look["py"]["weblate/uzbek"]["uz_UZ.UTF-8"] = "uz_Latn"
        v = w.grade(tables, scripts, locales, look)
        self.assertEqual(v["W3py"], "FAILED")
        self.assertEqual(v["W3"], "HELD")

    def test_fix_fail(self):
        tables, scripts, locales, look = setup_case()
        look["c"]["fix/uzbek"]["uz_UZ.UTF-8"] = ""
        self.assertEqual(w.grade(tables, scripts, locales, look)["F"], "FAILED")

    def test_control_fail(self):
        tables, scripts, locales, look = setup_case()
        look["c"]["weblate/chinese"]["zh_TW.UTF-8"] = ""
        self.assertEqual(w.grade(tables, scripts, locales, look)["K"], "FAILED")

    def test_sr_me_optional(self):
        tables, scripts, locales, look = setup_case()
        locales["sr_ME.UTF-8"] = False
        look["c"]["weblate/serbian"]["sr_ME.UTF-8"] = "sr_Cyrl"
        v = w.grade(tables, scripts, locales, look)
        self.assertEqual(v["S"], "HELD")
        self.assertEqual(v["W2"], "HELD")

    def test_gate_script(self):
        tables, scripts, locales, look = setup_case()
        scripts["uz_UZ.UTF-8"] = "Cyrl"
        v = w.grade(tables, scripts, locales, look)
        self.assertTrue(v["S"].startswith("FAILED"))
        self.assertEqual(v["W1"], "NOT TESTABLE")
        self.assertEqual(v["Fpy"], "NOT TESTABLE")

    def test_gate_table(self):
        tables, scripts, locales, look = setup_case()
        tables["LINUX_CODES"]["sr_Latn"] = "sr@latin"
        v = w.grade(tables, scripts, locales, look)
        self.assertEqual(v["T"], "FAILED")
        self.assertEqual(v["W2"], "NOT TESTABLE")

    def test_gate_missing_locale(self):
        tables, scripts, locales, look = setup_case()
        locales["be_BY.UTF-8@latin"] = False
        v = w.grade(tables, scripts, locales, look)
        self.assertTrue(v["S"].startswith("FAILED"))
        self.assertEqual(v["K"], "NOT TESTABLE")


if __name__ == "__main__":
    unittest.main()
