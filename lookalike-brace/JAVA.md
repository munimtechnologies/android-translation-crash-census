# lookalike-brace in Java: `｛0｝` instead of `{0}`

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0.
A follow-up to [BRACES.md](BRACES.md), which found Chinese and Japanese
translations that write `{0}` with the fullwidth braces `｛` (U+FF5B) and `｝`
(U+FF5D) in .NET `.resx`, gettext `.po` and JSON files. BRACES.md did not cover
Java, because `.properties` files usually store non-ASCII characters as
`｛` escapes, which a search for the literal `｛` does not find. This note
searches for the escaped form. It also closes two open points from BRACES.md
(ONLYOFFICE DocSpace and the upstream Watt Toolkit). As before, we **read** the
translation files and the code; we did not run any of these programs.

## What Java does with them

`java.text.MessageFormat` starts a placeholder only at the ASCII `{`:

| Translation has | Result |
|---|---|
| `｛0｝` | The value is dropped and `｛0｝` is printed |
| `｛0}` (fullwidth open, ASCII close) | The same. In OpenJDK's `MessageFormat.applyPattern`, a `}` outside a placeholder is kept as text; only an unmatched ASCII `{` throws. So unlike .NET (BRACES.md, VidCoder), nothing throws |
| `{0,choice,…}` rewritten as `｛0，选择，…｝` | The whole pattern, keyword and all, is printed as text |

Code that replaces the literal text `"{group}"` (Multiverse-Inventories below)
also finds nothing to replace.

## Confirmed in code (string is passed to a formatter)

Read on each project's default branch on 2026-10-18 (commit given where
Sourcegraph showed one). Values are shown decoded; the files store them as
`\uXXXX` escapes unless noted.

| Project | Translation | Strings | How the code formats it, and the effect |
|---|---|---|---|
| Portfolio Performance (portfolio-performance/portfolio, commit 805c20d) | zh_TW | 4 in `name.abuchen.portfolio.ui/…/ui/messages_zh_TW.properties`: `MsgSignedInAs` = `您已登入為 ｛0｝。`, `MsgRateLimitExceeded` = `｛0｝ 超出了速率限制。`, `MsgRateLimitExceededAndRetrying` (`｛0｝` and `｛1｝`), `MsgInstrumentWithConfigurationIssue` (`｛0｝`) | `label.setText(MessageFormat.format(Messages.MsgSignedInAs, claims.getEmail()))` in `LoginButton.java`; `MessageFormat.format(Messages.MsgRateLimitExceeded…, task.security.getName(), …)` and `MessageFormat.format(Messages.MsgInstrumentWithConfigurationIssue, security.getName())` in `RunTaskGroupJob.java` and `UpdatePricesJob.java`. In Traditional Chinese the sign-in label does not show the account's email, and the price-update messages do not say which security hit a rate limit or has a configuration error. |
| XWiki (xwiki/xwiki-platform, commit eadcfa1) | zh | 12 in `xwiki-platform-oldcore/…/ApplicationResources_zh.properties`. Four are whole `choice` patterns: English `extensions.info.features` = `{0,choice,0#No features\|1#Feature\|1<Features}`, Chinese = `｛0，选择，0#无功能\|1#功能\|1<功能｝` (the keyword `choice` translated as 选择, the commas fullwidth); likewise `extensions.info.components`, `…directDependencies`, `…backwardDependencies`. The other eight are invitation and office-importer messages, e.g. `xe.invitation.inspectMessages.lastEntryInfoBox` = `｛0｝，消息为：｛1｝` | `$services.localization.render('extensions.info.features', [$extension.extensionFeatures.size()])` in `templates/extension.vm`; `lastEntryInfoBox` is rendered in `Invitation/InvitationMemberActions.xml`. XWiki's English uses MessageFormat syntax (`{0,choice,…}`). On extension pages in Chinese, the label over an extension's features is the raw text `｛0，选择，0#无功能\|1#功能\|1<功能｝` (traced for this key; the other three `choice` keys were not traced). The invitation box loses both of its values. Every other language that translates the key either keeps the ASCII pattern or drops it; none rewrites it. |
| Tapdata (tapdata/tapdata, commit 4e9a3db) | zh_CN, zh_TW | 12 in `manager/tm/src/main/resources/messages_zh_CN.properties` and `messages_zh_TW.properties` (6 each; copies under `src/test/resources` not counted), e.g. `api.call.chart.time.range.too.large` = `查询范围不能超过最大查询范围：｛0｝天`, and `api.encryption.name.invalid` = `加密规则的名称已存在：｛0}` (fullwidth open, ASCII close) | `throw new BizException("api.call.chart.time.range.too.large", 365)`, `new BizException("api.encryption.name.invalid", saveEntity.getName())`, `…("module.save.check.where.tooDeep", context.getMaxDepth())`, `…("api.debug.not.support", method)`. `BizException` builds its message with `MessageUtil.getMessage(errorCode, args)`, which formats with `new MessageFormat(msg, locale).format(params)` in the request's locale. The Chinese error messages leave out the 365-day limit, the duplicate rule name, the maximum nesting depth and the unsupported HTTP method. Traced for these 4 of the 6 keys; the three `*.too.long` keys were not traced. |
| OpenCms (alkacon/opencms-core, commit 5f5e559) | zh | 7 in the `org.opencms.locale.zh` module: 5 update-XML report lines (e.g. `RPT_UPDATEXML_FILES_TO_UPDATE_1` = `更新文件的数量：｛0｝`), `GUI_UNDO_CHANGES_MULTI_2` = `撤销文件夹｛1｝中资源{0}的修改` (one placeholder ASCII, one fullwidth) and `ERR_CREATING_MESSAGES_2` | `CmsMessages` formats with `new MessageFormat(result, m_locale)`. `Messages.get().container(Messages.RPT_UPDATEXML_FILES_TO_UPDATE_1, …nrOfFiles…)` in `CmsUpdateXmlThread.java`; `setDialogTitle(Messages.GUI_UNDO_CHANGES_1, Messages.GUI_UNDO_CHANGES_MULTI_2)` in `CmsUndoChanges.java`. The Chinese update-XML report has no file counts or paths, and the multi-resource undo dialog title names the resource but not the folder. `ERR_CREATING_MESSAGES_2` was not traced. |
| Multiverse-Inventories (Multiverse/Multiverse-Inventories, commit d7a4649) | zh | `mv-inventories.deletegroup.confirmprompt` = `您确定要删除组 &f｛group｝&6 吗？` (stored as UTF-8 characters, not escapes; English `…delete group &f{group}&6?`) | `Message.of(MVInvi18n.DELETEGROUP_CONFIRMPROMPT, replace("{group}").with(group.getName()))` in `DeleteGroupCommand.java`. The Chinese confirmation asks whether to delete the group `｛group｝` without naming it. |

