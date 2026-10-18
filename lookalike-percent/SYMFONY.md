# lookalike-percent in Symfony translations: `％name％` and `٪ name٪`

MV2 of Munim, Inc., made with AI agents, 2026-10-18. Text CC BY 4.0.
[FINDINGS.md](FINDINGS.md) (Android), [APPLE.md](APPLE.md), [GETTEXT.md](GETTEXT.md) and
[RAILS.md](RAILS.md) showed translations that write a placeholder with the fullwidth `％`
(U+FF05) or the Arabic percent sign `٪` (U+066A). This note asks the same of the translation
files of PHP applications built on Symfony (`translations/*.<locale>.yaml` and `.xlf`/`.xliff`),
whose parameters are written `%name%`. It happens there too, in four projects, all in Chinese,
Japanese or Arabic. We **read** the translation files and the code that calls them; we did not
run any of these programs.

## Why it matters

Symfony's translator fills parameters with PHP's `strtr($message, $parameters)`
(`TranslatorTrait::trans` in symfony/contracts). The keys are used exactly as the caller passes
them, `'%name%'` with ASCII percent signs, and nothing adds or normalises the delimiters. So
`％name％` and `٪ name٪` are plain text: nothing is thrown or logged, the value is dropped, and the
user sees the placeholder name where a name, a number or a link belongs. Applications that pass
an indexed list and run `vsprintf` on the result (a Zend Framework 1 habit kept by Pimcore and
its forks) lose `％s` the same way.

## Confirmed in code (the key is called with the value that is lost)

Read on each project's default branch on 2026-10-18.

| Project | Translation | String | Call site | What users see |
|---|---|---|---|---|
| SonataAdminBundle (sonata-project/SonataAdminBundle, 4.x) | ja and zh_CN | `flash_lock_error` in `src/Resources/translations/SonataAdminBundle.ja.xliff` and `.zh_CN.xliff`: `別のユーザーがアイテム "％name％" を変更しました。 ％link_start％ここをクリック％link_end％ して、…` and `另一个用户修改了项目 "％name％"。请％link_start％单击此处％link_end％以重新加载页面并再次应用更改。` (English: `Another user has modified item "%name%". Please %link_start%click here%link_end% to reload the page and apply the changes again.`) | `src/Controller/CRUDController.php`, `editAction`, `catch (LockException)`: `$this->trans('flash_lock_error', ['%name%' => …, '%link_start%' => \sprintf('<a href="%s">', $this->admin->generateObjectUrl('edit', $existingObject)), '%link_end%' => '</a>'], 'SonataAdminBundle')` | When two people edit the same record (optimistic locking), the Japanese and Chinese warning shows `％name％` instead of the record's name and `％link_start％…％link_end％` as text, so the "click here" link that reloads the page is missing. |
| Akeneo PIM Community (akeneo/pim-community-dev) | zh_TW | `family_variant_no_axis` in `src/Akeneo/Pim/Enrichment/Bundle/Resources/translations/validators.zh_TW.yml`: `級別“％level％”的屬性z组應至少定義一個屬性作為軸` (English: `There should be at least one attribute defined as axis for the attribute set for level "%level%"`) | `src/Akeneo/Pim/Structure/Component/Validator/Constraints/FamilyVariantValidator.php`: `->buildViolation(FamilyVariant::NO_AXIS, ['%level%' => $i + 1])` | The validation error for a family variant without an axis names the level as `％level％` instead of its number. Of the 25 other translations of this key, every one we read in full keeps `%level%` except Turkish, which translates it as `%Seviye% ` and loses it for a different reason. |
| OpenDXP (open-dxp/opendxp, a Pimcore fork) | zh_Hans | `workflow_change_email_notification_text` in `bundles/CoreBundle/translations/admin.zh_Hans.yaml`: `对于ID为％s的％s，在工作流''％s''中触发了操作“％s”。` (English: `For %s with ID %s the action "%s" was triggered in workflow '%s'.`) | `bundles/CoreBundle/templates/Workflow/NotificationEmail/notificationEmail.html.twig`: `translator.trans('workflow_change_email_notification_text', [subjectType ~ ' ' ~ subject.getFullPath(), subject.getId(), …action…, …workflow name…], 'admin', lang)`; `lib/Translation/Translator.php` runs `vsprintf($term, $parameters)` for "an indexed array, that used the ZF1 vsprintf() notation" (we read those lines, not the condition between them). | The Chinese workflow notification email says that an action was triggered, without the item, its ID, the action or the workflow: all four values are dropped. |

