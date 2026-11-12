# Addendum 1 to census xcode-lproj v3: Xcode's new JSON project format

Written 2026-11-12 (about 21:30 UTC), after the pre-registration
([PREREG.md](PREREG.md)) and **before any result of job `xcl3-weblate-v1` has been seen**. It
changes no prediction, rule or code. Made with AI agents by MV2 of Munim, Inc.
(mv2@munimtech.com). Text CC BY 4.0.

## What changed after the pre-registration was written

Xcode 27.2 (release candidate 19 October 2026) adds a JSON project file, `project.xcproj`, which
replaces `project.pbxproj` inside the `.xcodeproj` bundle. New projects use it by default;
existing projects switch only when their owner converts them. Apple publishes the format's model
as open source: [apple/xcode-project-format](https://github.com/apple/xcode-project-format)
(Apache-2.0 with Runtime Library Exception).

## Limit this adds to the census

The census code reads only `*.xcodeproj/project.pbxproj`. A repository that has converted to
`project.xcproj` therefore has no project file the code can read, none of its tables count as
managed by Xcode, and it cannot be governed or flagged. This can only make the counts smaller,
never larger. When the results are written up we will say how many of the 35 repositories, if
any, hold a `project.xcproj`, if the job's outputs let us tell.

## Does the gap exist in the new format? (source reading, not a test)

From the format's Swift model on its `main` branch (tree `0a7242a`, read 2026-11-12):

- A localized file is still a **variant group** (`"kind": "variant-group"`) whose `children` are
  explicit file references, one per language
  (`Sources/Library/Schema/References/Groups/VariantGroup.swift`). The format's schema
  overview says a variant group "represents a localized file and collects per-language
  representations from the separate `lproj` folders".
- The project's languages are listed in `"localizations"`, as `development` plus `supported`
  (`Sources/Library/Schema/Values/ProjectLocalizationInfo.swift`), the JSON counterpart of
  `knownRegions`.
- A synchronized **folder** (`"kind": "folder"`) adds the files found on disk to its targets
  implicitly, as in Xcode 16.

So a `<lang>.lproj/<Table>.strings` file committed by a translation platform is not part of a
variant group in the JSON format either, until someone adds it in Xcode. We have not built a
`project.xcproj` project to confirm this; it is a reading of the published model only.
