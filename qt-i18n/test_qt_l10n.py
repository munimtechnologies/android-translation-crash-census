# Tests for qt_l10n. Standard library only.
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import contextlib
import io
import os
import shutil
import tempfile
import unittest

import qt_l10n as q

TS = ('<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE TS>\n'
      '<TS version="2.1" language="%s">\n</TS>\n')
QM = b"\x3c\xb8\x64\x18\xca\xef\x9c\x95"

MAIN_CPP = (
    "#include <QTranslator>\n"
    "int main(int argc, char **argv) {\n"
    "    QTranslator qtTr;\n"
    "    // tr.load(QLocale(), \"app\", \"_\");\n"
    "    qtTr.load(\"qt_\" + QLocale::system().name(),\n"
    "              QLibraryInfo::path(QLibraryInfo::TranslationsPath));\n"
    "    QTranslator tr;\n"
    "    QString locale = QLocale::system().name();\n"
    "    tr.load(QString(\":/i18n/app_%1\").arg(locale));\n"
    "    QPixmap p; p.load(\":/icons/logo.png\");\n"
    "    return 0;\n"
    "}\n")

MAIN_PY = (
    "from PyQt6.QtCore import QLocale, QTranslator\n"
    "# translator.load(\"x_\" + QLocale.system().name())\n"
    "def setup(app, path):\n"
    "    translator = QTranslator()\n"
    "    translator.load(QLocale(), \"viewer\", \"_\", path)\n"
    "    helper = QTranslator()\n"
    "    lang = QLocale.system().name()[:2]\n"
    "    helper.load(f\"plugin_{lang}\", path)\n")


