# Deviations from PREREG.md (linguas-script census v1)

1. **Two hand checks were partial.** For Escritoire (sample 7) the Rust entry point under
   `crates/` was not read, and for Frog (sample 12) the launcher script in `bin/` was not read. Both
   are labelled real on the evidence that was read (a real translation, a plain
   `i18n.gettext(...)` in `po/meson.build`, no `LANGUAGE` or renaming in the files read). This
   cannot change the verdict: H failed with 8 real of 12, and it would still fail at 6 of 12.
2. **Naev's content was not read by the job** (its row in `lost_files.csv` is blank). The hand
   check labels it not real on criterion 2 (its own loader finds `zh_Hans`), so its content does not
   matter for H.
3. **Hand checks were done by an AI agent working for MV2, reading files through a web fetch
   tool**, which PREREG.md allows ("a person or agent"). Each note in `labels.csv` names the files
   read at the recorded commit.

No prediction, threshold or sample was changed after the job ran.
