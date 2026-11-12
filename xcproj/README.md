# xcproj: translations that Xcode 27.2's JSON project file never builds

Xcode 27.2 adds a new project file, `<Name>.xcodeproj/project.xcproj`. It is JSON with
comments and trailing commas and replaces `project.pbxproj` in projects that opt in, and it is
the default for new projects. Translation tools that read `project.pbxproj` to find which
`<lang>.lproj/*.strings` files ship do not see these projects at all.

`xcproj_l10n.py` is a small checker for the new format: given a checked-out repository, it
lists translated `.strings` files that are committed next to a registered string table but
are not in the project, so Xcode never copies them into the app.

```
python xcproj_l10n.py path/to/repo            # JSON report, exit 0
python xcproj_l10n.py path/to/repo --strict   # exit 1 if any translation is not built
```

Standard library only (Python 3.8+). Tests: `python -m unittest -v test_xcproj_l10n`.

## How it reads the format

Written from the published model in Apple's
[xcode-project-format](https://github.com/apple/xcode-project-format) package (Apache-2.0
with the Swift runtime exception), read on 2026-11-12, and checked against two public files
in the new format: the Capacitor CLI test fixture
(`cli/test/fixtures/xcproj/default/project.xcproj` in
[ionic-team/capacitor#8608](https://github.com/ionic-team/capacitor/pull/8608)) and the
format-parity fixture in
[bitrise-io/go-xcode#401](https://github.com/bitrise-io/go-xcode/pull/401).

- `"files"` is the navigator tree. Each node has a `"kind"`: `file-reference` (the default
  when `"kind"` is missing), `group`, `folder` (a synchronized folder: everything inside it is
  in the project), `variant-group` or `version-group`.
- A node's location is a single `"path"` string. A bare relative path is relative to the
  parent node's folder; `<PROJECT>/...` is relative to the folder holding the `.xcodeproj`;
  `<SDK>/`, `<DEVELOPER>/`, `<PRODUCTS>/`, `<USER:VAR>/` and absolute paths are outside the
  repository.
- A localized resource is a `variant-group` (usually with a `"name"` and no `"path"`). Each
  language is a child file reference whose path carries its `.lproj` folder, for example
  `"de.lproj/Localizable.strings"`. File references have no `"name"`, so the language comes
  from the path. A `.lproj` file added by a translation platform is therefore not built until
  it is added to the variant group, exactly as with `project.pbxproj`.
- `"localizations": {"development": "en", "supported": [...]}` is the `knownRegions`
  equivalent, with one difference: in Apple's model `"supported"` never contains the
  development language (`precondition(!supported.contains(development))`). A tool that
  treats `"supported"` as `knownRegions` will think the development language is missing.
  This checker reports `regions` as the development language followed by the supported ones.

## What counts as "not built"

The same rules as MV2's xcode-lproj census v3 (see `weblate-apple/` in this repository):

- only string tables the project registers at least one language of are checked;
- a file is not built when neither it nor a folder above it is referenced;
- English, `Base` and a regional copy (`de-AT` when `de` ships) never count;
- `Pods/`, `Carthage/`, vendored and build folders, and bundles are skipped.

Each finding gives the table, the language, whether the language is listed in
`localizations`, and whether it is lost from the whole app (`whole`) or only from this table.

## Limits

- Not yet run on a real repository with a translation in the new format: no public
  `project.xcproj` with translated `.strings` files had been found on 2026-11-12. The tests
  use a synthetic project built from Apple's model; the two real files above only contain
  `Base.lproj` storyboards.
- How Xcode escapes `<` inside a path is assumed to be `\<`; node kinds it does not know are
  skipped.
- String Catalogs (`.xcstrings`) and `.stringsdict` files are not checked.
- If a `.xcodeproj` holds both `project.pbxproj` and `project.xcproj`, the report marks it
  (`pbxproj_too`) but reads only the JSON file.

Made with AI agents by MV2 of Munim, Inc. (mv2@munimtech.com). Licence: Apache-2.0.
