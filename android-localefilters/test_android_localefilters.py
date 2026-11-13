# Tests for android_localefilters. Standard library only.
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import contextlib
import io
import os
import shutil
import tempfile
import unittest

import android_localefilters as al

STRINGS = '<resources>\n  <string name="hello">%s</string>\n</resources>\n'

GROOVY = (
    "plugins {\n"
    "    id 'com.android.application'\n"
    "}\n"
    "android {\n"
    "    defaultConfig {\n"
    "        // resConfigs \"xx\"\n"
    "        resConfigs \"en\", 'de', \"pt\" /* , \"fr\" */\n"
    "        versionName \"1.0 // not a comment\"\n"
    "    }\n"
    "    productFlavors {\n"
    "        fdroid {\n"
    "            resConfig \"fr\"\n"
    "        }\n"
    "    }\n"
    "    androidResources { generateLocaleConfig true }\n"
    "}\n")

KTS = (
    "plugins { alias(libs.plugins.android.application) }\n"
    "val extra = listOf(\"ja\")\n"
    "android {\n"
    "    defaultConfig {\n"
    "        resourceConfigurations += listOf(\n"
    "            \"en\",\n"
    "            \"zh-rTW\", // Taiwan\n"
    "        )\n"
    "    }\n"
    "    androidResources {\n"
    "        localeFilters.addAll(listOf(\"b+sr+Latn\"))\n"
    "    }\n"
    "    productFlavors {\n"
    "        create(\"play\") {\n"
    "            resourceConfigurations += extra\n"
    "        }\n"
    "    }\n"
    "}\n"
    "tasks.register(\"show\") { println(android.defaultConfig.resourceConfigurations) }\n")

APP_KTS = (
    "plugins {\n"
    "    id(\"com.android.application\")\n"
    "}\n"
    "android {\n"
    "    defaultConfig {\n"
    "        resourceConfigurations += listOf(\"en\", \"pt\", \"zh-rTW\", \"xxhdpi\")\n"
    "    }\n"
    "}\n"
    "dependencies {\n"
    "    implementation(project(\":core:ui\"))\n"
    "}\n")

LIB_KTS = "plugins {\n    id(\"com.android.library\")\n}\n"

MANIFEST = ('<manifest xmlns:android="http://schemas.android.com/apk/res/android">\n'
            '  <application android:localeConfig="@xml/locales_config" />\n'
            '</manifest>\n')

LOCALES_CONFIG = (
    '<locale-config xmlns:android="http://schemas.android.com/apk/res/android">\n'
    '  <locale android:name="en" />\n'
    '  <locale android:name="pt-BR" />\n'
    '  <locale android:name="de" />\n'
    '  <locale android:name="zh-TW" />\n'
    '  <!-- <locale android:name="fr" /> -->\n'
    '</locale-config>\n')

KMP_APP_KTS = (
    "plugins {\n"
    "    id(\"com.android.application\")\n"
    "}\n"
    "android {\n"
    "    defaultConfig {\n"
    "        resourceConfigurations += listOf(\"en\", \"zh-rTW\", \"sr\")\n"
    "    }\n"
    "}\n"
    "dependencies {\n"
    "    implementation(projects.shared)\n"
    "}\n")

SHARED_KTS = (
    "plugins {\n"
    "    kotlin(\"multiplatform\")\n"
    "    id(\"com.android.library\")\n"
    "    id(\"dev.icerock.mobile.multiplatform-resources\")\n"
    "}\n"
    "dependencies {\n"
    "    commonMainApi(projects.coreUi)\n"
    "}\n")


def loc(lang, script="", region="", variant=""):
    return (lang, script, region, variant)


class ParseTest(unittest.TestCase):
    def test_folder_locale(self):
        p = al.parse_folder_locale
        self.assertEqual(p("fr"), loc("fr"))
        self.assertEqual(p("pt-rBR"), loc("pt", region="BR"))
        self.assertEqual(p("b+sr+Latn"), loc("sr", "Latn"))
        self.assertEqual(p("b+es+419"), loc("es", region="419"))
        self.assertEqual(p("mcc310-en-rUS"), loc("en", region="US"))
        self.assertEqual(p("fr-land"), loc("fr"))
        for q in ("land", "car", "night", "v21", "sw600dp", "xxhdpi"):
            self.assertIsNone(p(q), q)

    def test_filter_entry(self):
        p = al.parse_filter_entry
        self.assertEqual(p("en"), ("locale", loc("en")))
        self.assertEqual(p(" pt-rBR "), ("locale", loc("pt", region="BR")))
        self.assertEqual(p("b+sr+Latn"), ("locale", loc("sr", "Latn")))
        self.assertEqual(p("xxhdpi"), ("density", "xxhdpi"))
        self.assertEqual(p("en-US"), ("invalid", "en-US"))
        self.assertEqual(p("zh-Hant"), ("invalid", "zh-Hant"))
        self.assertEqual(p("zh_CN"), ("invalid", "zh_CN"))
        self.assertEqual(p("night"), ("other", "night"))
        self.assertEqual(p("fr-land"), ("other", "fr-land"))
        self.assertEqual(p("auto"), ("other", "auto"))

    def test_bcp47_and_fmt(self):
        self.assertEqual(al.parse_bcp47("zh-Hant-TW"), loc("zh", "Hant", "TW"))
        self.assertEqual(al.parse_bcp47("pt_BR"), loc("pt", region="BR"))
        self.assertEqual(al.fmt(loc("pt", region="BR")), "pt-rBR")
        self.assertEqual(al.fmt(loc("sr", "Latn")), "b+sr+Latn")
        self.assertEqual(al.fmt(loc("de")), "de")


