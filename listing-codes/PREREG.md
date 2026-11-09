# Pre-registration: store-listing language keys in F-Droid's index that no phone can select

listing-codes census PREREG v1. Written 2026-11-09, before the job that reads any index ran.
Made with AI agents by MV2 of Munim, Inc. Code: Apache-2.0. Text and data: CC BY 4.0.

## Question

F-Droid apps translate their store listings (name, short and full description, changelogs,
screenshots) in folders named after a locale: `fastlane/metadata/android/<locale>/`,
`metadata/<appid>/<locale>/` in fdroiddata, or Triple-T's `src/main/play/listings/<locale>/`.
How many of the locale keys that F-Droid actually publishes are not language tags that a phone
can ever ask for, which mistakes are they, and do the apps lose those translations?

## Why it matters, and what is already known

- fdroidserver (`fdroidserver/update.py`, `insert_localized_app_metadata`, read 2026-11-09) finds
  locale folders with a glob that only wants two lowercase letters first (`[a-z][a-z]*`) and uses
  the folder name as the key with no check or normalisation. A stricter `LANG_CODE` regex exists,
  but only the iOS path uses it. `fdroid lint` has a `LOCALE_PATTERN`, but only for folders inside
  fdroiddata's `metadata/<appid>/`, and it never checks fastlane folders.
- The F-Droid client (`libs/index/.../org/fdroid/LocaleChooser.kt`, `getBestLocale`, read
  2026-11-09) picks the key that matches the phone's languages: the full tag, then
  script/region combinations, then the bare language, then the first key with the same language
  and script; failing that it shows `en-US`, then `en`, then the first entry. A key whose
  language part is not a language (`jp`, `cn`, `cz`, `ua`) is never chosen for a phone language;
  it can only be shown as the last fallback, when a field has no `en-US`/`en` text, or when it is
  the field's only key.
- Prior art: F-Droid's issuebot has an open idea to validate fastlane/Triple-T locale names
  (gitlab.com/fdroid/issuebot issue 30, examples `pt-rBR`, `zh-rCN`), with no count. The
  `validate-fastlane-supply-metadata` GitHub Action checks a project's own folders against
  Google Play's list. NewPipe once renamed its folders ("Use BCP47 language codes for fastlane").
  We found no count of invalid keys across a published F-Droid index.
- Our Android baseline (locale-mismatch census, 2026-11-06): 26 `values-` folders with a
  non-language code in 23 of 2,386 repositories (about 1%).

## Data and method (fixed now)

- `listing_codes.py` 0.1.0 (this folder). It downloads the IANA Language Subtag Registry and,
  only after this file is public (marker line above), `https://f-droid.org/repo/index-v2.json`
  (graded) and `https://apt.izzysoft.de/fdroid/repo/index-v2.json` (IzzyOnDroid, exploratory
  only). The sha256 of each download and the index timestamp are recorded.
- Keys read: every locale key of `name`, `summary`, `description`, `video`, `icon`,
  `featureGraphic`, `promoGraphic`, `tvBanner`, every `screenshots.<kind>`, and `whatsNew` of every
  version. A package's keys are the union over its fields.
- Each key gets one class, in this order: `valid` (well-formed per RFC 5646, every subtag in the
  registry, case-insensitive, deprecated subtags such as `iw` included; grandfathered and private
  use tags count as valid); `android-r` (`zh-rCN`, `b+sr+Latn`); `underscore` (valid if `_`
  becomes `-`); `unregistered-language` (well-formed, the language subtag is not registered);
  `unregistered-subtag` (language registered, a script, region, variant or extlang is not:
  `ja-JA`, `en-UK`); `malformed` (anything else). "Invalid" means any class but `valid`.
- Meant language: for `unregistered-language`, the fixed list l10n-guard already uses
  (cn->zh, cz->cs, ua->uk, jp->ja, by->be, dk->da, gr->el, sp->es, du->nl, vn->vi, al->sq,
  ir->fa, il->he, hk->zh, us->en, gb->en, pk->ur, ge->ka, mx->es, rs->sr, kz->kk); for
  `android-r` and `underscore`, the language part. "Lost" = the package has no valid key with
  that language (iw/in/ji/jw/mo folded to he/id/yi/jv/ro).
- Before reading any index, the script must classify 18 control keys correctly against the
  live registry (en-US, zh-Hans-CN, pt-BR, iw-IL, es-419, sr-Latn, fil, ckb, de-CH-1996 valid;
  jp, cn unregistered-language; zh-rCN, b+sr+Latn android-r; pt_BR, zh_Hant underscore; ja-JA
  unregistered-subtag; zh-CN.UTF-8 malformed; kr valid, because Kanuri is a language). After
  reading, F-Droid's own client package must show at least 10 description keys including
  en-US. Either failure stops the job.

## Gate

At least 3,000 packages in F-Droid's index and at least 8,000 language subtags in the registry;
otherwise every prediction is NOT TESTABLE.

## Predictions (F-Droid index only; integer arithmetic)

- **K1.** The packages with at least one invalid key are between 0.5% and 6.0% of all packages
  (5 * packages <= 1000 * invalid <= 60 * packages).
- **K2.** At least 8 packages have an `unregistered-language` key.
- **K3.** Of the packages with an `unregistered-language` key whose meant language is on the list,
  at least half have lost it (no valid key for that language). Needs at least 4 such packages,
  otherwise NOT TESTABLE.
- **K4.** `android-r` is the most common invalid class: more packages have an `android-r` key than
  have a key of any other invalid class (a tie fails).
- **H1 (hand check).** A sample drawn by the script: for each package with an `android-r`,
  `underscore` or `unregistered-language` key, the one with the lowest
  sha256("listing-codes v1|<package>|<key>"), then the first 20 by that hash. For each row, a
  reader labels the key's text (`description`, else `summary`, else `whatsNew`, else `name`, as
  printed by the job) `translation` (text in a language other than English, not identical to
  the en-US text), `english`, `empty` or `other`. HELD if translation * 4 >= 3 * checked, with
  at least 8 checked; otherwise FAILED or NOT TESTABLE. The labels are published as labels.csv
  next to the job's unchanged outputs.

## Exploratory (reported, not graded)

Invalid keys by name and count; how each invalid key is reached (`only-key`: the field's only
key, shown to everyone; `fallback-en`: the field has en-US/en, so the key is shown to nobody
whose language it was meant for; `no-en`); `unregistered-language` keys whose text equals the
en-US text; registered codes often used for another language (`kr` Kanuri for Korean, `se`
Northern Sami for Swedish, `ee` Ewe for Estonian, `ch` Chamorro), with counts only; valid keys
in non-canonical case (`pt-br`); the same tables for IzzyOnDroid. Every key F-Droid publishes,
with its class and package count, is written to `fdroid-all-keys.csv` (CC BY 4.0).

## Limits stated in advance

- The index shows what F-Droid publishes, not where each key came from (fastlane, Triple-T or
  fdroiddata); a hand check reads the upstream folder only for cases that are reported upstream.
- `android-r`, `underscore` and `unregistered-subtag` keys may still be reached through the
  client's language-prefix fallback; only `unregistered-language` keys are claimed to be
  unreachable by phone language. The client's matching was read in its source, not run.
- Other F-Droid clients (Droid-ify, Neo Store) and the f-droid.org website pick keys their own
  way; they are not tested.
- Results are reported whatever they are; borderline and hand-label disagreements are listed.
