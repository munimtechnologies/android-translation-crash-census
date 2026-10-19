# antonym-collision, second held-out test: pre-registration

Written and published on 2026-10-19, **before** the code below has run and
before any translation of the five projects below has been read. Made by MV2
of Munim, Inc. with AI agents; no human has checked it yet. Text CC BY 4.0;
code Apache-2.0.

## Why

l10n-guard 0.12.0's `antonym-collision` warning was [tested](GUARD-RESULTS.md)
on five projects it had never seen. It raised 19 warnings, one short of the 20
needed for the precision test, so precision was **not tested**; 13 of the 19
were graded real. All 6 that were not defects came from one of the 40 word
classes, `upload`/`download`: "Download failed" and "Upload failed" share one
value in French (*Échec du téléchargement*) or Arabic (*فشل التحميل*), where
that noun covers transfers both ways.

That pattern was seen **after** grading, so it is a hypothesis, not a result.
This test checks it, and the warning's precision, on five more projects,
with the released v0.12.0 code unchanged.

## What runs

[holdout2/eval_holdout2.py](holdout2/eval_holdout2.py) fetches
`l10n_guard.py` from the
[v0.12.0 tag](https://github.com/munimtechnologies/l10n-guard/releases/tag/v0.12.0)
(no change), then reads each project's codeload tarball of its default branch
at run time; the commit is recorded from the archive. It refuses to fetch the
guard, and so to read any translation, until this page is on main. Offline
tests: [holdout2/test_eval_holdout2.py](holdout2/test_eval_holdout2.py).

Each warning gets its **class**: the word classes whose antonyms are swapped
between the two English texts. A warning is in the UPLOAD class when every
swapped word is `upload`/`uploaded`/`download`/`downloaded`.

## Predictions

| | Prediction |
|---|---|
| H0 | All five tarballs download; each project has its English reference and at least 10 locale files that parse |
| H1 | At least 20 warnings in total, from at least 3 of the 5 projects |
| H2 | Graded by hand after the run: of a seeded sample of up to 60 warnings **outside** the UPLOAD class (seed 130, drawn from the rows sorted by project, locale, key1, key2), at least 60% of those judged are real defects. At least 20 must be judged, or H2 is "not tested" |
| H3 | Graded by hand after the run: of a seeded sample of up to 30 **UPLOAD-class** warnings (seed 131, same order), **fewer** than 50% of those judged are real defects. At least 5 must be judged, or H3 is "not tested" |
| H4 | At least 50% of the warnings have **both** keys found as a string literal in the project's own code |
| H5 | At least 50% of the UPLOAD-class warnings are in French or Arabic locales (codes starting `fr` or `ar`). At least 5 must exist, or H5 is "not tested" |

**"Real defect" (H2, H3)** is the definition in [PREREG.md](PREREG.md), as in
the first test: the shared value says one side only, so one of the two labels
says the wrong thing, or it says neither side clearly, so users cannot tell the
two apart. A value that fits both meanings well in that language is not a
defect. Each row gets `real`, `not` or `unsure` (the graders cannot read the
language with confidence); `unsure` rows are counted but left out of the
share. The grader reads only the two English texts, the shared value and,
where needed, the project's use of the keys; no other row is looked up to
decide. Share = real / (real + not). Graders are AI agents working for MV2,
not native speakers; the results will say so.

**"Used in code" (H4)** is automatic and approximate, as before: the key, or
the key with `|` for `.`, or without a plural suffix, or without a
`messages.json` `.message` suffix (Bitwarden's `{"key": {"message": ...}}`),
appears as a quoted string in a `.js .jsx .mjs .cjs .ts .tsx .vue .svelte
.dart .html .py` file of the same tarball (outside `node_modules`, files up to
2 MB). Keys built at run time are missed, so this undercounts.

## What the results decide (fixed now)

- **H3 held:** l10n-guard 0.13.0 drops the UPLOAD class from the warning's
  word list, with its own tests.
- **H3 failed or not tested:** the class stays; the results say so.
- **H2 failed:** the next l10n-guard release states the measured precision in
  its README and turns `antonym-collision` off by default (opt-in).
- **H2 held:** the warning stays on by default.
- H2 not tested: no change from H2; the results say so.

## The population (picked by layout only)

Chosen for many locales, JSON catalogs and an English reference file, from
five different translation set-ups. Only the directory listings were looked
at; none of their translations was opened before this page.

| Project | Branch | Locale files | English reference |
|---|---|---|---|
| [Jellyfin Web](https://github.com/jellyfin/jellyfin-web) | master | `src/strings/<lang>.json` | `en-us.json` |
| [Uptime Kuma](https://github.com/louislam/uptime-kuma) | master | `src/lang/<lang>.json` | `en.json` |
| [Rocket.Chat](https://github.com/RocketChat/Rocket.Chat) | develop | `packages/i18n/src/locales/<lang>.i18n.json` | `en.i18n.json` |
| [Mattermost](https://github.com/mattermost/mattermost) | master | `webapp/channels/src/i18n/<lang>.json` | `en.json` |
| [Bitwarden web vault](https://github.com/bitwarden/clients) | main | `apps/web/src/locales/<lang>/messages.json` | `en/` |

Every other English variant (`en-gb`, `en_US`, `en-AU`, `enm` and so on) is
skipped. Locale files with identical bytes (for example a language and its
regional copy) are listed in the results; their warnings are each counted, as
in the first test, and the results give the total without them.

## Limits, known now

- One commit per project, taken at run time, not before.
- The 40 word classes miss antonyms outside the list by design; this measures
  precision on what the warning flags, not recall.
- The UPLOAD-class sample may be small; under 5 judged means H3 decides
  nothing.
- No defect found here will be reported to its project until it has been
  checked again; none of the earlier ones has been reported yet.
