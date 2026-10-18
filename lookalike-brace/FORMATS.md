# lookalike-brace across formats: Flutter `.arb`, .NET `.resx` and Java `.properties`

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text and data CC BY 4.0.
[BRACES.md](BRACES.md), [JAVA.md](JAVA.md) and [JSON.md](JSON.md) list Chinese and Japanese
translations that write a placeholder with the fullwidth braces `｛` `｝` (U+FF5B, U+FF5D), so
the value is never filled in. Those notes count cases. This one asks **how common** the problem
is, per format, wherever Sourcegraph's searches finish completely, and it starts with a format
the earlier notes never looked at: the `.arb` files of Flutter apps. We **read** translation
files and code; we ran nothing.

## Result

Searches were run on 2026-10-18 in Sourcegraph's default scope (no forks, no archived
repositories). The denominator is every repository with a Chinese or Japanese file of that format.
Every count here finished with no match limit hit.

| Format | Repositories with zh/ja files | Files | Repositories with a fullwidth-brace placeholder in a zh/ja translation | Rate |
|---|---|---|---|---|
| Flutter `.arb` (ICU) | 500 | 1,621 | **0** | 0% (95% upper bound 0.6%) |
| .NET `.resx` (`string.Format`) | 719 | 9,919 | **7** (6 without a plain copy of ONLYOFFICE) | 0.97% (0.84%) |
| Java `.properties` (`MessageFormat`) | 1,454 | not counted ¹ | **5** | 0.34% |

¹ The file list was too large to download. The repository count finished normally.

**The bug is rare in every format: under 1% of projects that ship Chinese or Japanese
translations.** Flutter's zero is **not** clearly different from the others:

- `.arb` against `.resx`: Fisher's exact test, two-sided, p = 0.046 with 7 repositories, but
  p = 0.087 once the plain copy of ONLYOFFICE CommunityServer (shr670377723/CommunityServer-master)
  is dropped.
- `.arb` against `.properties`: p > 0.2.
- `.arb` against `.resx` and `.properties` pooled (11 of 2,172): about 2.5 repositories would be
  expected in `.arb` and 0 were seen, one-sided Fisher p ≈ 0.10.

This comparison was chosen **after** we saw the `.arb` zero, across three formats, with no
correction for that. It is exploratory and does not show that Flutter apps have fewer of these bugs.
A real test would need a pre-registered plan and many more Flutter projects.

## Why the zero is not explained by Flutter's tools

We read `gen_l10n.dart` in flutter/flutter (master, 2026-10-18). The generator takes each
method's parameters from the **template** (English) placeholders. It throws only when a
translation declares a placeholder with a different type, or a date placeholder without a
format. A translation that leaves out a template placeholder gets **no warning**. To the ICU
parser a fullwidth `｛name｝` is plain text, so it would compile and show the braces and the name,
the same as in `.resx` or `.properties`. Nothing in the build would stop it.

## The cases

| Format | Project | Files | What it is |
|---|---|---|---|
| `.resx` | ONLYOFFICE/CommunityServer | 9 `*.ja.resx` | `｛0｝`/`｛1｝` in the audit trail, studio and Files resources, e.g. `作成したイベント：｛0｝` ("Created event: ｛0｝"); placeholder lines read in 5 of the 9 files (see [BRACES.md](BRACES.md)) |
| `.resx` | shr670377723/CommunityServer-master | 9 | A plain copy of the above |
| `.resx` | arkypita/LaserGRBL | 2 `*.zh-CN.resx` | `导入｛0｝个配置时出现｛1｝个错误！`, `｛0｝配置读取成功！`, `您似乎是｛0｝的幸运所有者。` |
| `.resx` | RandomEngy/VidCoder | `MiscRes.ja.resx` | see [BRACES.md](BRACES.md) |
| `.resx` | IllusionMods/KKManager | `Resources.zh-Hans.resx` | `无法打开日志文件：｛0｝` ("Cannot open log file: ｛0｝") |
| `.resx` | RayCarrot/RaymanControlPanel | `Resources.zh-Hans.resx` | `由｛0｝于｛1｝上传` ("uploaded by ｛0｝ on ｛1｝") |
| `.resx` | liushiyangFrsan/GitHub_WattToolkit | `SR.ja.resx` | `操作 hosts エラー｛0｝` ("hosts operation error ｛0｝"); a copy of Watt Toolkit, upstream not checked |
| `.properties` | tapdata, portfolio-performance, xwiki-platform, opencms-core, Multiverse-Inventories | 1 to 4 each | see [JAVA.md](JAVA.md) |

