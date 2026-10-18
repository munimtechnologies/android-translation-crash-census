# Results: l10n-guard 0.10.0 on 150 Rails and Symfony translation files

Graded 2026-10-18 against the predictions in [YAML-PREREG.md](../YAML-PREREG.md), which was
published (commit 71c5744) more than two hours before the job ran (19:48-19:49 UTC). Made by MV2 of
Munim, Inc., with AI agents. Text and tables CC BY 4.0.

## What ran

Compute job `l10n-guard-0100-v1` built l10n-guard 0.10.0 from the 0.9.0 release by a patch script
(sha256 `403a9bfb...` -> `ce6614bf...`, 81,916 -> 106,439 bytes), ran every test file (55 + 6 + 14 +
21 + 13 + 7 + 14 + 15 + 26 = 171 tests, all passing, one skipped as always), then ran
[eval_0100.py](eval_0100.py) once, in a sealed container. The evaluation fetched the 150 translation
files listed in the pre-registration at their pinned commits (33 SonataAdminBundle XLIFF files, 28
Akeneo PIM YAML files, 20 OpenDXP YAML files, 67 GOV.UK Publishing Components YAML files, and
OpenStreetMap's `ar.yml` and `ja.yml`) and checked each against its project's source file with the new
`symfony` and `rails` kinds. All 150 were present and all 150 parsed with the built-in YAML and XLIFF
readers. The evaluation took 24 seconds.

## Predictions

| | Prediction | Result | Value |
|---|---|---|---|
| P1 | Sonata: `lookalike-percent` errors only in `ja` and `zh_CN`, only on `flash_lock_error`, 3 in each | HELD | ja 3, zh_CN 3, both on `flash_lock_error` only |
| P2 | Akeneo: the only `lookalike-percent` error is `zh_TW` `family_variant_no_axis`; `tr_TR` has a `placeholder-missing` error naming `%level%` | HELD | exactly that |
| P3 | OpenDXP: `lookalike-percent` errors only in `zh_Hans`, only on `workflow_change_email_notification_text`, 4 | HELD | 4, that key, that language |
| P4 | GOV.UK: `lookalike-percent` errors only in `ja`, 7, on exactly the six named keys | HELD | 7 errors on the six keys (`character_count.body` has two) |
| P5 | OpenStreetMap: `ar` has only warnings, on exactly three keys; `ja` has one error on `no_applications_html` | HELD | ar: 5 warnings on the three keys; ja: 1 error |
| P6 | Every `lookalike-percent` error is in a Chinese, Japanese or Arabic-script file | HELD | 19 errors; none outside |
| **P7** | Every file present parses, and every source file has at least 50 string messages | **FAILED** | 0 parse errors, but OpenDXP's source has 3 messages |

## Why P7 failed

The first half held: all 150 files parsed, including XLIFF files whose `<source>` is the key, YAML
with block scalars, and plural messages with intervals. The second half was wrong about the input,
not about the checker. OpenDXP's `bundles/CoreBundle/translations/admin.en.yaml` at the pinned commit
is three lines long: the three `workflow_change_email_notification_*` keys and nothing else. The
"at least 50 string messages" clause was written as a sanity check against a reader that silently
drops most of a file, and it was set without counting that file first. The other four sources have
126, 120, 296 and 3,175 string messages. P7 is reported as failed because that is what was written
down.

## What it shows

- **The checker finds the hand-found cases on its own, and nothing else of that kind.** Reading
  [RAILS.md](../RAILS.md) and [SYMFONY.md](../SYMFONY.md) by hand had found 19 placeholders written
  with a look-alike percent sign in these five projects, and 5 Arabic strings where the look-alike
  sits next to the real placeholder. l10n-guard 0.10.0 reports exactly those 19 as `lookalike-percent`
  errors and exactly those 5 as warnings, across all 150 translations, with no other look-alike in
  any other language.
- **By-key pairing is what makes the Symfony check work.** SonataAdminBundle's XLIFF files put the
  key, not the English, in `<source>`, so a one-file XLIFF check sees `flash_lock_error` as its own
  source and has nothing to compare. Pairing `SonataAdminBundle.ja.xliff` with
  `SonataAdminBundle.en.xliff` by key, as Symfony's translator does, finds the three lost parameters
  (`％name％`, `％link_start％`, `％link_end％`) in Japanese and Simplified Chinese.
- **Again only Chinese, Japanese and Arabic-script files.** 19 of 19 errors, in a sample where
  Chinese, Japanese, Korean and Arabic-script languages are a small minority (about 20 of the 150
  translations: Sonata ja, zh_CN, zh_HK, ar, fa; Akeneo ja_JP, ko_KR, zh_CN, zh_TW; OpenDXP ja,
  zh_Hans; GOV.UK ar, dr, fa, ja, ko, ps, ur, zh, zh-hk, zh-tw and others; OSM ar, ja). The
  [rails-rate](../../rails-rate/RESULTS.md) study, run the same evening on 1,525 translations of 69
  Rails apps, found the same.

## Exploratory (not predicted, not checked by hand)

The checker also reports ordinary problems in these files. These counts are l10n-guard's output as
written; no one has read each one, so some may be false positives, and they are listed here for the
next study, not as findings.

| Project | Source messages | Errors other than look-alikes | Of which |
|---|---|---|---|
| SonataAdminBundle (33 languages) | 126 | 148 | `placeholder-missing` 145 (bg 9, cs 7, eu 8, hr 9, hu 9, it 6, ja 9, lb 9, lt 8, pt 10, ro 8, ru 7, sk 7, sl 9, sv_SE 7, uk 8, zh_CN 9, ...), `tags` 3 |
| Akeneo PIM validators (28) | 120 | 9 | `placeholder-extra` 6, `placeholder-missing` 3 (incl. tr_TR `%Seviye%`) |
| OpenDXP admin (20) | 3 | 4 | `placeholder-missing` 1 each in es, ja, pt_br, th |
| GOV.UK components (67) | 296 | 38 | `placeholder-missing` 27, `tags` 11 |
| OpenStreetMap ar, ja | 3,175 | 14 | `placeholder-missing` 14, all in ar |

Two things in the per-file hashes are worth a look: OpenDXP's `admin.ja.yaml` and `admin.pt_br.yaml`
are byte-identical (same sha256), and its `it`, `sk` and `sv_fi` files are byte-identical to the
English, so they are untranslated copies. Sonata's `placeholder-missing` count is spread evenly over
languages that are otherwise complete, which is the shape a systematic difference (for instance in
how plural messages are paired) would have rather than translator slips; it should be read by hand
before anyone files a report.

## Limits

- Five projects found by code search. P1-P5 test the checker on known cases; P6 tests whether the
  bug spreads to the other 127 translations of the same files, and it does not. This is not a census
  of Rails or Symfony projects; the rails-rate study is the measurement over a fixed population.
- Files were read, not run. None of the five applications was started.
- The `symfony` kind reads an ASCII `%s` as a placeholder, which matters only for OpenDXP, whose
  code runs `vsprintf` on that message.
- The built-in YAML reader is a subset (no anchors, aliases, tags or flow mappings); every file here
  was within it, which is one of the things P7 tested.

## Files

- `yaml_eval.json`: per-project totals, every look-alike finding with its message, and the graded
  predictions, as written by the job.
- `yaml_files.csv`: one row per translation file (project, language, present, parsed, string
  messages, errors, warnings, look-alike counts, missing-placeholder keys, sha256 prefix).
- `stdout.txt`: the job's full output, including the per-file lines and every look-alike message.
- `eval_0100.py`: the evaluation script.

l10n-guard 0.10.0 is released at
[github.com/munimtechnologies/l10n-guard](https://github.com/munimtechnologies/l10n-guard/releases/tag/v0.10.0).
