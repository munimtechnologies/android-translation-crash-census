# lookalike-percent in gettext `.po` files: `％s` and `٪s` in six projects

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0.
[FINDINGS.md](FINDINGS.md) (Android) and [APPLE.md](APPLE.md) (iOS/macOS) showed
translations that write a placeholder with the fullwidth `％` (U+FF05) or the
Arabic percent sign `٪` (U+066A). This note asks whether gettext `.po` files,
used by C, C++, Python, PHP and JavaScript projects, do the same. They do. We
**read** the code and the translation files; we did not run any of these programs.

## Why it matters

Every formatter we looked at starts a placeholder only at the ASCII `%`
(U+0025): C `vsnprintf`, wxWidgets `wxString::Format`, PHP `sprintf`, Python's
`%` operator, and the hand-written `replace('%s', …)` loops some JavaScript
apps use. In `"٪s بايت"` the `٪s` is plain text and the value passed for it is
dropped. What the user sees depends on the language:

| Formatter | Translation has no ASCII placeholder | Example below |
|---|---|---|
| C / C++ printf family, wxWidgets | Extra arguments are ignored; the look-alike is printed | Rufus, Tenacity |
| PHP `sprintf` | Extra arguments are ignored (PHP 8 throws only when arguments are *missing*) | openmediavault |
| Python `%` with a dict (named placeholders) | No error; the string comes back unchanged | Odoo |
| Python `%` with a tuple or single value | `TypeError: not all arguments converted during string formatting` | none confirmed in this snapshot |
| JavaScript `str.replace('%s', …)`, cuerdas `fmt` | Nothing to replace; the look-alike is printed | Zettlr, Penpot |

So, unlike Android's `String.format`, most of these never crash: the value
silently disappears. Odoo has a safety net (it catches `TypeError`, `ValueError`
and `KeyError`, logs "Bad translation" and falls back to English), but a dict
applied to a string with no placeholders raises nothing, so the net never fires.

## Confirmed in code (string is passed to a formatter)

Read on each project's default branch on 2026-10-18 (Sourcegraph commit given
where it showed one).

| Project | Translation | Strings | How the code formats it |
|---|---|---|---|
| Rufus (pbatard/rufus) | ja | `MSG_134`: "Because MBR has been selected … only create a partition up to 2 TB … `%s` of disk space will be unavailable" = `"…そのため、％s のディスク容量が使用できなくなります。"`, in `res/loc/po/ja-JP.po` and in the shipped `res/loc/rufus.loc` | `lmprintf(MSG_134, SizeToHumanReadable(SelectedDrive.DiskSize - 2 * TB, FALSE, FALSE))` in `src/rufus.c`; `lmprintf` (`src/localization.c`) calls `safe_vsnprintf` with the translated text as the format (commit 3e696ab). Japanese users are warned that "％s" of disk space will be lost, without the amount. |
| Zettlr (Zettlr/Zettlr) | zh-CN | 9 live entries (one more is obsolete): the 6 settings-validation messages ("Option %s is required.", "Option %s must be one of: %s.", "…between %s and %s…" and 3 more), "Malformed Textbundle: %s", "The file/directory %s already exists in target.", "Could not check for updates: The server tried to redirect (Status code: %s)" | `trans(msgid, ...args)` in `source/common/i18n-main.ts` and `i18n-renderer.ts` replaces one ASCII `%s` per argument with `transString.replace('%s', String(a))`; with `％s` nothing is replaced. |
| Odoo (odoo/odoo) | fa | `hr_holidays`: `"%(allocation_name)s (from %(date_from)s to %(date_to)s)"` = `"٪s (از ٪s تا ٪s)"` | `self.env._("%(allocation_name)s (from …)", allocation_name=…, date_from=…, date_to=…)` in `_compute_description_validity` (`addons/hr_holidays/models/hr_leave_allocation.py`). `Environment._` passes the kwargs dict to `get_translation`, which runs `translation % args` (`odoo/tools/translate.py`, commit eaef8b21). Persian users see the literal `٪s (از ٪s تا ٪s)` as a time-off allocation's validity, with no name or dates. |
| Penpot (penpot/penpot) | ar | 2: `dashboard.export-binary-multi` = `"تنزيل ملفات ٪s Penpot (.penpot)"`; `errors.webhooks.unexpected-status` = `"حالة غير متوقعة٪ s"` | `(tr "dashboard.export-binary-multi" file-count)` in `frontend/src/app/main/ui/dashboard/file_menu.cljs`; `tr` formats with cuerdas `str/fmt` (`frontend/src/app/util/i18n.cljs`, commit b633093). The second call site (`dashboard/team.cljs`) was not read. |
| openmediavault (openmediavault/openmediavault) | ar_SA | 5 storage-device descriptions: `"%s [on %s, %s]"`, `"Block layer cache [%s, %s]"`, `"Device Mapper %s [%s, %s]"`, `"LVM logical volume %s [%s, %s]"`, `"Loop device [%s, %s]"`, e.g. `"٪s [على ٪s ، ٪s]"` | e.g. `return sprintf(gettext("Loop device [%s, %s]"), $this->getDeviceFile(), binary_format($this->getSize()));` in `StorageDeviceLoop::getDescription()` (commit e5ca09e9). Device path and size are dropped from the description. |
| Tenacity (tenacityteam/tenacity) | ar | `"%s bytes"` = `"٪s بايت"` (flagged `c-format`) | `XO("%s bytes").Format( ToDisplayString(size) )` in `Internat::FormatSize` (`libraries/lib-strings/Internat.cpp`, commit ea6a9f50), used for sizes under 1 KB only. |