class Tmp(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def put(self, rel, content):
        path = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        mode = "wb" if isinstance(content, bytes) else "w"
        with open(path, mode) as fh:
            fh.write(content)

    def ts(self, rel):
        self.put(rel, TS % os.path.splitext(os.path.basename(rel))[0])

    def run_main(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = q.main([self.root] + list(args))
        return code, buf.getvalue()


class StemTests(unittest.TestCase):
    def test_split(self):
        self.assertEqual(q.split_stem("myapp_zh_Hans"), ("myapp_", "zh_Hans"))
        self.assertEqual(q.split_stem("app_pt-BR"), ("app_", "pt-BR"))
        self.assertEqual(q.split_stem("app_pt_BR"), ("app_", "pt_BR"))
        self.assertEqual(q.split_stem("my_app_de"), ("my_app_", "de"))
        self.assertEqual(q.split_stem("de"), ("", "de"))
        self.assertEqual(q.split_stem("app_sr@latin"), ("app_", "sr@latin"))
        self.assertEqual(q.split_stem("app_es_419"), ("app_", "es_419"))
        self.assertEqual(q.split_stem("qt_help_de"), ("qt_help_", "de"))
        self.assertEqual(q.split_stem("readme"), (None, None))

    def test_ambiguous_prefix(self):
        # 'tr_de' is Turkish-in-Germany or prefix 'tr_' + German.
        self.assertEqual(q.split_stem("pt_br"), ("", "pt_br"))
        self.assertEqual(q.split_stem("tr_de", {"": 2, "tr_": 2}), ("", "tr_de"))
        self.assertEqual(q.split_stem("tr_de", {"": 2, "tr_": 2}, {"tr"}), ("tr_", "de"))
        self.assertEqual(q.split_stem("tr_de", {"": 1, "tr_": 3}), ("tr_", "de"))


class JudgeTests(unittest.TestCase):
    def kind(self, code, style):
        v = q.judge(code, style)
        return v[0] if v else None

    def test_name_style(self):
        self.assertEqual(self.kind("zh_Hans", "A"), "script_code")
        self.assertEqual(self.kind("zh_hans", "A"), "script_code")
        self.assertEqual(self.kind("pt-BR", "A"), "hyphen")
        self.assertEqual(self.kind("sr@latin", "A"), "modifier")
        self.assertEqual(self.kind("pt_br", "A"), "case")
        self.assertEqual(self.kind("no", "A"), "legacy_code")
        self.assertIsNone(self.kind("nb_NO", "A"))
        self.assertIsNone(self.kind("pt_BR", "A"))
        self.assertIsNone(self.kind("es_419", "A"))
        self.assertIsNone(self.kind("fil", "A"))

    def test_language_only_style(self):
        self.assertEqual(self.kind("pt_BR", "A2"), "region_code")
        self.assertEqual(self.kind("es_419", "A2"), "region_code")
        self.assertIsNone(self.kind("pt", "A2"))

    def test_locale_overload(self):
        self.assertEqual(self.kind("pt-BR", "B"), "hyphen")
        self.assertEqual(self.kind("ca@valencia", "B"), "modifier")
        self.assertIsNone(self.kind("zh_Hans", "B"))
        self.assertIsNone(self.kind("pt_br", "B"))
        self.assertIsNone(self.kind("no", "B"))


class SourceTests(unittest.TestCase):
    def classify(self, text):
        i = text.index("load(") + 4
        return q.classify_call(text, q.call_args(text, i))[0]

    def test_strip_comments(self):
        self.assertEqual(q.strip_comments('a = "http://x"; // c\nb', False), 'a = "http://x"; \nb')
        self.assertEqual(q.strip_comments("x/* a\nb */y", False), "x\ny")
        self.assertEqual(q.strip_comments("s = '#x'  # c\n", True), "s = '#x'  \n")

    def test_styles(self):
        self.assertEqual(self.classify('t.load(":/i18n/app_" + QLocale().name().left(2));'), "A2")
        self.assertEqual(self.classify('t.load("app_" + QLocale::system().name(), dir);'), "A")
        self.assertEqual(self.classify('t.load("app_" + QLocale::system().bcp47Name(), d);'),
                         "bcp47")
        self.assertEqual(self.classify('QLocale loc = QLocale::system();\n'
                                       't.load(loc, "app", "_", dir);\n'), "B")
        self.assertEqual(self.classify('t.load(QLocale.system(), "app", "_", d)'), "B")
        self.assertIsNone(self.classify('p.load(":/icons/logo.png");'))

    def test_literal_base(self):
        self.assertEqual(q.literal_base(":/i18n/app_%1"), "app")
        self.assertEqual(q.literal_base("plugin_{lang}"), "plugin")
        self.assertEqual(q.literal_base(":/translations/"), "")


class ProjectTests(Tmp):
    def test_cpp_name_based(self):
        self.put("src/main.cpp", MAIN_CPP)
        for code in ("de", "es_419", "no", "pt-PT", "pt_BR", "sr@latin", "zh_Hans", "zh_Hant"):
            self.ts("translations/app_%s.ts" % code)
        self.ts("translations/qt_de.ts")
        self.put("web/de.ts", "export const x = 1;\n")
        r = q.check(self.root)
        self.assertEqual([(u["dir"], u["prefix"]) for u in r["units"]], [("translations", "app_")])
        unit = r["units"][0]
        self.assertEqual(unit["styles"], ["A"])
        self.assertEqual(unit["attribution"], "literal")
        self.assertEqual(len(unit["codes"]), 8)
        got = {(f["code"], f["kind"]) for f in r["findings"]}
        self.assertEqual(got, {("no", "legacy_code"), ("pt-PT", "hyphen"),
                               ("sr@latin", "modifier"), ("zh_Hans", "script_code"),
                               ("zh_Hant", "script_code")})
        self.assertEqual(sorted(c["style"] for c in r["calls"]), ["A", "A"])
        code, out = self.run_main("--strict")
        self.assertEqual(code, 1)
        self.assertIn("FINDING script_code: translations/app_zh_Hans", out)
        self.assertEqual(self.run_main()[0], 0)

    def test_python_two_styles(self):
        self.put("app/main.py", MAIN_PY)
        for code in ("de", "pt-BR", "zh_Hans", "pt_br"):
            self.put("app/i18n/viewer_%s.qm" % code, QM)
        for code in ("de", "pt_BR", "pt"):
            self.put("app/i18n/plugin_%s.qm" % code, QM)
        r = q.check(self.root)
        units = {u["prefix"]: u for u in r["units"]}
        self.assertEqual(sorted(units), ["plugin_", "viewer_"])
        self.assertEqual(units["viewer_"]["styles"], ["B"])
        self.assertEqual(units["plugin_"]["styles"], ["A2"])
        self.assertEqual(units["viewer_"]["codes"], ["de", "pt-BR", "pt_br", "zh_Hans"])
        got = {(f["prefix"], f["code"], f["kind"]) for f in r["findings"]}
        self.assertEqual(got, {("viewer_", "pt-BR", "hyphen"),
                               ("plugin_", "pt_BR", "region_code")})

    def test_qml_engine_and_no_call(self):
        self.put("qml/i18n/qml_de.qm", QM)
        self.put("qml/i18n/qml_pt-BR.qm", QM)
        self.ts("translations/de.ts")
        self.ts("translations/fr.ts")
        r = q.check(self.root)
        units = {u["dir"]: u for u in r["units"]}
        self.assertEqual(units["qml/i18n"]["attribution"], "qml_engine")
        self.assertEqual(units["translations"]["attribution"], "none")
        self.assertEqual([(f["code"], f["kind"]) for f in r["findings"]], [("pt-BR", "hyphen")])
        self.assertEqual([n["kind"] for n in r["notes"]], ["no_load_call_found"])

    def test_no_translations(self):
        self.put("src/main.cpp", "int main() { return 0; }\n")
        self.assertEqual(self.run_main()[0], 2)


if __name__ == "__main__":
    unittest.main()
