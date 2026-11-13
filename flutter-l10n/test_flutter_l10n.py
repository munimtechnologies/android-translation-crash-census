# Tests for flutter_l10n. Standard library only.
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import contextlib
import io
import json
import os
import plistlib
import shutil
import tempfile
import unittest

import flutter_l10n as fl

PUBSPEC = "name: demo\nflutter:\n  generate: true\n"
L10N_YAML = "arb-dir: lib/l10n\ntemplate-arb-file: app_en.arb\n"
EN = json.dumps({"@@locale": "en", "hello": "Hello", "bye": "Bye"})


def arb(**msgs):
    return json.dumps(msgs)


MAIN_LITERAL = (
    "import 'package:flutter/material.dart';\n"
    "// supportedLocales: [Locale('xx')]\n"
    "void main() => runApp(MaterialApp(\n"
    "  supportedLocales: const [\n"
    "    Locale('en'),\n"
    "    Locale('zh', 'TW'),   // Traditional Chinese, by country\n"
    "    Locale.fromSubtags(languageCode: 'pt'),\n"
    "    Locale('ko'),\n"
    "    Locale(\"fr\"),\n"
    "  ],\n"
    "  home: Text('a, b)'),\n"
    "));\n")

MAIN_GENERATED = (
    "import 'package:flutter/material.dart';\n"
    "void main() => runApp(MaterialApp(\n"
    "  localizationsDelegates: AppLocalizations.localizationsDelegates,\n"
    "  supportedLocales: AppLocalizations.supportedLocales,\n"
    "));\n")

GENERATED = (
    "abstract class AppLocalizations {\n"
    "  static const List<Locale> supportedLocales = <Locale>[Locale('en')];\n"
    "  void f() => g(supportedLocales: [Locale('zz')]);\n"
    "}\n"
    "AppLocalizations lookupAppLocalizations(Locale locale) {\n"
    "  throw FlutterError('AppLocalizations.delegate failed to load unsupported locale "
    "\"$locale\".');\n"
    "}\n")

PBXPROJ = ("/* Begin PBXProject section */\n"
           "\t\t\tdevelopmentRegion = en;\n"
           "\t\t\tknownRegions = (\n"
           "\t\t\t\ten,\n"
           "\t\t\t\tBase,\n"
           "\t\t\t\t\"es-419\",\n"
           "\t\t\t\tfr,\n"
           "\t\t\t);\n")

MANIFEST = ('<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '  <application android:label="demo"\n'
            '      android:localeConfig="@xml/locales_config">\n'
            '  </application>\n'
            '</manifest>\n')

LOCALES_CONFIG = ('<locale-config xmlns:android="http://schemas.android.com/apk/res/android">\n'
                  '  <locale android:name="en"/>\n'
                  '  <locale android:name="es-ES"/>\n'
                  '  <!-- <locale android:name="ja"/> -->\n'
                  '  <locale android:name="de"/>\n'
                  '</locale-config>\n')