## Why no check caught them

GNU `msgfmt --check-format` compares the placeholders of msgid and msgstr, but
only for entries that carry a format flag (`#, c-format`, `python-format`,
`php-format`, …) and only when the build passes `-c`. In this sample:

- Odoo, Penpot and openmediavault entries carry **no format flag**, so no
  gettext check looks at them.
- Tenacity's entry is flagged `c-format`, but its build runs
  `${msgfmt} -o "${mo}" "${po}"` (`locale/CMakeLists.txt`), without `-c`.
- Zettlr's entries are flagged `javascript-format`; we did not check whether
  any step of its build validates them.
- Rufus converts the `.po` into its own `rufus.loc` format; we found no
  placeholder check in its loader.

## Not counted

- **Fuzzy entries.** Sugar (sugarlabs/sugar) has 7 Persian entries with `٪s`
  ("Checking %s...", "Error: %s", …), but all are `#, fuzzy, python-format`, so
  msgfmt leaves them out and users get English. Any checker should skip fuzzy
  and obsolete (`#~`) entries; Zettlr's tenth hit and two Pootle/Zing hits are
  obsolete.
- **Help text about tokens.** Remmina's Persian and Arabic help strings
  translate "%h is substituted with the server name" (and `%t`, `%u`, `%U`,
  `%p`, `%g`, `%d`) as `٪h`, `٪t`, …, so users are told to type a character
  Remmina will not substitute. That is a documentation error, not a dropped
  value; we did not check whether Remmina's `%Y … %S` date string in the same
  files is passed to a date formatter.
- **Copies.** The Freemius SDK's Japanese file (2 strings) appears in two
  plugins that vendor it; a test fixture in wpscan copies a plugin's `ja_JP.po`;
  a CVE proof-of-concept repository copies a plugin's Urdu file.

## Seen in files, call sites not checked

WordPress plugins and themes (PHP `sprintf`, so the value would be dropped):
H5P (ar, 3, two inside `<a href="٪s">`, which would leave a broken link),
Nav Menu Roles (fa, 2), Responsive (ar, 1), Avada (ar, 1), StartBox (ja, 3),
WooCommerce PayPal Express Checkout copy in shadowsocks/shadow-shop (ja, 1).
Others: Odoo HR fork CybroOdoo/OpenHRMS (ar_001, 2), OTRS Community Edition
fork (fa, 1), Pandemonium engine (ar, 2), Ushahidi (zh_CN, 2), OrbisGIS (zh,
`％S`), Play My Music (zh, 1), Sky Chart (zh_CN, 1), Jorani (zh, 1),
luci-in-docker (zh_Hant, 1), dpviz (ja, 1), pqR, a fork of R (zh_CN, 4, plus 3
positional `％1$d`/`％2$s` in `parallel`).

## How we looked, and the limits

- Sourcegraph searches, read 2026-10-18, default scope (no forks, no archived
  repositories), `.po` files only: `٪s` 42 matches / 14 repositories; `％s` 50 /
  17; `٪d` 6 / 1 (Remmina); positional `(％|٪)n$[sd]` 3 / 1; named
  `(％|٪)(name)[sd]` 0. Every one of these reported a match or time limit, so
  they are a snapshot, **not a census**. A search scoped to upstream R
  (wch/r-source) returned nothing, but we did not confirm that repository is
  indexed; Godot's editor translations (godot-editor-l10n) were not indexed.
- "Confirmed in code" means we read the translation on the default branch and
  the call site named above. We did not check which release ships each file,
  and we ran nothing.
- The Python `TypeError` row in the first table is how Python's `%` operator
  behaves; we found no project in this snapshot where a look-alike reaches it.

## Prior art

Large placeholder audits of gettext projects exist (apache/superset #44551
counts 1,198 mismatched translations; genropy/genropy #1451 lists mangled
`% S` forms), and generic checks would report these strings as a missing
placeholder (pofilter's printf test; Weblate and `msgfmt -c` when a format flag
is set). None of these names the look-alike percent sign. The Qt form (`％n`) is covered by miguelaguiar01/corpus #1003; the
Android and Apple forms are in [FINDINGS.md](FINDINGS.md), [LINT.md](LINT.md)
and [APPLE.md](APPLE.md). We found no write-up on look-alikes in `.po` files.

## Check your own files

    grep -rnE '(％|٪) ?(\([A-Za-z_]+\))?([0-9]+\$)?[0-9.]*l{0,2}[sdiuxXfc]' --include='*.po' . | grep -v ':#~'

Read every hit by hand: Latin text right after a percent sign (`50٪ discount`)
also matches, and fuzzy entries are harmless. The fix is to replace the
look-alike with the ASCII `%` in the translation, which is best done on the
project's translation platform.
