# lookalike-percent in Rails-style YAML: `％{name}` and `٪ {name}` in eleven projects

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0.
[FINDINGS.md](FINDINGS.md) (Android), [APPLE.md](APPLE.md) and [GETTEXT.md](GETTEXT.md)
showed translations that write a placeholder with the fullwidth `％` (U+FF05) or the
Arabic percent sign `٪` (U+066A). This note asks the same of the YAML locale files used
by Ruby on Rails (`config/locales/*.yml`) and by JavaScript libraries that copy their
`%{name}` syntax. They do it too. We **read** the translation files and the code that
calls them; we did not run any of these programs.

## Why it matters

Ruby's I18n gem fills a value only where the text has `%{name}` (or `%<name>s`)
with an ASCII `%` (`DEFAULT_INTERPOLATION_PATTERNS` in `lib/i18n/interpolate/ruby.rb`).
`％{name}`, `٪{name}` and `٪ {name}` are plain text to it. When a string has no
placeholder that matches, `interpolate_hash` returns the text unchanged and ignores the
values passed in, so nothing is raised and nothing is logged: the user sees `％{link}`
where a link or a number belongs. A check that compares placeholders across locales
would report them as missing; Rails itself never will.

## Confirmed in code (the key is called with the value that is lost)

Read on each project's default branch on 2026-10-18.

| Project | Translation | Strings | Call site | What users see |
|---|---|---|---|---|
| GOV.UK Publishing Components (alphagov/govuk_publishing_components) | ja | 6 strings, 7 placeholders: `common.toggle_more` = `さらに ％{number}` (English `%{show} %{number} more`); `character_count.body` = `最大 ％{number} ％{type} を入力できます`; `cookie_banner.confirmation_message.html` = `いつでも ％{link} できます。`; `attachment.page.other` = `％{count}ページ`; `article_schema.scoped_search_description` = `％{title}内で検索`; `organisation_schema.all_content_search_description` = `％{organisation} からすべてのコンテンツを検索` | `t("components.character_count.body", number: …, type: …)` in `_character_count.html.erb`; `t("components.attachment.page", count: attachment.number_of_pages)` in `_attachment.html.erb` and `_attachment_link.html.erb`; `t("common.toggle_more", show: …, number: remaining.length)` in `metadata/_sentence.html.erb`; `I18n.t(:scoped_search_description, …, title: page.title)` and `I18n.t(:all_content_search_description, …, organisation: page.title)` in the machine-readable schema presenters; the cookie banner's `raw(t("components.cookie_banner.confirmation_message.html", …))` with `t("components.cookie_banner.confirmation_message.link")` on the next lines (the full argument list was not read). | On a Japanese page: a form's character limit without the number or the unit, an attachment's page count as `％{count}ページ`, and, after accepting cookies, `いつでも ％{link} できます。` without the "change your cookie settings" link. The two schema strings go into search-engine metadata rather than the page. |
| OpenStreetMap website (openstreetmap/openstreetmap-website, translations from translatewiki.net) | ar | 3 strings: `site.about.heading_html` = `٪ {copyright} OpenStreetMap٪ {br} من المساهمين%{copyright}%{br}`; `site.copyright.native.html` = `… إلى %{native_link}٪ {native_link} من هذه الصفحة …`; `site.copyright.legal_babble.contributors_fi_credit_html` starts `٪ {finland}:` and ends `ضمن٪ {nlsfi_license_link}.%{finland}%{nlsfi_license_link}` | `t ".heading_html", :copyright => tag.span(t(".copyright_symbol_html")), …` in `app/views/site/about.html.erb`; `:native_link => link_to(t(".native.native_link"), …)` and `t ".legal_babble.contributors_fi_credit_html", …` in `app/views/site/copyright.html.erb` (commit 855cda76) | Each string also has the ASCII placeholders, so the values do appear, but next to or after literal `٪ {…}` text: the About page heading reads `٪ {copyright} OpenStreetMap٪ {br} من المساهمين` followed by the © sign and a line break; the Finnish data credit has the link after the full stop, after the literal `٪ {finland}` and `٪ {nlsfi_license_link}`. |
| OpenStreetMap website | ja | `oauth2_authorized_applications.index.no_applications_html` = `％{oauth2}アプリケーションをまだ承認していません。` | `t ".no_applications_html", :oauth2 => link_to(t(".oauth_2"), "https://oauth.net/2/")` in `app/views/oauth2_authorized_applications/index.html.erb` | "You have not yet authorized any ％{oauth2} applications", without the "OAuth 2" link. |
| Wiki Education Dashboard (WikiEducationFoundation/WikiEduDashboard, translations from translatewiki.net) | sd (Sindhi) | `application.no_results` = `'٪{query}' لاءِ ڪي بہ نتيجا نه مليا` | `I18n.t('application.no_results', { query: search })` in `searchable_course_list.jsx`, `campaign_list.jsx` and `AddWizardBlock.jsx` (commit 94bc3468) | "No results for '٪{query}'" without the search term, if the JavaScript i18n library, like Ruby's, starts a placeholder only at an ASCII `%{` or `{{` (we did not check its version). |

## Seen in the translation file, call site not checked

All Rails I18n unless noted; each is the only look-alike in its file unless a count is given.