## The two open points from BRACES.md

- **ONLYOFFICE DocSpace.** DocSpace-server's
  `common/services/ASC.AuditTrail/AuditReportResource.ja-JP.resx` (392 entries)
  has none of the fullwidth forms that CommunityServer's `.ja.resx` still has:
  `FileDeleted` = `削除されたファイル：{0}`, `UserDeleted`, `FolderMoved` and
  `FilesDocumentSigned` all use ASCII braces. One remains:
  `UserSentActivationInstructions` = `ユーザー [{0}]。登録指導は送信された：｛１｝`.
  DocSpace's `AuditActionMapper.GetActionText` returns
  `string.Format(actionText, description)` inside a `try`, so this entry does
  not throw (its `{0}` is ASCII); the Japanese audit trail names the user but
  not who the activation instructions went to. The ~200 broken
  messages in BRACES.md are in the older ONLYOFFICE Workspace (CommunityServer).
- **Watt Toolkit.** The upstream repository (BeyondDimension/SteamTools, commit
  d042131, `src/BD.WTTS.Client/Resources/Strings.ja.resx`) has no fullwidth
  brace in any indexed file, so the `OperationHostsError_` string in
  BRACES.md's "Copies" section is only in the copy.

## Not counted

- **A reading in braces.** Pentaho Kettle and Apache Hop share a Japanese
  string `STANDARD_DEVIATION` = `標準偏差｛ひょうじゅん へんさ｝`: the
  pronunciation of the term, not a placeholder.
- **Help text that tells users what to type.** Universal G-Code Sender's
  zh_CN `mainWindow.swing.macroInstructions` lists the macro variables
  `{machine_x}` … `{prompt | name}`; four of the seven are written with
  fullwidth braces and `{work_z｝` mixes both. Nothing is dropped when the help
  is shown, but a user who copies a variable from it copies the wrong braces
  (we did not read UGS's macro code). PrisonTeam/Prison's zh-CN
  `ranks_commandCommands__command_add_cannot_use_percent_symbols` says to use
  `｛｝` instead of `%`. Both are wrong instructions, not dropped values.
- **Deliberate.** zouwei/termex writes `｛｛name:default｝｝` in its English and
  Chinese `.arb` labels alike, so the fullwidth braces there are intended.

## How we looked, and the limits

- Sourcegraph, read 2026-10-18, default scope (no forks, no archived
  repositories). `.properties` files containing `uFF5B` (case-insensitive, so it
  matches `｛` and `｛`): 57 matches; by repository, **6 repositories**
  (search completed): Pentaho Kettle, Apache Hop, Portfolio Performance, XWiki,
  Tapdata, OpenCms. `.properties` files containing the literal `｛`: 3
  repositories (Prison, Multiverse-Inventories, Universal G-Code Sender).
- Re-run of BRACES.md's searches by repository: `.resx` with `｛` gives 7
  repositories, the same five projects and two copies BRACES.md lists, so no
  `.resx` project was missed there. `.arb` gives one repository (termex,
  above).
- **Counts from Sourcegraph are a snapshot, not a census.** Searches for the
  literal fullwidth character were not stable: `.po` files with `｛` gave 6
  repositories in the run behind BRACES.md and 1, then 3, on two tries today,
  with "result limit hit" even under `count:all`. The `uFF5B` (ASCII text)
  searches agreed with each other. A clone-based count is the next step.
- "Confirmed in code" means we read the translation on the default branch and
  the call site named. We did not check which release ships each file, and we
  ran nothing. The `MessageFormat` behaviour follows from the OpenJDK source,
  not from a test.

## Prior art

Weblate's Java MessageFormat check (on by default for `.properties`) and
IntelliJ's MessageFormat inspections would report most of these as a missing
or unused placeholder, where a project uses them. Web searches in English and
Chinese found no write-up of fullwidth braces in Java translations; Chinese
articles on `MessageFormat` pitfalls cover single quotes and ASCII braces only.
The closest prior art is the same as for BRACES.md: a read-frog test that
rejects machine-translated output with `｛｛０｝｝`. The translated `choice`
keyword (选择) in XWiki is a sign of machine translation of the pattern itself,
which we have not seen described anywhere.

## Check your own Java files

    grep -rniE '\\uff5b|\\uff5d|｛|｝' --include='*.properties' .

Read every hit by hand: braces used as punctuation or around a reading also
match. The fix is to write the placeholder with ASCII braces and ASCII digits
(and, for `choice`, to restore the untranslated pattern), best done on the
project's translation platform.