class ProjectTest(unittest.TestCase):
    def make(self, files):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for rel, content in files.items():
            path = os.path.join(tmp, *rel.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(content)
        return tmp

    def kinds(self, res):
        return res["findings_by_kind"]


class UnitTest(unittest.TestCase):
    def test_try_parse_locale(self):
        self.assertEqual(fl.try_parse_locale("pt_BR"), ("pt", None, "BR"))
        self.assertEqual(fl.try_parse_locale("zh-hant-tw"), ("zh", "Hant", "TW"))
        self.assertEqual(fl.try_parse_locale("app_en"), ("app", None, "EN"))
        self.assertIsNone(fl.try_parse_locale("app_pt_BR"))
        self.assertIsNone(fl.try_parse_locale("intl"))

    def test_filename_locale(self):
        self.assertEqual(fl.filename_locale("app_en"), ("en", None, None))
        self.assertEqual(fl.filename_locale("app_pt_BR"), ("pt", None, "BR"))
        self.assertEqual(fl.filename_locale("strings_ui_de"), ("de", None, None))
        self.assertEqual(fl.filename_locale("app_fil"), ("fil", None, None))
        self.assertIsNone(fl.filename_locale("messages"))

    def test_lookup(self):
        known = {("en", None, None), ("zh", None, None), ("zh", "Hant", None),
                 ("pt", None, None), ("pt", None, "BR")}
        self.assertEqual(fl.lookup(("zh", None, "TW"), known), ("zh", None, None))
        self.assertEqual(fl.lookup(("zh", "Hant", "TW"), known), ("zh", "Hant", None))
        self.assertEqual(fl.lookup(("pt", None, "br"), known), ("pt", None, None))
        self.assertEqual(fl.lookup(("pt", None, "BR"), known), ("pt", None, "BR"))
        self.assertIsNone(fl.lookup(("de", None, None), known))

    def test_parse_locale_expr(self):
        self.assertEqual(fl.parse_locale_expr("Locale('iw')"), ("he", None, None))
        self.assertEqual(fl.parse_locale_expr("const Locale('en', '')"), ("en", None, None))
        self.assertEqual(fl.parse_locale_expr('Locale("pt", "BR")'), ("pt", None, "BR"))
        self.assertEqual(fl.parse_locale_expr(
            "Locale.fromSubtags(languageCode: 'zh', scriptCode: 'Hant')"),
            ("zh", "Hant", None))
        self.assertIsNone(fl.parse_locale_expr("myLocale"))

    def test_strip_comments_keeps_strings(self):
        self.assertEqual(fl.strip_comments("a = 'http://x'; // c\nb"), "a = 'http://x'; \nb")
        self.assertEqual(fl.strip_comments("a /* x\ny */ b"), "a \n b")

    def test_language(self):
        self.assertEqual(fl.language("zh-Hans"), "zh")
        self.assertEqual(fl.language("b+sr+Latn"), "sr")
        self.assertEqual(fl.language("iw"), "he")
        self.assertEqual(fl.language("English"), "en")


class DartListTest(ProjectTest):
    def test_literal_list(self):
        root = self.make({
            "pubspec.yaml": PUBSPEC, "l10n.yaml": L10N_YAML,
            "lib/l10n/app_en.arb": EN,
            "lib/l10n/app_zh.arb": arb(hello="Ni hao"),
            "lib/l10n/app_zh_Hant.arb": arb(hello="Ni hao (Hant)"),
            "lib/l10n/app_pt.arb": arb(hello="Ola"),
            "lib/l10n/app_pt_BR.arb": arb(hello="Oi"),
            "lib/l10n/app_de.arb": arb(hello="Hello", bye="Bye"),
            "lib/l10n/app_fr.arb": json.dumps({"@@locale": "fr"}),
            "lib/main.dart": MAIN_LITERAL,
        })
        res = fl.check(root)
        status = {a["file"]: a["status"] for a in res["arb"]}
        self.assertEqual(status["app_de.arb"], "same_as_template")
        self.assertEqual(status["app_fr.arb"], "empty")
        self.assertEqual(status["app_pt_BR.arb"], "ok")
        self.assertEqual(res["active_locales"], ["en", "pt", "pt_BR", "zh", "zh_Hant"])
        self.assertEqual(res["dart"]["status"], "checked")
        arg = res["dart"]["supported_locales_arguments"][0]
        self.assertEqual((arg["file"], arg["line"], arg["kind"]), ("lib/main.dart", 4, "literal"))
        self.assertEqual(arg["locales"], ["en", "zh_TW", "pt", "ko", "fr"])
        self.assertEqual(arg["unsupported"], ["ko"])
        self.assertEqual(res["dart"]["unreachable"], ["pt_BR", "zh_Hant"])
        self.assertEqual(self.kinds(res), {"unsupported_language": 1, "unreachable": 2})

    def test_identifier_resolved_in_other_file(self):
        root = self.make({
            "pubspec.yaml": PUBSPEC,
            "lib/l10n/app_en.arb": EN,
            "lib/l10n/app_de.arb": arb(hello="Hallo"),
            "lib/l10n/app_it.arb": arb(hello="Ciao"),
            "lib/app.dart": "const kLocales = <Locale>[Locale('en'), Locale('de')];\n",
            "lib/main.dart": "void main() => runApp(MaterialApp(supportedLocales: kLocales));\n",
        })
        res = fl.check(root)
        arg = res["dart"]["supported_locales_arguments"][0]
        self.assertEqual(arg["kind"], "literal")
        self.assertEqual(arg["defined_in"], "lib/app.dart:1")
        self.assertEqual(res["dart"]["unreachable"], ["it"])
        self.assertEqual(self.kinds(res), {"unreachable": 1})

    def test_custom_resolution_is_not_judged(self):
        root = self.make({
            "pubspec.yaml": PUBSPEC,
            "lib/l10n/app_en.arb": EN,
            "lib/l10n/app_it.arb": arb(hello="Ciao"),
            "lib/main.dart": ("void main() => runApp(MaterialApp(\n"
                              "  localeResolutionCallback: (l, s) => s.first,\n"
                              "  supportedLocales: const [Locale('en'), Locale('ko')],\n"
                              "));\n"),
        })
        res = fl.check(root)
        self.assertEqual(res["dart"]["status"], "not_all_literal")
        self.assertEqual(res["findings"], [])

    def test_default_supported_locales(self):
        root = self.make({
            "pubspec.yaml": PUBSPEC,
            "lib/l10n/app_en.arb": EN,
            "lib/l10n/app_es.arb": arb(hello="Hola"),
            "lib/main.dart": ("void main() => runApp(MaterialApp(\n"
                              "  localizationsDelegates: AppLocalizations.localizationsDelegates,\n"
                              "));\n"),
        })
        res = fl.check(root)
        self.assertEqual(res["dart"]["status"], "default_en_US")
        self.assertEqual(self.kinds(res), {"default_supported_locales": 1})
        self.assertEqual(res["findings"][0]["locale"], "es")


class PlatformTest(ProjectTest):
    def project(self):
        info = plistlib.dumps({"CFBundleName": "demo",
                               "CFBundleLocalizations": ["en", "es", "iw"]}).decode("utf-8")
        return self.make({
            "pubspec.yaml": PUBSPEC,
            "lib/l10n/app_en.arb": EN,
            "lib/l10n/app_es.arb": arb(hello="Hola"),
            "lib/l10n/app_he.arb": arb(hello="Shalom"),
            "lib/l10n/app_ja.arb": arb(hello="Konnichiwa"),
            "lib/l10n/app_localizations.dart": GENERATED,
            "lib/main.dart": MAIN_GENERATED,
            "ios/Runner.xcodeproj/project.pbxproj": PBXPROJ,
            "ios/Runner/Info.plist": info,
            "android/app/src/main/AndroidManifest.xml": MANIFEST,
            "android/app/src/main/res/xml/locales_config.xml": LOCALES_CONFIG,
        })

    def test_ios_and_android(self):
        res = fl.check(self.project())
        self.assertEqual(res["config"]["source"], "default")
        self.assertEqual(res["active_locales"], ["en", "es", "he", "ja"])
        self.assertEqual(len(res["dart"]["supported_locales_arguments"]), 1)
        self.assertEqual(res["dart"]["supported_locales_arguments"][0]["kind"], "expression")
        self.assertEqual(res["dart"]["status"], "not_all_literal")
        self.assertEqual(res["ios"]["known_regions"], ["en", "Base", "es-419", "fr"])
        self.assertEqual(res["ios"]["not_declared"], ["he", "ja"])
        self.assertEqual(res["ios"]["no_translation"], ["fr"])
        self.assertEqual(res["ios"]["plist_not_declared"], ["ja"])
        self.assertEqual(res["android"]["locales"], ["en", "es-ES", "de"])
        self.assertEqual(res["android"]["not_declared"], ["he", "ja"])
        self.assertEqual(res["android"]["no_translation"], ["de"])
        self.assertEqual(self.kinds(res), {"ios_not_declared": 2, "plist_not_declared": 1,
                                           "android_not_declared": 2})

    def test_cli_exit_codes(self):
        root = self.project()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(fl.main([root]), 0)
            self.assertEqual(fl.main([root, "--strict"]), 1)
            self.assertEqual(fl.main([os.path.join(root, "lib")]), 2)
        self.assertIn('"findings_by_kind"', out.getvalue())


class ConfigTest(ProjectTest):
    def test_flutter_intl(self):
        root = self.make({
            "pubspec.yaml": ("name: demo\nflutter_intl:\n  enabled: true\n"
                             "  arb_dir: lib/i18n\n  main_locale: de\n"),
            "lib/i18n/intl_de.arb": arb(hello="Hallo"),
            "lib/i18n/intl_en.arb": arb(hello="Hello"),
        })
        res = fl.check(root)
        self.assertEqual(res["config"], {"source": "pubspec flutter_intl", "arb_dir": "lib/i18n",
                                         "template_arb_file": "intl_de.arb"})
        self.assertEqual(res["active_locales"], ["de", "en"])
        self.assertEqual(res["dart"]["status"], "no_app_widget")

    def test_bad_arb_files(self):
        root = self.make({
            "pubspec.yaml": PUBSPEC,
            "lib/l10n/app_en.arb": EN,
            "lib/l10n/app_es.arb": json.dumps({"@@locale": "fr", "hello": "Bonjour"}),
            "lib/l10n/strings.arb": arb(hello="x"),
            "lib/l10n/bad_de.arb": "{not json",
        })
        res = fl.check(root)
        status = {a["file"]: a["status"] for a in res["arb"]}
        self.assertEqual(status, {"app_en.arb": "ok", "app_es.arb": "conflict",
                                  "strings.arb": "no_locale", "bad_de.arb": "invalid_json"})
        self.assertEqual(res["active_locales"], ["en"])

    def test_no_arb_dir(self):
        root = self.make({"pubspec.yaml": PUBSPEC, "lib/main.dart": "void main() {}\n"})
        self.assertIsNone(fl.check(root))


if __name__ == "__main__":
    unittest.main()
