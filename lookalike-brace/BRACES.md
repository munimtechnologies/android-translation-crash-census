# lookalike-brace: `｛0｝` instead of `{0}` in nine projects

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0.
[FINDINGS.md](../lookalike-percent/FINDINGS.md),
[APPLE.md](../lookalike-percent/APPLE.md) and
[GETTEXT.md](../lookalike-percent/GETTEXT.md) showed translations that write a
`%` placeholder with a look-alike percent sign. This note asks the same
question for **brace** placeholders (`{0}`, `{name}`, `{{name}}`): do
translations write them with the fullwidth braces `｛` (U+FF5B) and `｝`
(U+FF5D)? They do, in .NET `.resx`, gettext `.po` and JSON files. Every case we
found is Chinese or Japanese, where an input method in full-width mode types
these braces. We **read** the code and the translation files; we did not run
any of these programs.

## Why it matters

Every formatter below starts a placeholder only at the ASCII `{` (U+007B) and
ends it only at the ASCII `}` (U+007D):

| Formatter | Translation has `｛0｝` | Translation has `｛0}` (one side only) |
|---|---|---|
| .NET `string.Format` | Value dropped, `｛0｝` printed | `FormatException`: a lone ASCII `}` is a format error (VidCoder) |
| Python `str.format` | Value dropped, `｛0｝` printed | `ValueError: Single '}' encountered` |
| ngx-translate `{{name}}`, Servarr `translate()`, jfa-go `template()` | Value dropped, placeholder printed | Value dropped |
| Code that searches for the literal `"{0}"` | `IndexOf` returns -1 (Rayman Control Panel throws) | same |

So the usual effect is silent: the user sees `｛0｝` where a file name, a count
or a link should be. Two cases below throw instead.

## Confirmed in code (string is passed to a formatter)

Read on each project's default branch on 2026-10-18 (commit given where
Sourcegraph showed one).