## Seen in the translation file, call site not read

- **UVdesk community skeleton** (uvdesk/community-skeleton), ar: `translations/messages.ar.yml`
  translates `"Learn more about %deliveryStatus%."` as `"تعرف على المزيد حول٪ deliveryStatus٪."`.
  This is the spaced Arabic form (`٪ name٪`) that [RAILS.md](RAILS.md) found in every Arabic-script
  Rails file with a look-alike. If the caller passes `%deliveryStatus%`, the status is lost.

## Not bugs

The same searches returned many fullwidth or Arabic percent signs that are real percent signs:
`80％` and `（％）` in Mathigon, Seelen UI, edusoho, Bitcoin Cash and Akeneo's analytics labels;
`<percentage>％` in shapez.io and `{}％` in Mobileraker (the value comes first, then the sign);
`{percent}٪` in SUPLA Cloud and `20٪` and `0٪ و100٪` in Sylius. The Thai OpenDXP string writes
`% s` with a space, which PHP's `sprintf` reads as `%s` with a space-padding flag, so the values
still appear (Java's `String.format` would throw on it instead).

## A blind spot in placeholder checks

Sonata's XLIFF files use the key as `<source>` (`<source>flash_lock_error</source>`), and the
English text lives in the `.en.xliff` file. A check that compares `<source>` with `<target>`
inside one file, as XLIFF tools usually do, has no placeholder to compare and passes the Japanese
string. Only a check that pairs `ja` with `en` by key sees that `%name%` is missing. YAML
files are keyed the same way.

## What the cases have in common

All five strings are Chinese (3), Japanese (1) or Arabic (1). That matches what this census found
in Android, Apple, gettext, Rails, Qt, JSON, .resx and Laravel files. These are cases, **not a rate**:
there are no per-language totals.

## How we looked, and the limits

- Sourcegraph keyword searches, read 2026-10-18, default scope (no forks, no archived
  repositories), for the single character `％` in files matching
  `translations/.*\.(ya?ml|xlf|xliff)$` (every locale: 32 matches in 9 repositories; 13 files were listed),
  for `％` in Chinese and Japanese files only (20 matches, 5 files, 3 repositories) and for
  `٪` in Arabic, Persian, Urdu, Pashto, Kurdish, Uyghur and Sindhi files (10 matches, 4 files,
  3 repositories). Sourcegraph reported a result limit on each, so these are **lower bounds**.
  Every match line was read. Files outside a `translations/` folder, and other look-alikes
  (`﹪`), were not searched.
- "Confirmed in code" means we read the translation and the call site named, on the default
  branch. We did not check which release or deployment serves each file, and we ran nothing.

## Also checked: WebExtension `messages.json` (none found)

Browser extensions write placeholders as `$name$` and `$1` in `_locales/<lang>/messages.json`.
A keyword search for the fullwidth dollar sign `＄` (U+FF04) in the `ja`, `zh_CN`, `zh_TW` and `ko`
files returned **0 matches** and was reported as exhaustive (default scope, 2026-10-18). The same
search for the fullwidth colon `：` in the same files returned 50 matches in about 2 seconds, so
the search works on these files. In the files Sourcegraph indexes, the look-alike dollar
does not occur.

## Prior art

Symfony's documentation explains that parameters are replaced with `strtr` and that any wrapper
works as long as the key matches exactly, and Symfony issues #49093 and #36620 are about ASCII
placeholders that were not replaced. We found no report or write-up on fullwidth or Arabic
percent signs in Symfony translations (English web search, 2026-10-18). Loclint's
[placeholder checker](https://loclint.com/tools/placeholder-checker) names fullwidth retyping of
placeholders in general.

## Check your own files

    grep -rnE '(％|٪|﹪) ?[A-Za-z_]+ ?(％|٪|﹪)|(％|٪|﹪)[sd]' translations/

Read every hit. The fix is to replace the look-alike, and any space after it, with the ASCII
`%` in the translation, best done on the project's translation platform.
