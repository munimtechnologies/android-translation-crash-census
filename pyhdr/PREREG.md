# Pre-registration: gettext catalogs that Python's gettext module cannot load

Marker: pyhdr census PREREG v1

Written 2026-11-10 by AI agents working for MV2 of Munim, Inc., before the job reads any
repository. Code: [pyhdr_census.py](pyhdr_census.py) and [test_pyhdr.py](test_pyhdr.py) in this
folder. Text CC BY 4.0, code Apache-2.0.

## Why

CPython's `gettext.GNUTranslations` reads a compiled catalog's header with unguarded string
splits: `v.split('charset=')[1]` for Content-Type, and `v.split(';')[1].split('plural=')[1]`
then `c2py()` for Plural-Forms. It also decodes every header line as UTF-8. When a header
breaks one of these, Python raises (IndexError, ValueError, LookupError or UnicodeDecodeError)
while it opens the language. `fallback=True` covers only a missing file, so the error reaches
the program, and itstool fails the same way.

This is known one case at a time: virt-manager's Czech file in 2011
([Red Hat 692902](https://bugzilla.redhat.com/show_bug.cgi?id=692902)), policycoreutils
([bpo 1448060](https://bugs.python.org/issue1448060)), HyperKitty's placeholder
`plural=EXPRESSION` ([MR 564](https://gitlab.com/mailman/hyperkitty/-/merge_requests/564)), and
gnome-terminal, which dropped Karbi (`mjw`) from LINGUAS in 2022 because its header
`Plural-Forms: n=2 ; ( n != 1 )` "breaks itstool". We found no count of how often shipped
catalogs carry such a header, and no linter that checks for it. Dennis's docs say it doesn't
lint Plural-Forms and point to `msgfmt --check-header`. We expect `msgfmt --check` to pass some
of these files, for example a file with no plural messages. That is not verified; the census
measures it.

## Population

- The 526 Flathub app repositories whose po folder's build reads LINGUAS (Meson or autotools),
  taken from [linguas/v1/dirs.csv](../linguas/v1/dirs.csv).
- The 291 GNOME, GNOME World, elementary and Xfce repositories of the same kind, from
  [l10n-guard-0210/repos.csv](../l10n-guard-0210/repos.csv).

Each is cloned again at HEAD (blobless, depth 1) and the commit is recorded. The job finds its
po folders the way l10n-guard 0.21.0's `linguas` kind does, using that release's own helper
functions. It skips vendored and archived folders and reads every `<locale>.po` file there,
whether `LINGUAS` lists it or not.

## Measures, per .po file

1. **Ground truth:** compile it with GNU msgfmt (plain, as Meson and gettext's autotools rules
   do), then open the result with `gettext.GNUTranslations` in CPython 3.12. A **crash** is any
   exception there.
2. `msgfmt --check` pass or fail.
3. **The rule:** `py_load_problem()`, a pure-Python reading of the `.po` text that mirrors
   CPython 3.12's `_parse` without msgfmt. It applies msgfmt's rules for which entries are kept
   (translated, and not fuzzy unless it is the header). Codes: `header-not-utf8`,
   `content-type-no-charset`, `plural-forms-syntax`, `plural-forms-expression`,
   `unknown-charset`, `text-not-in-charset`.

Before the census runs, the unit tests compare the rule with real msgfmt and CPython on 12
synthetic files (every one that msgfmt compiles, at least 6). If they fail, the census does not run.

## Predictions

- **G (gate):** at least 600 repositories are cloned and at least 10,000 `.po` files compile.
  If not, A1, A2 and P1 are NOT TESTABLE.
- **A1 (rule precision):** among compiled files the rule flags, at least 95% crash
  (20 x crashing >= 19 x flagged). NOT TESTABLE with fewer than 5 flagged files.
- **A2 (rule recall):** among compiled files that crash, the rule flags at least 95%. NOT
  TESTABLE with fewer than 5 crashing files.
- **P1 (prevalence):** at least 1 repository, and at most 5% of cloned repositories, ship a
  crashing catalog: a file that `LINGUAS` lists and that crashes.
- **H (hand check):** the job samples up to 12 repositories that ship a crashing catalog and
  contain Python files outside build, test and doc folders (one file each, seeded with the
  key "pyhdr census v1"). A sample is **real** when all three of these hold at the recorded
  commit:
  (a) the header is malformed as recorded;
  (b) the build compiles and installs the file;
  (c) the app's own Python code loads its catalog through Python's `gettext` module
  (`gettext.install`, `translation`, `gettext.gettext`, `dgettext` or the like) without
  catching the error, so a user who picks that language hits it.
  HELD if at least 10 of 12 are real. With 4 to 11 samples, HELD if 6 x real >= 5 x sampled.
  Fewer than 4 samples: NOT TESTABLE, and the cases are reported one by one.

## Reported, not predicted

Crashes by exception type and by rule code. How many crashing files pass `msgfmt --check`.
Flathub and platform repositories counted separately. Crashing files that `LINGUAS` leaves out
(gnome-terminal's `mjw.po` should be one if its header is unchanged). Listed files that
msgfmt cannot compile.

## Limits

- The ground truth is CPython 3.12. The split logic is unchanged since Python 2, but `c2py`
  differs between versions, so a few expression results may differ on other Pythons.
- Programs that use only the C library's gettext (C, Vala, Rust or GJS apps) do not crash on
  these headers. For them a finding affects tools like itstool, not the app itself. P1 counts
  catalogs, and H asks whether a Python app really loads them.
- HEAD differs from the commits of the earlier censuses, so this population is a new snapshot.

## What follows

If G, A1 and A2 hold, the rule goes into l10n-guard's `po` kind (pre-registered separately).
If H holds, confirmed cases in active projects get one-line header fixes, offered upstream at
one a day, each with the project's AI policy read first.