Found by the searches but **not counted**:

- **pentaho/pentaho-kettle** and its descendant **apache/hop**, `memgroupby` `messages_ja_JP.properties`:
  `標準偏差｛ひょうじゅん へんさ｝`, a reading of the term in fullwidth braces. It is not a placeholder.
- **Instruction text**, below.

## A second kind: help text that teaches the wrong braces

Three projects have messages that **tell users what to type**, with fullwidth braces where the
program reads ASCII. Nothing is lost when the message is shown. The harm comes later, when a user
types what it says.

- **Universal G-Code Sender** (winder/Universal-G-Code-Sender), `MessagesBundle_zh_CN.properties`,
  `mainWindow.swing.macroInstructions`. The Chinese macro help lists seven variables. Only
  `{machine_x}` and `{machine_y}` have ASCII braces. `｛machine_z｝`, `｛work_x｝`, `｛work_y｝` and
  `｛prompt | name｝` are fullwidth, and `{work_z｝` mixes the two. `MacroHelper.java` matches
  `Pattern.compile("\\{machine_x}")` and so on, ASCII only. A macro typed as the Chinese help shows
  would send the braces to the machine instead of the coordinates.
- **Prison** (PrisonTeam/Prison), `lang/ranks/zh-CN.properties`,
  `ranks_commandCommands__command_add_cannot_use_percent_symbols`. English says "must use { }
  instead"; Chinese says `必须改用｛｝` ("must use ｛｝ instead").
- **termex** (zouwei/termex), `app_en.arb` **and** `app_zh.arb`, `snippetContentLabel`:
  `Command (use ｛｛name:default｝｝ to insert a variable)`. This is in the source language too. It is
  probably on purpose: in an `.arb` file, `{{` would be read as a placeholder. termex's own tests
  write snippet variables as ASCII `{{host}}`. We did not read the parser, so whether a user who
  copies the hint gets a variable is untested. gen-l10n has a `use-escaping` option (off by default)
  for literal braces.

This kind of problem cannot be caught by comparing placeholders between languages: the braces are
in the text, not in a placeholder.

## How we looked, and the limits

- Denominators: `file:(^|/|[._-])(zh|ja)([._-][^/]*)?\.<ext>$` with `select:file` (`.arb`,
  `.resx`) or `select:repo` (`.properties`). The pattern catches `app_zh.arb`, `Strings.zh-CN.resx`
  and `messages_ja_JP.properties`. It misses translations kept in a `zh/` or `ja/` folder under a
  neutral name, and it counts any file whose name happens to fit.
- Numerators: `.arb`: `\x{FF5B}` and `\x{FF5D}` over **all** `.arb` files (only termex matched).
  `.resx`: `\x{FF5B}` in zh/ja `.resx` files. `.properties`: `｛` and the escaped form `uFF5B` in
  zh/ja `.properties` files. All of these finished. Two broader searches (`\x{FF5B}` in every
  `.resx`, and one regular expression for both forms in `.properties`) **hit the match limit** and
  were used only as cross-checks.
- Not checked: a closing `｝` with an ASCII `{` and no `｛` in the same file, and fullwidth
  digits (`｛０｝`) on their own. Both would be missed; both are rarer forms.
- A positive control for the `.arb` path filter (`\{count\}`) returned matches, and the `\x{FF5B}`
  search found termex, so the zero is not a broken query.
- The `.properties` and JSON rows of earlier notes were read at the call site; the new `.resx`
  lines here were read in the translation file only. Default branches as indexed on 2026-10-18.
- A repository with Chinese or Japanese files is not a fixed amount of translation: a large
  project counts once, like a small one.

## Prior art

The problem is known. Loclint's free placeholder checker (loclint.com/tools/placeholder-checker,
read 2026-10-18) warns that "a translator typing in Japanese may produce fullwidth braces that look
nearly identical and match nothing". It gives no figures, though. Web searches on 2026-10-18 found
no published rate in any format, and no report of the help-text kind. Platform checks (Weblate,
Crowdin, Phrase) compare ASCII placeholders: they catch the first kind as "missing placeholder"
without naming the cause, and they miss the second kind.

## Data

[data/formats.csv](data/formats.csv): one row per file found, with format, repository, path and
class (`placeholder`, `unread` (contains `｛`, line not read; its repository is counted from
other files), `copy`, `instruction`, `not-placeholder`).
