# Results: l10n-guard 0.9.0 on three Laravel applications' translations

Graded 2026-10-18 against the predictions in [LARAVEL-PREREG.md](../LARAVEL-PREREG.md), which was
published (commit b98e757, 14:04 UTC) before the job ran (14:32-14:34 UTC). Made by MV2 of
Munim, Inc. with AI agents. Text CC BY 4.0; code Apache-2.0.

## What ran

Compute job `l10n-guard-090-v1` built l10n-guard 0.9.0 from 0.8.0 (sha256 `b80f3474...` ->
`403a9bfb...`), ran every test file (55 + 6 + 14 + 21 + 13 + 7 + 14 + 15 tests, all passing,
one skipped), and then read every translation of these files at pinned commits, each against its
source language:

| Project | Commit | Files | Source | Languages looked for | Present |
|---|---|---|---|---|---|
| Akaunting | `06dfa473` | `resources/lang/<lang>/validation.php` | en-GB (115 string keys) | 60 | 54 |
| UNIT3D | `8b88f4c8` | `lang/<lang>/{email,page,common,user,torrent}.php` | en | 62 (x5 files) | 62 |
| Snipe-IT | `d98baec3` | `resources/lang/<lang>/validation.php` | en-US (180 string keys) | 75 | 75 |

445 files were looked for, 439 were present and 434 parsed. The job's output is in
[stdout.txt](stdout.txt), unedited; the per-file table is in [laravel_files.csv](laravel_files.csv)
and every flagged string is in [laravel_eval.json](laravel_eval.json).

## Predictions

| | Prediction | Result | Value |
|---|---|---|---|
| P1 | Akaunting ja-JP: at least 15 keys, at least 18 `lookalike-colon` errors | HELD | 15 keys, 18 errors |
| P2 | UNIT3D ja: errors on exactly the six listed keys, 8 errors | HELD | the six keys, 8 errors |
| P3 | Snipe-IT zh-CN and zh-TW: errors on `required_unless` only, 2 each | HELD | 2 and 2 |
| P4 | every `lookalike-colon` error is in a Japanese or Chinese locale | HELD | none outside |
| P5 | every file present parses, and Akaunting en-GB has at least 60 string keys | **FAILED** | 5 parse errors (115 keys) |

Four held; P5 failed.

## Why P5 failed

The five files that did not parse are UNIT3D's `lang/pt_BR/{email,page,common,user,torrent}.php`.
They are not translations. All 31 files in UNIT3D's `lang/pt_BR/` folder are 6 bytes long and
identical: the PHP opening tag and nothing else (GitHub contents API at the pinned commit). There is
no array in them to read, so the reader's "no return statement in the PHP file" is the right
answer. The prediction was wrong because it assumed every file present held an array.

These stubs do not reach users as far as we can tell: UNIT3D offers only the locales listed in
`config/language.php` under `allowed`, which has `pt` but not `pt_BR`. If Laravel ever did load
one, `require` of a file with no `return` gives `1`, and Laravel's `FileLoader::loadPaths` passes
that to `array_replace_recursive`, which needs an array. We read this in the code; nothing was run.

## What it shows

- **Only in Chinese and Japanese, and not in all of them.** 191 languages are present across the
  three projects. 10 of them are Japanese or Chinese (Akaunting ja-JP, zh-CN, zh-TW; UNIT3D ja,
  zh-CN, zh-TW; Snipe-IT ja-JP, zh-CN, zh-HK, zh-TW). Four of those 10 write a placeholder with the
  fullwidth colon `：`. None of the other 181 languages do.
- **30 lost values on 23 keys.** Akaunting ja-JP 18 on 15 validation messages, UNIT3D ja 8 on six
  strings (three of them in the failed-login email: `：ip`, `：host`, `：time`), and Snipe-IT 2 in
  each Chinese `required_unless`. Each one is shown to the user as the literal text, for example
  `：attribute`, and the value is never filled in.
- **No half-fixed copies.** There were no `lookalike-colon` warnings, so no string has both the
  fullwidth form and the real ASCII `:name`.
- **The checker finds what the hand search found.** The cases in [LARAVEL.md](../LARAVEL.md) were
  found by code search and read by hand. The checker reproduced every one except
  `torrent.announce-url-desc`, which the pre-registration excluded because the English no longer
  has `:source`.

## Exploratory (not predicted)

- Snipe-IT's `zh-HK/validation.php` is byte-identical to `en-US` (same sha256), so it is an
  untranslated copy.
- `placeholder-missing` counts per language are in the CSV. Some are translated placeholder names,
  such as Snipe-IT zh-CN's `：属性` for `:attribute`, which Laravel also never replaces. 0.9.0 does
  not name these as look-alikes, and they were not counted.
- The error message prints the placeholder name lower-cased (`:actiontext` for UNIT3D's
  `:actionText`). Laravel replaces `:actionText`, `:ACTIONTEXT` and `:ActionText`; the lower-case
  name in the message is cosmetic and will be fixed in a later version.

## Limits

- Three projects found by code search. P1-P3 test the checker on known cases. P4 tested whether the
  bug spreads to other languages of the same files, and it did not, but this is not a census of
  Laravel applications.
- The verdicts come from reading the files. None of the applications was run, and call sites were
  read only for the cases in LARAVEL.md.
