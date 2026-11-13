#!/usr/bin/env python3
# sphinx_locales.py - find Sphinx translations that a build never compiles or never finds.
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
#
# Source reading, not a build test. Sphinx v9.2.0 and CPython's gettext module were read:
# - sphinx/util/i18n.py CatalogRepository.locale_dirs: a catalog folder is compiled only if
#   <srcdir>/<locale_dir>/<language>/LC_MESSAGES exists, with `language` used exactly as
#   given (no lowercasing, no '-' to '_').
# - sphinx/builders/__init__.py compile_catalogs: .po -> .mo only for those folders, and only
#   when gettext_auto_build is true (the default).
# - sphinx/transforms/i18n.py Locale.apply -> sphinx/locale init(): every locale_dirs entry is
#   searched with gettext.translation(domain, localedir=dir, languages=[language]).
# - CPython Lib/gettext.py find() / _expand_lang(): the language is normalised with
#   locale.normalize and expanded (pt_BR -> pt_BR.ISO8859-1, pt_BR, pt.ISO8859-1, pt).
# So lookup falls back from pt_BR to pt, but compilation never does: a pt/ folder holding
# only .po files is never compiled for a pt_BR build and that build stays in English.
# Folder names that differ from the language in case (zh_cn vs zh_CN) or separator
# (pt-br vs pt_BR) are found by neither step on a case-sensitive filesystem.
#
# Standard library only. Reads conf.py as text (ast, never executed).
import argparse
import ast
import gettext
import json
import os
import sys

VERSION = "0.1.0"
DEFAULT_LOCALE_DIRS = ["locales"]

# Read the Docs project language codes (lowercase, dash) and the value its default Sphinx
# build passes as -D language=..., from readthedocs/projects/constants.py
# OLD_LANGUAGES_CODE_MAPPING and doc_builder/backends/sphinx.py get_language().
# Every other code is passed unchanged.
RTD_TO_SPHINX = {
    "nb-no": "nb_NO",
    "pt-br": "pt_BR",
    "es-mx": "es_MX",
    "uk-ua": "uk_UA",
    "zh-cn": "zh_CN",
    "zh-tw": "zh_TW",
}

CONF_KEYS = ("language", "locale_dirs", "gettext_auto_build", "gettext_compact")


def expand_language(language):
    """The folder names gettext.find tries for one language, most specific first."""
    expand = getattr(gettext, "_expand_lang", None)
    if expand is None:  # pragma: no cover - present in every CPython 3.x
        return [language]
    try:
        return list(expand(language))
    except Exception:  # pragma: no cover
        return [language]


def read_conf(srcdir):
    """Top-level assignments of the i18n settings in conf.py, without running it."""
    info = {
        "found": False,
        "parsed": False,
        "language": None,
        "language_expr": None,
        "locale_dirs": None,
        "locale_dirs_expr": None,
        "locale_dirs_set": False,
        "gettext_auto_build": True,
        "gettext_auto_build_expr": None,
    }
    path = os.path.join(srcdir, "conf.py")
    if not os.path.isfile(path):
        return info
    info["found"] = True
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        text = handle.read()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return info
    info["parsed"] = True
    last = {}
    for node in ast.walk(tree):
        targets = []
        value = None
        if isinstance(node, ast.Assign):
            targets = node.targets
            value = node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
            value = node.value
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
            value = node
        for target in targets:
            if isinstance(target, ast.Name) and target.id in CONF_KEYS:
                previous = last.get(target.id)
                if previous is None or node.lineno >= previous[0]:
                    last[target.id] = (node.lineno, value)
    for key, (_, value) in last.items():
        literal = None
        ok = False
        if not isinstance(value, ast.AugAssign):
            try:
                literal = ast.literal_eval(value)
                ok = True
            except (ValueError, SyntaxError, TypeError):
                ok = False
        expr = ast.get_source_segment(text, value) or ""
        if key == "language":
            if ok and isinstance(literal, str):
                info["language"] = literal
            else:
                info["language_expr"] = expr
        elif key == "locale_dirs":
            info["locale_dirs_set"] = True
            if ok and isinstance(literal, (list, tuple)) and all(
                    isinstance(item, str) for item in literal):
                info["locale_dirs"] = list(literal)
            else:
                info["locale_dirs_expr"] = expr
        elif key == "gettext_auto_build":
            if ok and isinstance(literal, bool):
                info["gettext_auto_build"] = literal
            else:
                info["gettext_auto_build_expr"] = expr
    return info


def _domains(folder, suffix):
    found = set()
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for name in files:
            if name.endswith(suffix):
                rel = os.path.relpath(os.path.join(root, name), folder)
                found.add(rel[: -len(suffix)].replace(os.sep, "/"))
    return found