class MatchTest(unittest.TestCase):
    def test_aapt2_rules(self):
        k = al.kept
        self.assertFalse(k(loc("pt", region="BR"), [loc("pt")]))
        self.assertTrue(k(loc("pt"), [loc("pt", region="BR")]))
        self.assertTrue(k(loc("pt", region="BR"), [loc("pt", region="BR")]))
        self.assertFalse(k(loc("sr", "Latn"), [loc("sr")]))
        self.assertFalse(k(loc("sr"), [loc("sr", "Latn")]))
        self.assertTrue(k(loc("zh", "Hant"), [loc("zh", region="TW")]))
        self.assertFalse(k(loc("zh", "Hant"), [loc("zh")]))
        self.assertFalse(k(loc("zh", region="TW"), [loc("zh")]))
        self.assertTrue(k(loc("tlh", "Latn"), [loc("tlh")]))  # script unknown -> match
        self.assertFalse(k(loc("fr"), [loc("en"), loc("de")]))
        self.assertTrue(k(loc("iw"), [loc("he")]))

    def test_reasons(self):
        r = al.drop_reason
        self.assertEqual(r(loc("de"), [loc("en")]), "language_not_listed")
        self.assertEqual(r(loc("pt", region="BR"), [loc("pt")]), "region_not_listed")
        self.assertEqual(r(loc("sr", "Latn"), [loc("sr")]), "script_mismatch")

    def test_analyse_variant(self):
        a = al.analyse_variant(["xxhdpi"], [loc("pt", region="BR")])
        self.assertEqual(a["dropped"], {})
        a = al.analyse_variant(["en", "night"], [loc("pt")])
        self.assertIsNone(a["dropped"])
        self.assertEqual(a["other"], ["night"])
        a = al.analyse_variant(["en", "pt-BR"], [loc("pt")])
        self.assertEqual(a["invalid"], ["pt-BR"])
        self.assertEqual(a["dropped"], {loc("pt"): "language_not_listed"})


class MokoTest(unittest.TestCase):
    def test_java_locale(self):
        j = al.java_locale
        self.assertEqual(j("zh-Hant"), ("zh", "Hant", ""))
        self.assertEqual(j("zh-hant-tw"), ("zh", "Hant", "TW"))
        self.assertEqual(j("pt-BR"), ("pt", "", "BR"))
        self.assertEqual(j("es-419"), ("es", "", "419"))
        self.assertEqual(j("pt_BR"), ("", "", ""))
        self.assertEqual(j("b+zh+Hant"), ("", "", ""))

    def test_moko_android(self):
        m = al.moko_android
        self.assertIsNone(m("base"))
        self.assertEqual(m("zh-rTW")[0], "values-zh-rTW")
        self.assertEqual(m("pt-rBR")[1], loc("pt", region="BR"))
        self.assertEqual(m("zh-Hant")[0], "values-zh")
        self.assertEqual(m("zh-Hant")[1], loc("zh"))
        self.assertEqual(m("zh-Hant-TW")[0], "values-zh-rTW")
        self.assertEqual(m("he")[0], "values-iw")
        self.assertEqual(m("pt_BR")[0], "values-")

    def test_findings(self):
        def e(name, android, java):
            return {"root": "r", "folder": "r/" + name, "name": name,
                    "android": android, "java": java}
        entries = [e("zh-Hans", "values-zh", ("zh", "Hans", "")),
                   e("zh-Hant", "values-zh", ("zh", "Hant", "")),
                   e("zh-Hant-TW", "values-zh-rTW", ("zh", "Hant", "TW")),
                   e("sr-Latn", "values-sr", ("sr", "Latn", "")),
                   e("pt_BR", "values-", ("", "", ""))]
        got = [(f["kind"], f.get("folder", f["android_folder"]))
               for f in al.moko_findings(entries)]
        self.assertEqual(got, [("moko_script_dropped", "r/zh-Hant"),
                               ("moko_script_dropped", "r/sr-Latn"),
                               ("moko_unparsable", "r/pt_BR"),
                               ("moko_collision", "values-zh")])
        same = [e("pt-rBR", "values-pt-rBR", ("pt", "", "BR")),
                e("pt-BR", "values-pt-rBR", ("pt", "", "BR"))]
        self.assertEqual(al.moko_findings(same), [])


