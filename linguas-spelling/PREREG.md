# Pre-registration: translations built under a name gettext never looks up

Marker: linguas-spelling census PREREG v1. Written 2026-11-12 before the job runs; no repository
of the population has been read for this question. Made with AI agents by MV2 of Munim, Inc.
Text CC BY 4.0; code (linguas_spelling.py, test_linguas_spelling.py, fetch_lc.py) Apache-2.0.

## Question

Meson's `i18n.gettext()` and gettext's autotools rules compile every language listed in
`po/LINGUAS` and install `<name>.mo` as `share/locale/<name>/LC_MESSAGES/<domain>.mo`, using the
listed name unchanged. glibc's and Python's gettext look a catalog up under names built from the
user's locale: `lang_TERRITORY.codeset`, `lang_TERRITORY`, `lang.codeset`, `lang` (plus
`@modifier` forms), with the territory in upper case and `_` as the separator. So a language
listed as `zh_cn`, `pt-BR` or `nb-no` is compiled and installed, but a user whose locale is
`zh_CN.UTF-8`, `pt_BR.UTF-8` or `nb_NO.UTF-8` never gets it (Linux file systems are
case-sensitive). How often do Flathub apps' source repositories ship a translation this way?

The mechanism itself is tested separately, in a sealed run with real glibc and Python:
l10n-guard 0.22.0's pre-registration, predictions M1 and M2 (`l10n-guard-0220/PREREG.md` in this
repository). If M1 or M2 fails, the counts below are still reported, but the claim that these
catalogs are never loaded is withdrawn.

## Population

The 526 repositories that linguas census v1 (`linguas/`, run 2026-11-09) found with a governed
LINGUAS directory (a Meson or autotools build that reads `LINGUAS`) and read without error: rows
of `linguas/v1/repos.csv` with `governed=yes` and `status=ok`, de-duplicated without regard to
case. Each is read again at its current default-branch HEAD (blobless depth-1 clone), with the
same v1 code (`linguas/linguas_census.py`, fetched unchanged) for finding LINGUAS directories,
reading LINGUAS the way Meson or gettext's po.m4 does, and telling the build kind.

## What is counted

For each governed directory, each listed name that has a `<name>.po` file next to it (so the
build compiles it) is classed:

- ok: `lang[_TERRITORY][@modifier]` with a 2-3 letter lower-case language, `_`, and a 2-letter
  upper-case or 3-digit territory (`de`, `pt_BR`, `es_419`, `sr@latin`).
- script: a title-case 4-letter script subtag (`zh_Hans`, `sr_Latn`). Not counted here; these
  are the subject of the separate linguas-script census.
- misspelled: the same shape with the wrong case or a `-` separator (`zh_cn`, `pt-BR`, `pt_br`,
  `nb-no`, `DE`). The proposed name is the ok spelling (`zh_CN`, `pt_BR`, `nb_NO`, `de`).
- other: anything else (`de_FORM`, `en_US_POSIX`, `zh_CN.UTF-8`, `zh_hans`). Reported only.

A misspelled name is shadowed when its proposed spelling is also listed (the language still
ships under the right name); shadowed names are reported but do not count. A repository is
flagged when a governed directory has at least one misspelled, non-shadowed name.

## Predictions (fixed before any population repository is read)

- G (gate): at least 480 repositories read without error, and at least 450 of them still have a
  governed LINGUAS directory. If G fails, P1-P3 are not testable.
- P1: the flagged share of the repositories with a governed LINGUAS directory is between 0.5%
  and 5% inclusive. (Our guess: the problem is real but rare. 0 or 1 flagged repository fails
  P1 on the low side; that would mean the new l10n-guard warning targets a rare case.)
- P2: at least half of the flagged names are Chinese or Portuguese (proposed language `zh` or
  `pt`). Not testable with fewer than 4 flagged names.
- P3: no repository whose Flathub listing says it is translated on l10n.gnome.org (Damned Lies)
  is flagged. Not testable with fewer than 20 such repositories.
- H (hand check): up to 12 flagged repositories (sorted by a SHA-256 key of the repository URL,
  one name each, the job writes them to `sample.csv`) are checked by hand on the forge at the
  recorded commit: LINGUAS lists the name, `<name>.po` exists next to it, the build reads that
  LINGUAS, and the app does not set up its own lookup that would find the name. H holds if at
  least 90% are confirmed; not testable with fewer than 4.

Unit tests (`test_linguas_spelling.py`) and a control run first: GNOME Calculator's `po/LINGUAS`
must list at least 30 languages with none flagged, or the job stops before reading anything.

## Cases seen before this pre-registration

DeimosHall/Metamorphosis (commit 813da90) and adhami3310/Switcheroo (commit 8f773bb) have
`po/zh_cn.po`, but it is NOT listed in LINGUAS (found by linguas census v1), so neither counts
as flagged unless it has since been listed. No listed misspelled name is known to us.

## Limits

One snapshot of one population (apps on Flathub whose repositories our v1 code could read);
not all Linux software. Apps that call `setlocale`/`bindtextdomain` and also set `LANGUAGE`
themselves, or that bundle their own lookup, can still load a misspelled catalog; the hand
check looks for that but cannot rule it out everywhere. A user can also set `LANGUAGE=zh_cn` by
hand. Results are published unchanged, negatives first, with deviations stated.

## What it is for

If P1 holds and H confirms, the cases back l10n-guard 0.22.0's `linguas-spelling` warning and
become one-line fix pull requests (rename the .po and the LINGUAS entry), one a day, with AI
disclosed.
