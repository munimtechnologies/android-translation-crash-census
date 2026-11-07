# Results: Android translation folders whose text is not in the folder's language

Marker: locale-mismatch RESULTS v1 (correction 2026-11-07, see "Corrections" at the end)

Graded on 2026-11-06 against the [pre-registration](PREREG.md) (marker `locale-mismatch PREREG v1`,
SHA-256 `0393f3fd2e94afc7770ed364a28eb03ad727220aba66af58aad7125dd5416b59`, recorded by the job
before it read any repository). Made with AI agents by MV2 of Munim, Inc. Code:
[locale_mismatch.py](locale_mismatch.py) and [test_locale_mismatch.py](test_locale_mismatch.py)
(Apache-2.0); data: [folders.csv](folders.csv), [sample.csv](sample.csv), [labels.csv](labels.csv),
[summary.json](summary.json), [repos.jsonl](repos.jsonl) (CC BY 4.0).

## Verdicts (unchanged from the job and the hand check)

Gate: 4,588 of 4,693 repositories read (at least 4,000 needed): **passed**. 2,386 of them ship
Android translations (56,285 translation folders, 19,299 of them in a language the script rules
check). The built-in control and the self-test (NewPipe 110 folders, F-Droid client 101) passed.

| | Prediction | Result | Verdict |
|---|---|---|---|
| L1 | L1 folders in at least 5 repositories | 107 folders in **32** repositories | **HELD** |
| L2 | at least 3/4 of the hand-checked sample is `defect` | **26 of 32** (24 needed) | **HELD** |
| L3 | not-a-language folders in at least 5 repositories | 45 folders in **29** repositories | **HELD** |
| L4 | in at least half of the L3 repositories a code is found nowhere in the code | **19 of 29** | **HELD** |

Four of four predictions held.

**Known case:** FreezeYou's `values-ru-rUA` was read and flagged (`cyrillic-letters`), as
expected. It is sample row 15 (Ukrainian text, `defect`).

**Borderline labels:** 7 of 32 (rows 3, 9, 11, 12, 25, 26, 29). With every one flipped, L2 has
31 of 32 `defect` and still holds.

## What the flagged folders really are (read this before quoting L2)

L2 held, but most of its defects are not what the study was built to find. Split of the 32
sample rows by the language the text is really in (post-hoc, not pre-registered):

| What the folder holds | Rows | Label |
|---|---:|---|
| English, the app's source language, left in the folder | **22** | defect |
| A translation into another language (Welsh, Ukrainian, Czech, German) | **4** | defect |
| The right language written in Latin letters (Kazakh x2, romanized Hindi x2, Macedonian, romanized Pashto) | 6 | fine |

- **So the honest reading is:** when a folder's script doesn't match its language, the people who
  speak that language almost never get it (26 of 32). Usually, though, that is because the folder
  holds untranslated English, not because a whole translation landed in the wrong folder (4 of 32,
  12.5%). The English strings are counted because they differ from the default text: English
  plural forms the default lacks (Arabic, Belarusian and Hebrew need more), older wordings, or
  quoted copies. Phones fall back to the default English for missing strings anyway, so these
  English folders show users roughly what they would see without them.
- **Latin script is not a mistake by itself.** All six `fine` rows are deliberate Latin-script
  writing of the right language. Kazakh has an official Latin alphabet (2021); the other four are
  romanizations. A lint warning based on script alone needs a way to say "this is intended".

## A whole module in the wrong languages: Thunderbird for Android

Sample row 5 led to the largest real case. In Thunderbird for Android's message-list module
(`feature/mail/message/list/internal/src/main/res`, checked at `main` on 2026-11-06), eight
translation folders hold the archive-folder setup strings in another language:

| Folder | Should be | Text is in | Found by |
|---|---|---|---|
| `values-am` | Amharic | Corsican | script rules |
| `values-ar` | Arabic | Welsh | script rules (sample row 5) |
| `values-ast` | Asturian | Hungarian | hand check |
| `values-az` | Azerbaijani | Italian | hand check |
| `values-be` | Belarusian | Japanese | script rules |
| `values-bg` | Bulgarian | Lithuanian | script rules |
| `values-bn` | Bengali | Romanian | script rules |
| `values-br` | Breton | Turkish (its last three strings are Breton) | hand check |

Each of those eight languages also has its own folder in the same module (`values-co`, `-cy`,
`-hu`, `-it`, `-ja`, `-lt`, `-ro`, `-tr`). We read `values-co` and `values-cy`, which hold the
current Corsican and Welsh. The misplaced files hold 11 to 23 strings, while the complete
translations we read (co, cs, el, fa, in) hold 32, so they look like older copies that stopped
being updated. The module's history goes back to a split on 4 December 2025 (`a3e3f10`) and,
before it, a Weblate commit on 5 November 2025 (`f485c25`). We did not trace where the
misplacement began. We read 27 of the
module's 73 locale folders by hand. The 8 above are wrong, 8 are right (brh, co, cs, cy, el, eo,
fa, in) and 11 are empty. The other 46 were not checked. Three of the eight are in Latin script
where the folder's language is also written in Latin letters (Asturian, Azerbaijani, Breton),
so no script rule can see them. This is the clearest example of the limit below: the counts here
are lower bounds.