class GradleTest(unittest.TestCase):
    def test_groovy(self):
        f = al.extract_filters(GROOVY)
        self.assertEqual(f["global"], ["en", "de", "pt"])
        self.assertEqual(f["flavors"], {"fdroid": ["fr"]})
        self.assertEqual(f["dynamic"], [])
        self.assertTrue(f["generate_locale_config"])
        self.assertTrue(al.is_app_module(GROOVY))
        self.assertEqual(al.variants(f), {"fdroid": ["en", "de", "pt", "fr"],
                                          "flavors without their own list": ["en", "de", "pt"]})

    def test_kotlin(self):
        f = al.extract_filters(KTS)
        self.assertEqual(f["global"], ["en", "zh-rTW", "b+sr+Latn"])
        self.assertEqual(f["flavors"], {})
        self.assertEqual(len(f["dynamic"]), 1)
        self.assertEqual(f["dynamic"][0]["scope"], "flavor:play")
        self.assertFalse(f["generate_locale_config"])
        self.assertTrue(al.is_app_module(KTS))

    def test_not_app(self):
        self.assertFalse(al.is_app_module(LIB_KTS))
        self.assertFalse(al.is_app_module(
            "plugins {\n    alias(libs.plugins.android.application) apply false\n}\n"))


class TreeCase(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.root)

    def put(self, rel, text):
        p = os.path.join(self.root, *rel.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)


class AccessorTest(TreeCase):
    def test_resolve(self):
        self.put("settings.gradle.kts", 'include(":core:ui", ":feature:some_lib")\n')
        self.put("core/ui/build.gradle.kts", LIB_KTS)
        self.put("feature/some_lib/build.gradle", "plugins { id 'com.android.library' }\n")
        r = al.resolve_accessor
        self.assertEqual(r(self.root, ["core", "ui"]), os.path.join(self.root, "core", "ui"))
        self.assertEqual(r(self.root, ["feature", "someLib"]),
                         os.path.join(self.root, "feature", "some_lib"))
        self.assertEqual(r(self.root, ["core", "ui", "dependencyProject"]),
                         os.path.join(self.root, "core", "ui"))
        self.assertIsNone(r(self.root, ["missing"]))
        self.assertIsNone(r(self.root, ["core"]))

    def test_gradle_root(self):
        self.put("android/settings.gradle", "include ':app'\n")
        self.put("android/app/build.gradle", "plugins { id 'com.android.application' }\n")
        app = os.path.join(self.root, "android", "app")
        self.assertEqual(al.gradle_root(app, self.root),
                         os.path.normpath(os.path.join(self.root, "android")))
        self.assertEqual(al.gradle_root(self.root, self.root), os.path.normpath(self.root))