def scan_locale_dir(base):
    """Each child folder of one locale dir: its exact name and its catalogs."""
    folders = {}
    if not os.path.isdir(base):
        return folders
    for name in sorted(os.listdir(base)):
        child = os.path.join(base, name)
        if name.startswith(".") or not os.path.isdir(child):
            continue
        lc = os.path.join(child, "LC_MESSAGES")
        if os.path.isdir(lc):
            folders[name] = {"lc_messages": True, "po": _domains(lc, ".po"),
                             "mo": _domains(lc, ".mo")}
        else:
            folders[name] = {"lc_messages": False, "po": _domains(child, ".po"),
                             "mo": _domains(child, ".mo")}
    return folders


def _rel(srcdir, *parts):
    return os.path.relpath(os.path.join(srcdir, *parts), srcdir).replace(os.sep, "/")


def evaluate_language(language, requested_as, scans, auto_build, srcdir):
    order = expand_language(language)
    compiled = set()
    exact_dirs = []
    uncompiled_exact = set()
    for locale_dir, folders in scans:
        entry = folders.get(language)
        if entry and entry["lc_messages"]:
            exact_dirs.append(_rel(srcdir, locale_dir, language))
            compiled |= entry["mo"]
            if auto_build:
                compiled |= entry["po"]
            else:
                uncompiled_exact |= entry["po"] - entry["mo"]
    fallback_mo = set()
    fallback_po = set()
    fallback_dirs = []
    for candidate in order:
        if candidate == language:
            continue
        for locale_dir, folders in scans:
            entry = folders.get(candidate)
            if entry and entry["lc_messages"] and (entry["po"] or entry["mo"]):
                fallback_dirs.append(_rel(srcdir, locale_dir, candidate))
                fallback_mo |= entry["mo"]
                fallback_po |= entry["po"] - entry["mo"]
    fallback_mo -= compiled
    fallback_po -= compiled | fallback_mo
    near = []
    exact_names = set(order)
    plain = [c for c in order if "." not in c]
    for locale_dir, folders in scans:
        for name, entry in folders.items():
            if name in exact_names or not (entry["po"] or entry["mo"]):
                continue
            folded = name.lower().replace("-", "_")
            for candidate in plain:
                if folded == candidate.lower().replace("-", "_"):
                    kind = ("case_mismatch" if name.lower() == candidate.lower()
                            else "separator_mismatch")
                    near.append({"kind": kind, "folder": _rel(srcdir, locale_dir, name),
                                 "expected": candidate,
                                 "lc_messages": entry["lc_messages"]})
                    break
    if compiled:
        status = "ok"
    elif fallback_mo:
        status = "fallback_mo"
    elif fallback_po:
        status = "fallback_uncompiled"
    elif uncompiled_exact:
        status = "auto_build_off"
    else:
        status = "missing"
    return {
        "language": language,
        "requested_as": requested_as,
        "lookup_order": order,
        "status": status,
        "exact_dirs": exact_dirs,
        "fallback_dirs": fallback_dirs,
        "compiled_domains": len(compiled),
        "fallback_mo_domains": sorted(fallback_mo),
        "uncompiled_fallback_domains": sorted(fallback_po),
        "uncompiled_exact_domains": sorted(uncompiled_exact),
        "near_misses": near,
    }


