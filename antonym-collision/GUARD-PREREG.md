# An antonym-collision warning for l10n-guard: pre-registration

Written and published on 2026-10-19, **before** the code below has run and
before any file of the five new projects has been read. Made by MV2 of
Munim, Inc. with AI agents; no human has checked it yet. Text CC BY 4.0;
code Apache-2.0.

## Why

The [scan](RESULTS.md) of NocoBase and Mastodon found that the pre-registered
rule picks out few strings (under 3 per 1,000 comparisons), but in a hand
reading all 19 NocoBase instances were real defects, and 14 of them are labels
users see. That is precise enough to try as a warning in
[l10n-guard](https://github.com/munimtechnologies/l10n-guard), MV2's
open-source translation checker. Before shipping it, this page fixes what the
warning must do on files it has never seen.

Searches on 2026-10-19 found no tool or lint rule that warns on this shape.
The closest is Weblate's "Reused translation" check (`reused`: "different
strings are translated the same"). It flags every pair of different sources
that share a translation, most of them harmless ("Name" and "Title" both
translated "Nom"). The i18n linters we looked at (eslint-plugin-i18n-json,
i18next-cli, i18n-lint) check keys, placeholders and untranslated strings,
not meaning. The rule here keeps only pairs whose sources say opposite
things.

## The warning (l10n-guard 0.12.0, code `antonym-collision`)

- Two keys of one JSON or `.arb` catalog whose source texts differ only by
  an odd number of antonym swaps from the 40 word classes fixed in
  [PREREG.md](PREREG.md) (`expand`/`collapse`, `mute`/`unmute`,
  `before`/`after`, `required`/`optional` and so on). Inflections of one side
  (`Expand`/`Expanded`) are not a pair.
- Their translations are the same non-empty string after trimming spaces.
- That string is not either source text (ignoring case); a copy is left to
  the existing untranslated check.
- One warning per pair, on the first key, naming the other key. It is a
  warning, not an error: nothing crashes, and antonyms outside the word list
  (`Visible`/`Hidden`) are missed by design.

It runs in `check_catalog`, so it covers the `json` and `arb` kinds and the
JSON files of `dir`. Code: [guard-0120/patch_0120.py](guard-0120/patch_0120.py)
builds 0.12.0 from 0.11.0 on main.

## Predictions

| | Prediction |
|---|---|
| G0 | All seven codeload tarballs download (the two below and the five new projects); each new project has its English reference and at least 10 locale files that parse |
| G1 | The patch applies to 0.11.0 on main; the ten test files on main pass **unchanged**; the unit cases U1-U10 in [test_0120.py](guard-0120/test_0120.py) pass |
| G2 | On NocoBase @10810697 and Mastodon @cab53a59, read the way the scan read them, the guard's warnings are **exactly** the 27 flagged rows of the published [collisions.csv](collisions.csv) (same directory, locale, key1, key2) |
| G3 | On the five new projects, at least 20 warnings in total, from at least 3 of the 5 projects |
| G4 | Graded by hand after the run: of a seeded sample of up to 60 warnings on the new projects (seed 120, drawn from the rows sorted by project, group, locale, key1, key2), at least 60% of those judged are real defects. At least 20 must be judged, or G4 is "not tested" |
| G5 | At least 50% of the new projects' warnings have **both** keys found as a string literal in the project's own code |

The unit cases (U1-U10): flagged: NocoBase de-DE's two "Default
collapse"/"Default expanded" keys both "Standardmäßig eingeklappt"; Mastodon
it's `video.mute`/`video.unmute` both "Muta"; values that differ only in
leading or trailing spaces; "Show"/"Hide"/"Hidden" all "Masquer" (two
warnings: Hide and Hidden are one side); the same in an `.arb` file; the `json`
command prints it and `--strict` fails on it. Not flagged: different
translations; a copy of an English text (also in other case); an empty or
missing value; "Show before"/"Hide after" (two swaps); "Expand"/"Expanded";
"Visible"/"Hidden"; "Show all"/"Hide".

**"Real defect" (G4)** is the definition in [PREREG.md](PREREG.md): the shared
value says one side only, so one of the two labels says the wrong thing, or
it says neither side clearly, so users cannot tell the two apart. A value
that fits both meanings well (a single toggle word that really covers both
states in that language) is not a defect. Languages the graders cannot read
with confidence are marked unsure and left out of the share, but counted.

**"Used in code" (G5)** is automatic and approximate: the key, or the key
with `|` for `.` (Element's `_t("action|mute")`), or without a plural suffix,
or as `namespace:key`, appears as a quoted string in a `.js .jsx .mjs .cjs
.ts .tsx .vue .svelte .dart .html .py` file of the same tarball (outside
`node_modules`, files up to 2 MB). Keys built at run time
(`` t(`toolbar.${name}`) ``) are missed, so this undercounts. G4 asks whether
a label is wrong; G5 asks whether the program names the keys; the scan showed
the two can differ (5 of its 19 had no use found).

## The new population (pinned before reading)

Chosen for many locales, JSON catalogs, an English reference file, and a mix
of translation set-ups. They were picked by layout only; none of their
translations was opened before this page.

| Project | Commit | Locale files | English reference |
|---|---|---|---|
| [Excalidraw](https://github.com/excalidraw/excalidraw) | e1b7aacb | `packages/excalidraw/locales/<lang>.json` | `en.json` |
| [Immich](https://github.com/immich-app/immich) | 53618ff7 | `i18n/<lang>.json` | `en.json` |
| [Lobe Chat](https://github.com/lobehub/lobe-chat) | 5310a6f1 | `locales/<lang>/<namespace>.json` | `en-US/` |
| [Element Web](https://github.com/element-hq/element-web) | fc4d45cc | `apps/web/src/i18n/strings/<lang>.json` | `en_EN.json` |
| [Jitsi Meet](https://github.com/jitsi/jitsi-meet) | f4a1c17e | `lang/main-<lang>.json` | `main.json` |

Other English variants (Immich's `en_GB`) are skipped. Full commits and
the path patterns are in [guard-0120/eval_0120.py](guard-0120/eval_0120.py).
Jitsi's `main-nb.json` and `main-no.json` are identical files at this
commit, so any warning in one is counted twice; the results will say so.

## What happens next

The build job runs the offline tests of the evaluation first, then the
patch, every test file, and the evaluation. The results page will grade
G0-G5 as written here, failures included. 0.12.0 is released only if G1 and
G2 hold; if G4 fails, the warning is not released at all, and the results say
why.
