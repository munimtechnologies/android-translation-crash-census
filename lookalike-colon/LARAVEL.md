# Look-alike colons in Laravel translations: `：attribute` for `:attribute`

Made by MV2 of Munim, Inc. with AI agents, 2026-10-18. Text CC BY 4.0. A snapshot from code
search and reading files, not a census; nothing was run against any of these applications.

## The bug

Laravel writes translation placeholders as a colon and a name: `:attribute`, `:name`, `:time`.
`Illuminate\Translation\Translator::makeReplacements` builds its search keys as
`':'.$key`, `':'.Str::ucfirst($key)` and `':'.Str::upper($key)` and swaps them in with `strtr`.
Validation messages are filled separately, by
`Illuminate\Validation\Concerns\FormatsMessages`, whose `replaceAttributePlaceholder` calls
`str_replace` on `':attribute'`, `':ATTRIBUTE'` and `':Attribute'`; the rule-specific replacers
(`:other`, `:values`, `:size`) live in `ReplacesAttributes` and were not read. Only the ASCII
colon (U+003A) is searched for in the code that was read. A translation that writes the placeholder with the
fullwidth colon `：` (U+FF1A), which Chinese and Japanese input methods type and which the
surrounding text often uses as punctuation, is printed as written. The user sees `：attribute`
and the value is lost. Nothing throws and nothing is logged.

This is the same family as the look-alike percent signs ([lookalike-percent/](../lookalike-percent/FINDINGS.md),
`٪s`, `％d`) and fullwidth braces ([lookalike-brace/](../lookalike-brace/BRACES.md), `｛０｝`) in
this repository, in a fourth placeholder syntax.

## Cases (files read in full on 2026-10-18, default branches)

| Project | Stars | File | Keys | Placeholders written with `：` |
|---|---|---|---|---|
| [Akaunting](https://github.com/akaunting/akaunting) (accounting) | 10.2k | `resources/lang/ja-JP/validation.php` | 15 | 18 |
| [UNIT3D](https://github.com/HDInnovations/UNIT3D) (tracker software) | 2.4k | `lang/ja/{email,page,common,user,torrent}.php` | 7 | 9 |
| [Snipe-IT](https://github.com/grokability/snipe-it) (asset management) | 15.0k | `resources/lang/zh-CN/validation.php`, `zh-TW/validation.php` | 1 each | 2 each |

**Akaunting, Japanese validation messages.** 15 of the 65 standard rule messages use `：attribute`
(the other 50 use `:attribute`), among them `required`, `email`, `unique`, `url`, `file`, `image`
and `integer`. Three also carry a second one: `：other` (`different`), `：values` (`ends_with`,
written `：：values`) and `：size` (`size.string`). Laravel's validator always passes `attribute`,
so a Japanese user who leaves a required field empty is told
`The：attributeフィールドは必須です。` (with the `<strong>` markup around 必須) instead of the field's name. The
same lines carry other machine-translation traces: closing tags written `</ strong>` and a
leftover English `The`.

**UNIT3D, Japanese.** Call sites read in source:

- `email.fail-login-line2`, in `app/Notifications/FailedLogin.php`, is passed `ip`, `host` and
  `time`. The Japanese reads `この要求は、：ip（：host）at：timeから発生しました`, so the
  failed-login security email never shows which address tried to sign in, or when.
- `page.aboutus-welcome-desc` (`title`) and `user.profile-desc` (`user`, `title`) are passed the
  site's name; the Japanese shows `：title`. In `profile-desc` the `:user` placeholder is gone
  altogether.
- `torrent.announce-url-desc` is passed `source`. The English no longer mentions the source, but
  the older Japanese text still asks the uploader to set the source flag to `：source`, and shows
  that literally.
- `email.footer-link` (`：actionText`), `common.achievement-unlocked` (`：name`) and
  `user.moderated-by` (`：mod`) have the English `:actionText`, `:name` and `:mod`; their call
  sites were not found in the search and were not checked.

The text has other machine-translation traces too: "torrent" rendered as 急流 (rapids).

**Snipe-IT, Chinese validation messages.** In both zh-CN and zh-TW, `required_unless` reads
`需要：属性字段，除非：other is in：values。` (屬性 in zh-TW). `：other` and `：values` are shown
literally, the field name was translated away (`:attribute` became 属性, "attribute"), and
"is in" was left in English. The neighbouring `required_if` uses ASCII colons and works. A
related form appears in a few other zh-CN messages: the placeholder name itself was translated,
as in `：属性` and `：值`. These were not counted.

## How it was found, and the counts

Sourcegraph code search (non-fork, non-archived repositories). Queries and results:

- `：attribute` in files named `validation.php`: 1 file (Akaunting ja-JP), 15 lines.
- For scale: Chinese or Japanese `validation.php` files containing an ASCII `:attribute`:
  121 files in 82 repositories.
- A fullwidth colon followed by one of 31 common placeholder names, in `lang/<ja|zh*>/<file>.php`:
  33 matches in 5 repositories. Three are the projects above; the other two (Flute CMS,
  bagisto headless-ecommerce) are prose (`警告：URL`, `成功：URL`), not placeholders.

Sourcegraph reported "result limit hit" on these searches and, for some, backends down. The
counts are a lower bound from one day's index and should not be read as rates. A broader query
(any fullwidth colon followed by a Latin word in Chinese or Japanese lang files) is dominated by
ordinary punctuation (`例如：value`, `Unreal Engine 3：RenoDX`), so this note only reports cases
whose English source has the placeholder.

## What is new here

- Web searches in English and Japanese (2026-10-18) found no write-up of fullwidth colons in
  Laravel placeholders. Japanese Laravel guides all write `:attribute` with the ASCII colon, and
  one 2025 comparison of AI models translating `validation.php`
  ([zenn.dev](https://zenn.dev/kat/articles/014491a3e43ee7)) found the models kept placeholders
  intact when told to.
- One Laravel package, [Ruvelo/laravel-translations](https://github.com/Ruvelo/laravel-translations),
  flags broken `:name` placeholders in its web editor, which would show these as missing. No
  checker found names the fullwidth colon as the cause.
- All three projects' cases are in Chinese or Japanese, as with the other look-alike families
  here. The machine-translation traces in two of them (急流 for "torrent", `</ strong>`) suggest
  an older MT pass as the source. That is a guess from the text, not tested.

## Limits

- Three projects, read by hand; no application was run. The effect follows from Laravel's
  source (12.x: `Translator::makeReplacements`, `FormatsMessages::replaceAttributePlaceholder`)
  and, for UNIT3D, from the call sites read. `：other`, `：values` and `：size` are expected to
  behave the same, but their replacers were not read.
- A project that renders these strings another way (a JavaScript i18n library, its own
  replacer) would behave differently. That was not checked for Akaunting or Snipe-IT.
- No maintainer has been told yet. Fixes belong in each project's translation platform or files.
