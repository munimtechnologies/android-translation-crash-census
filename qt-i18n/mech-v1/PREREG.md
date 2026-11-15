# PREREG: qt-mech-v1 (written 2026-11-14 ~02:00Z, before any Qt run)

Question: do the verdicts of MV2's qt-i18n desk checker (`qt_l10n.judge`, published
2026-11-13 at munimtechnologies/android-translation-crash-census, commit 37865f2) match
what a real Qt runtime does when an app loads its translation file?

Source reading (qtbase dev, qtranslator.cpp, read 2026-11-14): the string overload
`QTranslator::load(filename, directory)` tries the name as given, then cuts it at the
rightmost '_' or '.', and never changes case. The QLocale overload
`load(locale, filename, prefix, directory)` tries each `uiLanguages(Underscore)` entry as
written and then lowercased, with no cutting. `QLocale::name()` never holds a script.

## Method
- 21 codes: de pt_BR pt zh_CN zh_TW zh nb he fil es_419 sr zh_Hans zh_Hant sr_Latn pt_br
  zh_tw no tl iw pt-BR sr@latin. Each gets its own folder holding only `app_<code>.qm`,
  one message (context Mech, "Hello" -> "MV2-QT-MECH <code>").
- .qm built by lrelease if present (pyside6-lrelease, then Debian qt6-l10n-tools), else
  by qt_mech.qm_bytes. V = every file loads directly and translates to its marker.
- Styles: A = load("app_" + L.name(), dir); A2 = load("app_" + L.name().split("_")[0], dir);
  B = load(L, "app", "_", dir).
- A cell (code, style) is "reachable" if ANY locale L in
  QLocale.matchingLocales(language of the code, AnyScript, AnyTerritory) loads the file.
  The code's language is QLocale(<part before _ @ ->).language(), so no -> Bokmal,
  tl -> Filipino, iw -> Hebrew. Linux, case-sensitive file system.
- The checker predicts reachable iff judge(code, style) is None. 63 cells.

## Predictions (all from the checker; frozen by test_checker_predictions_frozen)
- V: all 21 files valid. If V fails, nothing else is graded (INVALID).
- C (controls, must hold or the run is invalid): reachable: de/A, de/A2, de/B, pt_BR/A,
  pt_BR/B, zh_CN/A, zh_CN/B.
- M1 (headline): under A, NOT reachable: zh_Hans, zh_Hant, sr_Latn (script), pt_br, zh_tw
  (case), no, tl (legacy codes).
- M2: under B, reachable: pt_br, zh_tw (the lowercase retry).
- M3: pt-BR and sr@latin NOT reachable under A, A2 or B.
- K: the checker agrees with Qt on all 57 cells outside the exploratory set E.
- E (exploratory, no prediction graded): no/B, tl/B, iw/B, zh_Hans/B, zh_Hant/B,
  sr_Latn/B. My guess (not graded): no/B, tl/B, iw/B unreachable (checker says reachable);
  zh_Hans/B and zh_Hant/B depend on whether uiLanguages() lists zh-Hans / zh-Hant alone.
- S (descriptive): with LANG=LC_ALL=xx.UTF-8, QLocale.system().name() equals
  QLocale(xx).name() for the 6 plain locales. sr_RS@latin is recorded only: if its name()
  is "sr_RS", A-style apps cannot tell Serbian Latin from Cyrillic users.
Also recorded: uiLanguages() for 13 locales, PySide6 and Qt versions, the lrelease used.

## What follows
- ALL (V, C, M1, M2, M3, K) hold: the qt-i18n README says "verified against Qt <ver>
  (PySide6) at runtime" for these rules, with the cells table. Then look for Weblate-run
  Qt apps that ship zh_Hans/pt_br/no files and load with name(): one fix PR each, paced.
- Any of M1-M3 or K fails: report it first in RESULTS.md, fix the checker (post-hoc,
  labelled), and say which published claims change.
- Any exploratory disagreement: fix judge() for style B (post-hoc, labelled), e.g. legacy
  codes under B.
- No claim about Qt resources (:/), macOS/Windows case-insensitive file systems, or Qt 5.

Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
