# lookalike-brace in JSON locale files: `｛0｝` and `｛label｝` in six projects

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0.
[BRACES.md](BRACES.md) and [JAVA.md](JAVA.md) showed translations that write a placeholder
with the fullwidth braces `｛` `｝` (U+FF5B, U+FF5D), so the value is never filled in. This note
asks the same of JSON locale files, the format of most web and Electron apps (i18next,
vue-i18n, react-intl, Theia/VS Code `nls`, home-made `{0}` formatters). They have it too. We
**read** the translation files and, where named, the code that formats them; we ran nothing.

Unlike the Rails YAML note ([RAILS.md](../lookalike-percent/RAILS.md)), this is a **snapshot,
not a census**: every global JSON search below stopped at Sourcegraph's match limit.

## Why it matters

Each formatter named below starts a placeholder only at an ASCII `{`. A fullwidth `｛0｝` or
`｛label｝` is plain text: nothing is thrown or logged, and the user sees the braces and the
name where a value belongs.

## Formatter read

Read on each project's default branch on 2026-10-18.

| Project | Translation | String | Formatter | What users see |
|---|---|---|---|---|
| Gloomhaven Secretariat (Lurkars/gloomhavensecretariat) | zh_Hans, zh_Hant | `battleGoals.deselect` = `取消选择｛0｝的当前战斗目标` / `取消選擇｛0｝的當前戰鬥目標` (English `Deselect current Battle Goal of {0}`) | `SettingsManager.getLabel` replaces `` `{${index}}` `` with each argument (`src/app/game/businesslogic/SettingsManager.ts`); the key is built in `battlegoal-dialog.ts` (`'battleGoals.' + (… 'select' : 'deselect')`), whose argument list we did not read | `｛0｝` instead of the character's name, in both Chinese scripts. Every other language has `{0}`. |
| CaretTab (bluecaret/carettab) | ja | `widget.windIsCurrentlyBlowing` = `風は現在｛1｝（｛2｝°）から｛0｝で吹いている。` (English `Wind is currently blowing at {0} from the {1} ({2}°).`) | vue-i18n list interpolation: `$t('widget.windIsCurrentlyBlowing', [ … ])` in `src/components/widgets/WeatherWidget.vue` | The weather widget's wind line with all three values lost: speed, direction and degrees. The other 14 languages use `{0}` `{1}` `{2}`. |
| VUEngine Studio (VUEngine/VUEngine-Studio) | ja | `taskTerminatedBySignal` = `タスク｛0｝はシグナル｛1｝により終了した。` | Eclipse Theia's `Localization.format` uses `/{([^}]+)}/g`, ASCII braces only (`packages/core/src/common/i18n/localization.ts`); the call site was not read | "Task ｛0｝ was terminated by signal ｛1｝": no task name, no signal. |
| Decrediton (decred/decrediton) | ja | `trezor.changeLabel.success` = `選択されたトレゾールに｛label｝へラベルを変更する` | react-intl (ICU message syntax, ASCII braces); the message id is used in `app/reducers/snackbar.js` | The Trezor "label changed" notice without the new label. The 10 other translations have `{label}`. |

## Seen in the translation file, formatter not read

- **aaPanel** (aaPanel/aaPanel), `BTPanel/static/vite/lang/*/index.json`: the English string ends
  `…please go to the {a}`, but Italian, German, Ukrainian, Indonesian, Turkish, Chinese and
  Traditional Chinese end `｛a｝`. The Traditional Chinese `all/cht` file also has `新增子站點-｛0｝`
  and `您確定要｛0｝群集嗎？`. If `{a}` is a link or a value filled by the app, it is lost in seven
  languages.
- **Pydio Cells** (pydio/cells), `frontend/assets/gui.ajax/res/i18n/zh-cn.all.json`: a plural
  `other` form `已开始｛startTime｝` ("started ｛startTime｝").