| Project | Translation | Strings | How the code formats it, and the effect |
|---|---|---|---|
| ONLYOFFICE Workspace Community Server (ONLYOFFICE/CommunityServer, last commit 2026-05-05 "Update to v12.8") | ja | about 200 audit-trail messages in `module/ASC.AuditTrail/AuditReportResource.ja.resx` (Sourcegraph counts 246 fullwidth `｛` in the file), mostly with fullwidth digits too: `FileDeleted` = `"削除されたファイル：｛０｝"`, `UserDeleted` = `"削除されたユーザー：｛０｝"`, `FilesDocumentSigned` = `"｛1｝文書は｛0｝で署名された"`; some mix both, e.g. `FolderMoved` = `"フォルダ[{0}]。フォルダ：｛１｝に移動されました。"` | `MessageMaps.GetActionText()` reads the text with `AuditReportResource.ResourceManager.GetString(...)`, and `AuditActionMapper.GetActionText` returns `string.Format(actionText, description)` (`module/ASC.AuditTrail/Mappers/`, commit fe1fa7b). In Japanese, the audit trail says *a file was deleted* without saying which file, user, project or document. |
| VidCoder (RandomEngy/VidCoder) | ja | `EncodeCompleteWarning_SleepMessage` = `"｛0}秒後にスリープになります"` (fullwidth open, ASCII close) | `string.Format(CultureInfo.CurrentCulture, messageFormat, this.secondsRemaining)` in the `Message` getter of `ShutdownWarningWindowViewModel.cs`, no try/catch (commit 6894f76). The lone `}` makes `string.Format` throw `FormatException` every time the countdown ticks. The window reads `Message` through a WPF binding (`Text="{Binding Message}"`), which normally catches getter exceptions, so the likely effect is an empty sleep warning rather than a crash. |
| Rayman Control Panel (RayCarrot/RaymanControlPanel) | zh-Hans | `ModLoader_GameBanana_UploadInfo` ("Uploaded by {0} on {1}") = `"由｛0｝于｛1｝上传"` | `GameBananaDownloadableModViewModel.cs` splits the text at the literal `"{0}"`: `str.Substring(0, str.IndexOf("{0}", …))`. With no ASCII `{0}`, `IndexOf` returns -1 and `Substring(0, -1)` throws `ArgumentOutOfRangeException` (commit 6826d8b). We did not trace whether a caller catches it. |
| LaserGRBL (arkypita/LaserGRBL) | zh-CN | 4: `BoxImportConfigWithError` = `"导入｛0｝个配置时出现｛1｝个错误！"`, `BoxWriteConfigWithError` = `"｛0｝配置写入时出现｛1｝个错误！"`, `BoxReadConfigSuccess` = `"｛0｝配置读取成功！"`, and the Ortur Wi-Fi prompt `"您似乎是｛0｝的幸运所有者。…"` | `String.Format(...)` in `GrblConfig.cs` (lines 105, 145, 150) and `String.Format(LblPrompt.Text, core.GrblVersion?.MachineName)` in `OrturWiFiConfigPrompt.cs`. The GRBL configuration dialogs lose the setting and error counts; the prompt loses the machine name. The sibling strings in the same file use ASCII `{0}`. |
| KKManager (IllusionMods/KKManager) | zh-Hans | `OpenGameLogFailedMessage` = `"无法打开日志文件：｛0｝…"` | `MessageBox.Show(string.Format(Resources.OpenGameLogFailedMessage, exception.Message), …)` in `InstallDirectoryHelper.cs` (commit 7a7e266). The error box drops the actual error. |
| Extract ISBN calibre plugin (kiwidude68/calibre_plugins) | zh_CN | `"Could not find an ISBN for {0} book(s)."` = `"找不到｛0｝书籍的ISBN。 "` (not fuzzy) | `_('Could not find an ISBN for {0} book(s).').format(len(failed_ids))` in `extract_isbn/action.py`. The count of books is dropped. |
| OWASP Juice Shop (juice-shop/juice-shop) | zh_TW | `NFT_SBT_BOX_TEXT` ("Find the Juice Shop SBT on {{link}}.") = `"好哇！ 在｛｛link｝｝上找到果汁店SBT。…"` | `[innerHTML]="'NFT_SBT_BOX_TEXT' \| translate: i18nParams"` in `nft-unlock.component.html` (commit 399fba7); ngx-translate fills only ASCII `{{…}}`. The link is replaced by the text `｛｛link｝｝`. |
| Whisparr (Whisparr/Whisparr) | zh_CN | 2: `MarkAsFailedConfirmation` = `"是否确实要将“｛sourceTitle｝”标记为失败？"`, `ProgressBarProgress` = `"进度栏位于｛Progress｝%"` | `translation.replace(/\{([a-z0-9]+?)\}/gi, …)` in `frontend/src/Utilities/String/translate.ts` (commit c55fdc6). The confirmation does not name the release being marked as failed. The same search over every indexed Servarr-style `Localization/Core/*.json` (Sonarr, Radarr, Lidarr, Prowlarr, …) found only these two. |
| jfa-go (hrfee/jfa-go) | zh-hant | Telegram/Discord `languageSet` ("Language set to {language}.") = `"語言設置為｛Language｝。"` | `Strings.template("languageSet", tmpl{"language": …})` in `discord.go`; `templateString` in `lang.go` starts a placeholder only at the byte `'{'` (commit 2f5e51b). The bot replies with the placeholder instead of the language name. (The key's capital `L` would not match `language` either.) |

## Not counted

- **Set or JSON notation, not placeholders.** Scilab's zh_CN graphics messages
  write a set as `｛%s｝`; the `%s` is ASCII and still filled. Klipper's
  Simplified Chinese documentation shows JSON examples with fullwidth braces;
  that is a documentation error, not a dropped value.
- **A stray extra brace.** PKP (pkp-lib) Japanese `grid.po` has
  `「 ｛{$oldUsername}」`: the ASCII `{$oldUsername}` is still filled; the
  extra `｛` is only a visible typo.
- **Copies.** `shr670377723/CommunityServer-master` repeats ONLYOFFICE's file;
  `liushiyangFrsan/GitHub_WattToolkit` has `OperationHostsError_` =
  `"操作 hosts エラー｛0｝"` in `SR.ja.resx`, but we did not confirm that the
  upstream project (Watt Toolkit) still ships it.

## How we looked, and the limits

- Sourcegraph searches, read 2026-10-18, default scope (no forks, no archived
  repositories): `.resx` `｛0｝` 39 matches / 6 repositories (limit hit);
  `.resx` `｛` + ASCII or fullwidth digit, excluding CommunityServer, 11 / 5
  (completed); `.resx` `｛0}` 1 (VidCoder), `{0｝` 0 (limit hit); `.po` `｛`
  10 / 6 (limit hit); `.json` `｛｛` 1 (Juice Shop, limit hit); `.json`, `.arb`,
  `.xlf`, `.xliff` `｛name｝` 3 / 2 (limit hit); `.properties` `｛0｝` 0 (limit
  hit); YAML `%｛` 0 (limit hit). Searches that hit a limit are a snapshot,
  **not a census**.
- Java `.properties` files usually store non-ASCII as `｛` escapes. We did
  not search for the escaped form, so Java `MessageFormat` is not covered.
- "Confirmed in code" means we read the translation on the default branch and
  the call site named above. We did not check which release ships each file,
  and we ran nothing. The WPF and `Substring` effects follow from the documented
  behaviour of those APIs, not from a test.

## Prior art

Generic checks would report most of these as a missing placeholder (Weblate's
C# and Python brace-format checks, `msgfmt -c` with `python-brace-format`)
where the project enables them. The browser extension read-frog
(mengxi-ream/read-frog) has a test that rejects machine-translated output in
which placeholders came back as `｛｛０｝｝`, so its authors have seen the
pattern from machine translation. Searches in English, Japanese and Chinese
found no write-up of fullwidth-brace placeholders in shipped translations.
The percent-sign form is covered by [FINDINGS.md](../lookalike-percent/FINDINGS.md),
[APPLE.md](../lookalike-percent/APPLE.md) and
[GETTEXT.md](../lookalike-percent/GETTEXT.md).

## Check your own files

    grep -rnE '｛[0-9０-９A-Za-z_{｛$]|[0-9０-９A-Za-z_]｝' --include='*.resx' --include='*.po' --include='*.json' --include='*.arb' --include='*.xlf' .

Read every hit by hand: braces used as punctuation also match. The fix is to
replace the fullwidth braces (and any fullwidth digits inside them) with ASCII
in the translation, which is best done on the project's translation platform.