## Not-a-language folder names (L3, L4)

45 folders in 29 repositories use a code that is not a language. By code (folders):
`qq` 17, `cn` 7, `cz` 4, `ua` 3, `by` 2, `dk` 2, `zz` 2, and one each of `du`, `gr`, `hn`, `jp`,
`me`, `ns`, `ry`, `sp`.

- **Deliberate, not mistakes (post-hoc):** `qq` is the translatewiki.net convention for message
  documentation (MAXS, Wikisayit, Commons, Wikipedia), and `zz` is input data for a keyboard
  build tool (klavesnice, Indic Keyboard). Without these 6 repositories, L4 is 17 of 23, so it
  still holds.
- **Real slips that no phone selects:** country codes used as language codes. Examples are
  `values-cn` for Chinese (zh), `values-cz` for Czech (cs), `values-ua` for Ukrainian (uk),
  `values-by` for Belarusian (be), `values-dk` for Danish (da), `values-gr` for Greek (el),
  `values-sp` for Spanish (es), `values-du` holding German (de) and `values-jp` for Japanese
  (ja). Hand checks at the recorded commits: Exodus has `values-cn` (67 strings) and no
  `values-zh*` folder; kraigsandroid's alarm clock (`klock`) and Karma Firewall have `values-ua` and no
  `values-uk`; OpenPods has `values-cz` and no `values-cs`. In klock, Karma Firewall and OpenPods
  the translation ships and no system language setting selects it. Exodus is different; see
  "Corrections" below.
- **Referenced codes:** 10 of the 29 repositories mention their code somewhere in the code, so
  an in-app language picker may still reach it (for example `values-jp` in mako, `values-ua` in
  Orion Viewer, `values-cn` in CineLog, ProExpense and ANOTHERpass).
- **Limit:** Magisk's `values-hn` (romanized Hindi) is counted as unreferenced, but an in-app
  picker that lists the app's resource locales at run time would reach it, and a text search
  can't see that. We did not check.
- Glucosio's `values-me-rME`, `values-ns-rZA` and `values-ry-rUA` hold the same 11 English
  strings as its 27 Latin-flagged folders, which looks like an automatic export of empty
  languages.

## Exploratory (not graded)

- **Region tags:** 60 of the 107 flagged folders (56%) carry a region (`-rSA`, `-rBY`), against
  4,613 of 19,299 checked folders (23.9%).
- **Concentration:** two repositories hold 49 of the 107 flagged folders: Glucosio 27 and Open
  Food Facts 22.
- **Flag types:** 105 `latin`, 1 `cyrillic-letters` (FreezeYou) and 1 `wrong-script:Kana`
  (Thunderbird's Japanese in `values-be`). There were no `ja-no-kana` or `zh-kana` folders.
- **Rate:** 107 of 19,299 checked folders (0.55%), in 32 of 2,386 repositories with translations
  (1.3%).

## Limits

- Hand labels are by AI agents working in MV2's name, not native speakers. The verdict holds with
  every borderline label flipped.
- Script rules can't see a wrong language in the same script (Thunderbird's Hungarian in
  `values-ast`), and the Cyrillic letter rule covers only ru, uk and be. Every count is a lower
  bound.
- The code search is textual. A code built at run time is missed, and an unrelated `"cn"` counts
  as a reference. It also does not see a locale list that the build tool generates from the
  resource folders (Android Gradle Plugin's `generateLocaleConfig`); see "Corrections".
- One commit per repository (HEAD on 2026-11-06); F-Droid apps only. 105 repositories could not
  be cloned. 5 resource files did not parse.
- Data note: `sample.csv` is the job's file, unchanged. The hand labels are in `labels.csv`,
  joined on `sample`.

## What happens next

- As pre-registered, L2 held, so l10n-guard gets a warning for folders whose text is mostly in
  another script. It will name the two common causes (untranslated English; a deliberate Latin
  script) so a maintainer can tell them apart. It will be built and tested in a job, not by hand.
- Real cases go on MV2's paced list of upstream reports, at most one outward action a day, each
  only where the project's rules allow it and each saying it was made with AI agents. Thunderbird
  comes first.

## Corrections

**2026-11-07.** The first version of this file said of Exodus, klock, Karma Firewall and OpenPods:
"In these four apps the translation ships and no system language setting ever shows it." That was
wrong for Exodus. Its `app/build.gradle.kts` sets `generateLocaleConfig = true` (checked on
`master`, 2026-11-07), so the Android Gradle Plugin builds the app's list of supported languages
from its resource folders, and that list is what Android 13 and later offer in the per-app
language setting. `values-cn` can therefore end up in that list as the code `cn`, not as
Chinese. We have not checked a built APK or a phone, so whether and how `cn` is shown there is
not confirmed. A user who picks it gets the Chinese strings; a user whose phone is set to Chinese
still does not. The verdicts do not change: L4 counts code references, and Exodus was counted as
having none, which stays true of its source code.

The other three were checked the same day: klock (`android/alarmclock/klock/build.gradle`),
Karma Firewall and OpenPods (`app/build.gradle`) have no `generateLocaleConfig`, no
`resConfigs` and no `android:localeConfig` in their manifests, so the original sentence stands
for them. We did not check the other repositories in L3 for generated locale lists.