- **An old ONLYOFFICE copy.** sweetwisdom/onlyoffice-web-local vendors ONLYOFFICE's editors, and
  its seven Simplified Chinese `locale/zh.json` files (document, spreadsheet, presentation, PDF and
  Visio editors, desktop and mobile) have `｛0｝` in at least 17 places in the document editor alone,
  for example `Common.Controllers.ReviewChanges.textOff` = `｛0｝不再使用“跟踪更改”。` ("｛0｝ is no
  longer using Track Changes", where a user's name belongs). Upstream ONLYOFFICE/web-apps has
  `{0}` in the same strings: a regular-expression search of its `locale/*.json` files found no
  fullwidth braces. The fix exists; the copy predates it. (ONLYOFFICE's older CommunityServer
  Japanese file is in [BRACES.md](BRACES.md).)

## Not bugs

- **On purpose, in the source language.** FaserF/ha-db_infoscreen (a Home Assistant
  integration) writes `｛line｝`, `｛journeyID｝` and others in the **English** and German help text
  of its deduplication-key option. Home Assistant treats ASCII `{name}` in a translation as a
  placeholder, so fullwidth braces appear to be a deliberate way to show literal braces. A
  look-alike check should accept them when the source string has them too.
- **A look-alike percent before a real placeholder.** smolcars/blixt-wallet's Arabic
  `(٪{{defaultMaxLNFee}})` and Chrome DevTools' Persian `٪{PH1}` (two strings in `fa.json`)
  matched a search for `٪` or `％` before a brace. In i18next and ICU the ASCII `{{defaultMaxLNFee}}` / `{PH1}` is still
  filled; the `٪` is just a percent sign in front of it. In JSON formats, the percent look-alike
  that loses values in Rails YAML, gettext, Android and Qt is harmless; the brace look-alike is the
  one that matters.

## What the cases have in common

All the broken strings are Chinese or Japanese, except aaPanel's, whose fullwidth braces
appear in European-language files too and so were probably copied from a Chinese string. Wherever
we compared (Gloomhaven Secretariat, CaretTab and Decrediton across all their languages, aaPanel
against English), the same key has ASCII braces elsewhere, so a per-key comparison of placeholders across locales would catch these. This is a count of cases, **not a rate**.

## How we looked, and the limits

- Sourcegraph regular-expression searches, read 2026-10-18, default scope (no forks, no archived
  repositories), for `\x{FF5B}[\x{FF5B}{]?\w+[\x{FF5D}}]` in JSON files under `locales?/`
  (all languages and `zh|ja|ko` only), `/locale/`, `i18n/` and `/(lang|langs|translations|messages)/`
  paths. **Each one stopped at Sourcegraph's match limit** after 60 to 70 seconds, so they are
  samples. Searches scoped to the named repositories finished, with nothing skipped, and gave the
  lines quoted above.
- Searches for `[\x{FF05}\x{066A}]\s*\{\{?\w+\}` (a look-alike percent before a brace) found only
  the harmless cases under "Not bugs".
- "Formatter read" means we read the formatting code named (or, for react-intl, relied on the ICU
  message syntax) and saw the key in the code; we did not check which release ships each file.

## Prior art

Translation platforms check placeholders (for example Weblate's format checks and the
placeholder QA checks of Crowdin and Phrase). They compare ASCII placeholders, so they would
report these strings as missing a placeholder, without naming the look-alike. A web search on
2026-10-18 for fullwidth braces in i18n placeholders found no bug report or write-up about them. [l10n-guard](https://github.com/munimtechnologies/l10n-guard)
does not yet have a fullwidth-brace rule; one is planned.

## Check your own files

    grep -rnE '｛[A-Za-z0-9_]+[｝}]|\{[A-Za-z0-9_]+｝' locales/

Read every hit. If the source-language string has the same fullwidth braces, they may be there on
purpose. The fix is to replace `｛` and `｝` with ASCII `{` and `}` in the translation, best done on
the project's translation platform.