class ProjectTest(TreeCase):
    def build(self):
        self.put("settings.gradle.kts", 'include(":app", ":core:ui")\n')
        self.put("app/build.gradle.kts", APP_KTS)
        self.put("app/src/main/AndroidManifest.xml", MANIFEST)
        res = "app/src/main/res/"
        self.put(res + "xml/locales_config.xml", LOCALES_CONFIG)
        self.put(res + "values/strings.xml", STRINGS % "Hello")
        self.put(res + "values-pt/strings.xml", STRINGS % "Ola")
        self.put(res + "values-pt-rBR/strings.xml", STRINGS % "Oi")
        self.put(res + "values-de/strings.xml", STRINGS % "Hallo")
        self.put(res + "values-b+zh+Hant/strings.xml", STRINGS % "Ni hao")
        self.put(res + "values-fr/colors.xml", '<resources><color name="a">#fff</color></resources>\n')
        self.put(res + "values-night/colors.xml", '<resources><color name="a">#000</color></resources>\n')
        self.put("core/ui/build.gradle.kts", LIB_KTS)
        self.put("core/ui/src/main/res/values-ja/strings.xml", STRINGS % "Konnichiwa")
        self.put("app/build/intermediates/build.gradle", "plugins { id 'com.android.application' }\n")

    def test_findings(self):
        self.build()
        rep = al.check(self.root)
        self.assertEqual([m["module"] for m in rep["modules"]], ["app"])
        mod = rep["modules"][0]
        self.assertEqual(mod["dependency_modules"], ["core/ui"])
        self.assertEqual(sorted(mod["translations"]),
                         ["b+zh+Hant", "de", "ja", "pt", "pt-rBR"])
        self.assertEqual(mod["moko"], {})
        got = [(f["kind"], f["locale"], f.get("reason")) for f in rep["findings"]]
        self.assertEqual(got, [
            ("filtered_out", "de", "language_not_listed"),
            ("filtered_out", "ja", "language_not_listed"),
            ("filtered_out", "pt-rBR", "region_not_listed"),
            ("declared_but_filtered", "de", None),
        ])
        self.assertEqual(rep["findings"][1]["folders"], ["core/ui/src/main/res/values-ja"])
        self.assertEqual(rep["findings"][3]["locale_config"],
                         "app/src/main/res/xml/locales_config.xml")
        self.assertEqual(rep["notes"], [])

    def test_exit_codes(self):
        self.build()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(al.main([self.root, "--strict"]), 1)
            self.assertEqual(al.main([self.root]), 0)
        self.assertIn("FILTERED OUT pt-rBR", out.getvalue())
        empty = tempfile.mkdtemp()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(al.main([empty, "--json"]), 2)
        finally:
            shutil.rmtree(empty)

    def test_dynamic_skips_module(self):
        self.put("app/build.gradle.kts", KTS)
        self.put("app/src/main/res/values-de/strings.xml", STRINGS % "Hallo")
        rep = al.check(self.root)
        self.assertEqual(rep["findings"], [])
        self.assertEqual([n["kind"] for n in rep["notes"]], ["dynamic_filter"])


class KmpProjectTest(TreeCase):
    MR = "shared/src/commonMain/moko-resources/"

    def build(self):
        self.put("settings.gradle.kts", 'include(":androidApp", ":shared", ":core-ui")\n')
        self.put("androidApp/build.gradle.kts", KMP_APP_KTS)
        self.put("androidApp/src/main/res/values/strings.xml", STRINGS % "Hello")
        self.put("shared/build.gradle.kts", SHARED_KTS)
        self.put(self.MR + "base/strings.xml", STRINGS % "Hello")
        self.put(self.MR + "fr-rCA/strings.xml", STRINGS % "Allo")
        self.put(self.MR + "sr-Latn/strings.xml", STRINGS % "Zdravo")
        self.put(self.MR + "zh-Hans/strings.xml", STRINGS % "Ni hao S")
        self.put(self.MR + "zh-Hant/strings.xml", STRINGS % "Ni hao T")
        self.put(self.MR + "images/logo.svg", "<svg><string/></svg>\n")
        self.put("core-ui/build.gradle.kts", LIB_KTS)
        self.put("core-ui/src/main/res/values-ja/strings.xml", STRINGS % "Konnichiwa")

    def test_moko_and_accessors(self):
        self.build()
        rep = al.check(self.root)
        self.assertEqual([m["module"] for m in rep["modules"]], ["androidApp"])
        mod = rep["modules"][0]
        self.assertEqual(mod["dependency_modules"], ["shared", "core-ui"])
        self.assertEqual(sorted(mod["translations"]), ["fr-rCA", "ja", "sr", "zh"])
        self.assertEqual(mod["translations"]["zh"],
                         [self.MR + "zh-Hans", self.MR + "zh-Hant"])
        self.assertEqual(mod["moko"][self.MR + "zh-Hant"], "values-zh")
        self.assertEqual(len(mod["moko"]), 4)
        got = [(f["kind"], f.get("locale", f.get("android_folder"))) for f in rep["findings"]]
        self.assertEqual(got, [
            ("moko_script_dropped", "values-sr"),
            ("moko_script_dropped", "values-zh"),
            ("moko_collision", "values-zh"),
            ("filtered_out", "fr-rCA"),
            ("filtered_out", "ja"),
        ])
        self.assertEqual(rep["findings"][2]["folders"],
                         [self.MR + "zh-Hans", self.MR + "zh-Hant"])
        self.assertEqual(rep["findings"][3]["folders"], [self.MR + "fr-rCA"])
        self.assertEqual(rep["findings"][0]["module"], "androidApp")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(al.main([self.root, "--strict"]), 1)
        self.assertIn("MOKO COLLISION values-zh", out.getvalue())
        self.assertIn("MOKO SCRIPT DROPPED " + self.MR + "sr-Latn", out.getvalue())

    def test_moko_needs_plugin(self):
        self.build()
        self.assertEqual(al.moko_dirs(os.path.join(self.root, "shared"), LIB_KTS), [])


if __name__ == "__main__":
    unittest.main()