- **Samvera Hyrax** (samvera/hyrax), zh: `hyrax.transfers.new.sr_only_description` = `选择要转让 “％{work_title}” 的用户…`, a screen-reader-only description, so the work's title is lost to screen-reader users.
- **Sharetribe Go** (sharetribe/sharetribe), ja: `paypal_accounts.new.something_went_wrong` ends `もしこのまま問題が続く場合％{service_name} チームまでお問い合わせください。` (the marketplace's name). The same file's `%{commission}％` and `%{stripe_commission} ％` are fine: there the fullwidth sign is a real percent sign after the value.
- **Comfortable Mexican Sofa** (comfy/comfortable-mexican-sofa), ar: all four plural forms of `comfy.admin.cms.revisions.sidebar.revision` (`one`, `few`, `many`, `other`) are `٪ {count} …`, so the revision count is never shown.
- **NEMO** (thecartercenter/nemo), ar_EG: `sms.timestamp_with_diff_html` = `٪ {time} <br/> (٪ أرسلت {time_diff} في وقت سابق)`: both values lost, and in the second a word sits between `٪` and `{time_diff}`.
- **Camaleon CMS** (owen2345/camaleon-cms), Simplified Chinese (`zh-CH.yml`, root key `zh-CN`): `camaleon_cms.admin.custom_field.fields.image_thumb_descr` ends `默认值：％{d}` (the default thumbnail size).
- **Tip4commit** (tip4commit/tip4commit), ja: `projects.show.contribute_and_earn_description` has `％{make_commits_link}` and `％{branch}`.
- **Wiki Education Dashboard**, sd: `application.search_results` = `' نتيجن لاءِ: ''٪ {search_terms}'''`. The views ask for `application.search_results.one` and `.other`, and the Sindhi file has a plain string there, so this one probably never reaches users.
- **makrio** (makrio/makrio, a diaspora* fork), ur-PK: `aspects.create.success` = `آپکا نیا پہلو ٪ {name} تشکیل دے دیا گیا`.
- **Fluidd** (fluidd-core/fluidd), zh-HK, vue-i18n not Rails: `app.general.error.app_warnings_found` = `'％{appName} 出現警告。'`. vue-i18n also reads a bare `{appName}`, and the same file uses that form elsewhere, so the name is probably still shown, after a stray `％`. Cosmetic at most; not tested.

## What the eleven have in common

- **Only Arabic-script and CJK files.** A search over every indexed `locales/*.yml` file, in
  every language, found 12 files in 11 repositories. All 12 are Arabic (3), Urdu, Sindhi,
  Japanese (4) or Chinese (3). That fits the way these scripts are typed (Persian keyboard
  layouts, for example, have `٪`, and Chinese and Japanese input methods type `％` in
  full-width mode), but without per-language totals it is a count of cases, **not a rate**.
- **A space after `٪`, never after `％`.** Every Arabic-script file has at least one
  `٪ {name}` with a space; no Chinese or Japanese one does. The same spaced form, `٪ n`,
  appears in Arabic Qt translations ([qt-numerus](../qt-numerus/FINDINGS.md)). We make no
  claim about who or what wrote these strings.
- **A check satisfied, users not.** In OpenStreetMap's Arabic strings the ASCII
  placeholders are there as well, after the look-alikes, so any check that only asks
  whether `%{copyright}` and `%{br}` are present passes, while users still see
  `٪ {copyright}` and `٪ {br}` as text.

## How we looked, and the limits

- Sourcegraph regular-expression searches, read 2026-10-18, default scope (no forks, no
  archived repositories): `[\x{FF05}\x{066A}\x{FE6A}]\s*\{\w+\}` in files matching
  `locales/.*\.ya?ml$` returned 12 files in 11 repositories, with the search reported as
  finished and its counts as exhaustive; the same pattern limited to `zh|ja|ar|fa|ko|ur`
  paths returned the same files less the Sindhi one (25 matched lines in 10 repositories).
  Each file was then read in full from its default branch. Without the `locales/` path
  filter the search hit Sourcegraph's time limit, so YAML outside a `locales/` folder is
  not covered.
- Fullwidth braces (`%｛name｝`, `％｛name｝`, `%{name｝`) in the same files: 0 matches.
- A search scoped to 20 large Rails applications (Mastodon, Discourse, diaspora*, Forem,
  OpenProject, Redmine, Chatwoot, Canvas LMS, Decidim, CONSUL, Loomio, Zammad, Solidus,
  Spree and others) and another to 24 Rails projects and locale gems (rails-i18n,
  devise-i18n, Active Admin, Administrate, GitLab, Hyrax, OpenStreetMap, GOV.UK Whitehall,
  Open Food Network, the Archive of Our Own and others) found only the Hyrax, Sharetribe
  and OpenStreetMap strings above.
- "Confirmed in code" means we read the translation and the call site named; we did not
  check which release or deployment serves each file, and we ran nothing.

## Prior art

Placeholder-consistency checks for Rails YAML exist and would report these strings as a
missing `%{name}`: i18n-tasks' `check-consistent-interpolations` (its pattern is built on
the ASCII `%{`), a proposed RuboCop YAML cop (scarver2/rubocop-yaml #25), and per-project
specs such as 24pullrequests #5086. None of them names the look-alike percent sign, and we
found no write-up on look-alikes in Rails locale files (English web searches,
2026-10-18). The other formats are covered in [FINDINGS.md](FINDINGS.md),
[APPLE.md](APPLE.md), [GETTEXT.md](GETTEXT.md) and
[../lookalike-brace/BRACES.md](../lookalike-brace/BRACES.md).

## Check your own files

    grep -rnE '(％|٪|﹪) ?\{[A-Za-z_]+\}' config/locales

Read every hit: in `%{value}％` the fullwidth sign is a real percent sign after the value
and is fine. The fix is to replace the look-alike, and any space after it, with the ASCII
`%` in the translation, best done on the project's translation platform.
