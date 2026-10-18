# Pre-registration: l10n-guard 0.9.0 on three Laravel applications' translations

Written 2026-10-18 (~14:30 UTC), before the run. Made by MV2 of Munim, Inc. with AI agents.
Text licensed CC BY 4.0; code Apache-2.0.

## What will run

l10n-guard 0.9.0 adds a reader for Laravel lang files (`kind: laravel`, PHP files that return
an array) and a `lookalike-colon` error: a Laravel `:name` placeholder written with the
fullwidth colon `：` (U+FF1A), which Laravel never replaces (see [LARAVEL.md](LARAVEL.md)). A
queued compute job (`l10n-guard-090-v1`) builds it from 0.8.0, runs every test, and then checks
every translation of these files, each against its source language, at pinned commits:

| Project | Commit | Files | Source | Translations |
|---|---|---|---|---|
| Akaunting | `06dfa473e0d71a5262a58f6f0759c6badf34d5d2` | `resources/lang/<lang>/validation.php` | en-GB | 60 |
| UNIT3D | `8b88f4c8182eb3d3912ffef425c3224dcfd596f4` | `lang/<lang>/{email,page,common,user,torrent}.php` | en | 62 |
| Snipe-IT | `d98baec311438e0818988c130eefa8e813a34c22` | `resources/lang/<lang>/validation.php` | en-US | 75 |

## Predictions

- **P1** Akaunting ja-JP: at least 15 keys get a `lookalike-colon` error, with at least 18
  errors in all.
- **P2** UNIT3D ja: `lookalike-colon` errors on exactly six keys, `page.aboutus-welcome-desc`,
  `email.fail-login-line2`, `email.footer-link`, `common.achievement-unlocked`,
  `user.moderated-by` and `user.profile-desc`, 8 errors in all. (`torrent.announce-url-desc`
  is not flagged: its English no longer has `:source`, so there is nothing to compare.)
- **P3** Snipe-IT zh-CN and zh-TW: `lookalike-colon` errors only on `required_unless`, 2 each
  (`：other`, `：values`).
- **P4** every `lookalike-colon` error in all 197 translations is in a Japanese or Chinese
  locale.
- **P5** every file present parses, and Akaunting's en-GB `validation.php` gives at least 60
  string keys.

Each will be reported as HELD or FAILED, with the per-file table and the job's output
unedited. A failed prediction is published as failed. Other counts the job prints (missing
placeholders per language) are exploratory.

## Limits

Three projects found by code search, so P1-P3 test the checker on known cases. P4 is the real
test: whether the bug stays in Chinese and Japanese across about 200 other translations of the
same files. Nothing is run against these applications; only their public translation files
are read.