def check(srcdir, languages=None, rtd_languages=None, locale_dirs=None):
    conf = read_conf(srcdir)
    findings = []
    warnings = []
    if locale_dirs:
        dirs = list(locale_dirs)
        dirs_source = "argument"
    elif conf["locale_dirs"] is not None:
        dirs = conf["locale_dirs"]
        dirs_source = "conf.py"
    else:
        dirs = list(DEFAULT_LOCALE_DIRS)
        dirs_source = "default"
        if conf["locale_dirs_expr"]:
            dirs_source = "default (conf.py value not literal)"
            warnings.append({"kind": "locale_dirs_not_literal",
                             "detail": "conf.py sets locale_dirs = %s; pass --locale-dirs"
                                       % conf["locale_dirs_expr"]})
    scans = []
    for locale_dir in dirs:
        base = os.path.join(srcdir, locale_dir)
        if not os.path.isdir(base):
            if dirs_source != "default":
                warnings.append({"kind": "locale_dir_missing",
                                 "path": _rel(srcdir, locale_dir)})
            continue
        scans.append((locale_dir, scan_locale_dir(base)))

    if not conf["locale_dirs_set"] and not locale_dirs:
        if not os.path.isdir(os.path.join(srcdir, "locales")):
            alt = scan_locale_dir(os.path.join(srcdir, "locale"))
            with_catalogs = sorted(n for n, e in alt.items()
                                   if e["lc_messages"] and (e["po"] or e["mo"]))
            if with_catalogs:
                findings.append({
                    "kind": "locale_dirs_default_mismatch",
                    "path": "locale",
                    "detail": "conf.py does not set locale_dirs, so Sphinx searches only "
                              "'locales/'; catalogs under 'locale/' (%s) are never used"
                              % ", ".join(with_catalogs)})

    for locale_dir, folders in scans:
        for name, entry in folders.items():
            if not entry["lc_messages"] and entry["po"]:
                findings.append({
                    "kind": "no_lc_messages",
                    "path": _rel(srcdir, locale_dir, name),
                    "detail": "%d .po file(s) not under LC_MESSAGES; Sphinx compiles and "
                              "searches only <language>/LC_MESSAGES" % len(entry["po"])})

    expr = conf["language_expr"] or ""
    if "READTHEDOCS_LANGUAGE" in expr:
        warnings.append({
            "kind": "language_from_rtd_env",
            "detail": "conf.py sets language = %s. READTHEDOCS_LANGUAGE is lowercase with a "
                      "dash (pt-br, zh-cn) and Sphinx does not normalise it, so a build that "
                      "uses it finds no pt_BR/ or zh_CN/ catalog. Read the Docs' default "
                      "Sphinx build overrides it with -D language=pt_BR; custom "
                      "build.commands and local builds do not." % expr})

    requests = []
    for value in languages or []:
        requests.append((value, value))
    for value in rtd_languages or []:
        mapped = RTD_TO_SPHINX.get(value, value)
        requests.append((mapped, "%s (Read the Docs)" % value))
    if not requests and conf["language"] and not conf["language"].lower().startswith("en"):
        requests.append((conf["language"], "%s (conf.py)" % conf["language"]))

    results = []
    seen = set()
    for language, requested_as in requests:
        if (language, requested_as) in seen:
            continue
        seen.add((language, requested_as))
        result = evaluate_language(language, requested_as, scans,
                                   conf["gettext_auto_build"], srcdir)
        results.append(result)
        status = result["status"]
        is_english = language.lower().startswith("en")
        if status == "fallback_uncompiled":
            findings.append({
                "kind": "fallback_uncompiled", "language": language,
                "path": ", ".join(result["fallback_dirs"]),
                "detail": "no %s/ catalog folder; gettext would fall back to %s, but Sphinx "
                          "compiles only the exact folder, so %d .po domain(s) there are "
                          "never turned into .mo and the build stays untranslated"
                          % (language, ", ".join(result["fallback_dirs"]),
                             len(result["uncompiled_fallback_domains"]))})
        elif status == "auto_build_off":
            findings.append({
                "kind": "auto_build_off", "language": language,
                "path": ", ".join(result["exact_dirs"]),
                "detail": "gettext_auto_build = False and %d .po domain(s) have no .mo"
                          % len(result["uncompiled_exact_domains"])})
        elif status == "missing" and not is_english and not result["near_misses"]:
            findings.append({
                "kind": "missing", "language": language,
                "detail": "no catalog folder that Sphinx or gettext looks up for %s "
                          "(tried %s)" % (language, ", ".join(result["lookup_order"]))})
        elif status == "fallback_mo":
            warnings.append({
                "kind": "fallback_mo", "language": language,
                "path": ", ".join(result["fallback_dirs"]),
                "detail": "translated only through .mo files in a fallback folder; Sphinx "
                          "never rebuilds them from their .po files, so they can go stale"})
        for miss in result["near_misses"]:
            item = {"kind": miss["kind"], "language": language, "path": miss["folder"],
                    "detail": "folder name differs from %s only in %s; Sphinx compiles and "
                              "gettext looks up only the exact name"
                              % (miss["expected"],
                                 "case (works only on case-insensitive filesystems)"
                                 if miss["kind"] == "case_mismatch" else "'-' versus '_'")}
            if status == "ok":
                item["kind"] = "duplicate_" + miss["kind"]
                warnings.append(item)
            else:
                findings.append(item)

    folders_out = []
    for locale_dir, folders in scans:
        for name, entry in folders.items():
            folders_out.append({"path": _rel(srcdir, locale_dir, name),
                                "lc_messages": entry["lc_messages"],
                                "po": len(entry["po"]), "mo": len(entry["mo"])})
    if not requests:
        warnings.append({"kind": "no_language",
                         "detail": "no non-English language to evaluate; pass --language "
                                   "or --rtd-language"})
    return {
        "tool": "sphinx_locales",
        "version": VERSION,
        "basis": "source reading of Sphinx v9.2.0 and CPython gettext, not a build test",
        "conf": conf,
        "locale_dirs": dirs,
        "locale_dirs_source": dirs_source,
        "folders": folders_out,
        "languages": results,
        "findings": findings,
        "warnings": warnings,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Find Sphinx translation catalogs a build never compiles or finds.")
    parser.add_argument("srcdir", help="the Sphinx source folder (holding conf.py)")
    parser.add_argument("--language", action="append", default=[],
                        help="a value passed as -D language=... (repeatable)")
    parser.add_argument("--rtd-language", action="append", default=[],
                        help="a Read the Docs project language code, e.g. pt-br (repeatable)")
    parser.add_argument("--locale-dirs", default="",
                        help="comma-separated locale_dirs, overriding conf.py")
    parser.add_argument("--strict", action="store_true",
                        help="exit 1 when there is any finding")
    args = parser.parse_args(argv)
    dirs = [d for d in args.locale_dirs.split(",") if d] if args.locale_dirs else None
    report = check(args.srcdir, args.language, args.rtd_language, dirs)
    print(json.dumps(report, indent=2, sort_keys=False))
    if args.strict and report["findings"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
