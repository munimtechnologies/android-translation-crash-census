#!/usr/bin/env python3
# qt_l10n.py: Qt translation files (.ts/.qm) that the app's QTranslator::load call never tries.
# Source reading of qtbase (qtranslator.cpp, qlocale.cpp, Qt 6 docs), not a build test.
# Standard library only, no network.
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
"""Find Qt translation files whose locale part no QTranslator::load call can reach.

Load styles modelled:
  A   load("app_" + QLocale::system().name()) and friends (the string overload).
      name() is "language_TERRITORY" with no script, ever. The string overload
      tries that name, then cuts it at the rightmost '_' or '.', and never
      lowercases. So it reaches only codes like "pt_BR" and "pt".
  A2  the same, but the name is cut to the language first (.left(2), [:2],
      .split('_')[0], .section('_', 0, 0)). It reaches only "pt".
  B   load(QLocale(), "app", "_", dir): the QLocale overload. It tries each
      QLocale::uiLanguages() entry with '_' separators, as written and in
      lowercase. Those entries never hold '-' or '@'.
"""
import argparse
import json
import os
import re
import sys

ISO639_1 = set((
    "aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce ch co cr cs cu cv "
    "cy da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi ho hr "
    "ht hu hy hz ia id ie ig ii ik in io is it iu iw ja ji jv jw ka kg ki kj kk kl km kn ko kr "
    "ks ku kv kw ky la lb lg li ln lo lt lu lv mg mh mi mk ml mn mo mr ms mt my na nb nd ne ng "
    "nl nn no nr nv ny oc oj om or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg sh si sk "
    "sl sm sn so sq sr ss st su sv sw ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve "
    "vi vo wa wo xh yi yo za zh zu").split())
ISO639_3_COMMON = set((
    "ast ber bho chr ckb csb dsb fil frp fur gsw haw hsb jbo kab kmr lij lmo ltg lzh mai mni "
    "nap nds nqo pms sat scn sco szl tok tzm vec yue zgh").split())
LANGS = ISO639_1 | ISO639_3_COMMON

# Two-letter codes QLocale reads as another language, and the code it writes back
# (qlocale.cpp, QLocalePrivate::codeToLanguage, legacy table, read 13 Nov 2026).
LEGACY = {"no": "nb", "tl": "fil", "sh": "sr", "mo": "ro", "iw": "he", "in": "id", "ji": "yi"}

CODE_RE = re.compile(
    r"^(?P<lang>[a-z]{2,3})"
    r"(?:(?P<sep1>[_-])(?P<script>[A-Z][a-z]{3}|[a-z]{4}))?"
    r"(?:(?P<sep2>[_-])(?P<region>[A-Za-z]{2}|\d{3}))?"
    r"(?P<mod>@[A-Za-z]+)?$")

SKIP_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", "build",
             "_build", "dist", ".tox"}
SOURCE_EXT = (".cpp", ".cc", ".cxx", ".c++", ".h", ".hh", ".hpp", ".hxx", ".mm", ".py")
# Qt's own catalogs (installed in QLibraryInfo's TranslationsPath), not the app's.
QT_OWN_PREFIX = re.compile(
    r"^(qt|qtbase|qtconnectivity|qtdeclarative|qtlocation|qtmultimedia|qtquickcontrols2?"
    r"|qtserialport|qtwebengine|qtwebsockets|qtscript|qtxmlpatterns|qt_help|assistant"
    r"|designer|linguist|qmlviewer)$")


def parse_code(code):
    """Return the regex match for a locale code if its language is known, else None."""
    m = CODE_RE.match(code)
    if not m or m.group("lang") not in LANGS:
        return None
    return m


def split_options(stem):
    """Every way to split a file stem into (prefix, locale code), shortest prefix first."""
    starts = [0] + [i + 1 for i, ch in enumerate(stem) if ch in "_.-"]
    return [(stem[:i], stem[i:]) for i in starts if i < len(stem) and parse_code(stem[i:])]


def split_stem(stem, counts=None, known=()):
    """Pick one split: a prefix a load call names, then the folder's most common, then shorter."""
    opts = split_options(stem)
    if not opts:
        return None, None
    counts = counts or {}
    return max(opts, key=lambda o: (o[0].rstrip("_.-") in known, counts.get(o[0], 0),
                                    -len(o[0])))


def is_qt_ts(path):
    try:
        with open(path, "rb") as fh:
            head = fh.read(4096)
    except OSError:
        return False
    return b"<TS" in head


def find_units(root, known=()):
    """Map (relative dir, prefix) -> {code: [file names]} for every Qt translation file.

    known: prefixes (without the trailing delimiter) that the source's load calls name.
    """
    units = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS and not d.startswith("cmake-build"))
        files = []
        for name in sorted(filenames):
            stem, ext = os.path.splitext(name)
            if ext not in (".ts", ".qm"):
                continue
            if ext == ".ts" and not is_qt_ts(os.path.join(dirpath, name)):
                continue
            files.append((name, stem))
        counts = {}
        for _, stem in files:
            for p, _c in split_options(stem):
                counts[p] = counts.get(p, 0) + 1
        for name, stem in files:
            prefix, code = split_stem(stem, counts, known)
            if code is None:
                continue
            if QT_OWN_PREFIX.match(prefix.rstrip("_.-")):
                continue
            rel = os.path.relpath(dirpath, root).replace(os.sep, "/")
            units.setdefault((rel, prefix), {}).setdefault(code, []).append(name)
    return units


# ---------------------------------------------------------------- source side

def strip_comments(text, python):
    """Blank out comments, keeping string literals and line count."""
    out = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch in "\"'":
            j = i + 1
            while j < n and text[j] != ch and text[j] != "\n":
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif python and ch == "#":
            j = text.find("\n", i)
            j = n if j < 0 else j
            i = j
        elif not python and text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            i = j
        elif not python and text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("\n" * text.count("\n", i, j))
            i = j
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def call_args(text, open_idx):
    """Return the text between the parenthesis at open_idx and its match (or None)."""
    depth, i, n = 0, open_idx, len(text)
    quote = None
    while i < n and i - open_idx < 2000:
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i]
        i += 1
    return None


def split_top(args):
    """Split call arguments at top-level commas."""
    parts, depth, cur, quote = [], 0, [], None
    i = 0
    while i < len(args):
        ch = args[i]
        if quote:
            cur.append(ch)
            if ch == "\\" and i + 1 < len(args):
                cur.append(args[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            cur.append(ch)
        elif ch in "([{":
            depth += 1
            cur.append(ch)
        elif ch in ")]}":
            depth -= 1
            cur.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(cur).strip())
            cur = []
        else:
            cur.append(ch)
        i += 1
    if "".join(cur).strip():
        parts.append("".join(cur).strip())
    return parts


LITERAL_RE = re.compile(r"\"((?:[^\"\\\n]|\\.)*)\"|'((?:[^'\\\n]|\\.)*)'")
NAME_RE = re.compile(r"QLocale\s*(?:::|\.)\s*system\s*\(\s*\)\s*\.\s*name\s*\(\s*\)"
                     r"|QLocale\s*\([^()]*(?:\([^()]*\)[^()]*)*\)\s*\.\s*name\s*\(\s*\)")
CUT_RE = re.compile(r"^\s*(?:\.\s*left\s*\(\s*2\s*\)|\.\s*mid\s*\(\s*0\s*,\s*2\s*\)"
                    r"|\[\s*:\s*2\s*\]|\.\s*section\s*\(|\.\s*split\s*\()")
BCP47_RE = re.compile(r"\.\s*bcp47Name\s*\(")
UILANG_RE = re.compile(r"uiLanguages\s*\(")
LOAD_RE = re.compile(r"(?:\.|->)\s*load\s*\(")


def literals(text):
    return [a if a is not None else b for a, b in LITERAL_RE.findall(text)]


def name_style(expr):
    """'A2' if a name() in expr is cut to the language, 'A' if used whole, else None."""
    style = None
    for m in NAME_RE.finditer(expr):
        if CUT_RE.match(expr[m.end():]):
            return "A2"
        style = "A"
    return style


def assigned_exprs(text, ident):
    """Right-hand sides assigned to ident in this file (C++ or Python)."""
    rx = re.compile(r"(?<![\w.>])" + re.escape(ident) + r"\s*(?:=(?!=)|\{|\()\s*([^;\n]+)")
    return [m.group(1) for m in rx.finditer(text)]


def classify_call(text, args):
    """Return (style, literals) for one .load(...) call; style None if not a translator load."""
    parts = split_top(args)
    if not parts:
        return None, []
    lits = literals(args)
    first = parts[0]
    bare = LITERAL_RE.sub('""', args)
    idents = re.findall(r"(?<![\w.\"':>])([A-Za-z_]\w*)(?![\w(\"':])", bare)
    idents += re.findall(r"\{([A-Za-z_]\w*)[}!:]", args)  # Python f-string fields
    idents = [i for i in dict.fromkeys(idents) if i not in ("QLocale", "self", "this", "QString")]
    exprs = [args]
    for ident in idents:
        exprs.extend(assigned_exprs(text, ident))
    for e in exprs[1:]:
        lits.extend(literals(e))
    styles = [name_style(e) for e in exprs]
    if "A2" in styles:
        return "A2", lits
    if "A" in styles:
        return "A", lits
    if any(BCP47_RE.search(e) for e in exprs):
        return "bcp47", lits
    first_is_locale = "QLocale" in first and ".name" not in first
    if not first_is_locale and re.fullmatch(r"[A-Za-z_]\w*", first):
        decl = re.compile(r"QLocale\s*[&*]?\s*" + re.escape(first) + r"\b"
                          r"|\b" + re.escape(first) + r"\s*=\s*QLocale\b")
        first_is_locale = bool(decl.search(text))
    if first_is_locale and len(parts) >= 2:
        return "B", lits
    if any(UILANG_RE.search(e) for e in exprs):
        return "ui_languages_loop", lits
    return None, lits


def find_calls(root):
    calls = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames
                             if d not in SKIP_DIRS and not d.startswith("cmake-build"))
        for name in sorted(filenames):
            if not name.endswith(SOURCE_EXT):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    raw = fh.read()
            except OSError:
                continue
            if "QTranslator" not in raw and "installTranslator" not in raw:
                continue
            text = strip_comments(raw, name.endswith(".py"))
            for m in LOAD_RE.finditer(text):
                args = call_args(text, m.end() - 1)
                if args is None:
                    continue
                style, lits = classify_call(text, args)
                if style is None:
                    continue
                calls.append({
                    "file": os.path.relpath(path, root).replace(os.sep, "/"),
                    "line": text.count("\n", 0, m.start()) + 1,
                    "style": style,
                    "literals": lits,
                })
    return calls


def literal_base(lit):
    base = re.sub(r"\{[^}]*\}|%\d|%s|%L\d", "", lit)
    base = re.split(r"[/:\\]", base)[-1]
    return base.rstrip("_.-")


def attribute(prefix, calls):
    """Calls whose string literals name this prefix."""
    want = prefix.rstrip("_.-")
    hits = []
    for c in calls:
        bases = [literal_base(x) for x in c["literals"]]
        if want and want in bases:
            hits.append(c)
        elif not want and any(re.search(r"[/:\\]", x) and not literal_base(x)
                              for x in c["literals"]):
            hits.append(c)
    return hits


def is_qt_call(c):
    bases = [literal_base(x) for x in c["literals"] if literal_base(x)]
    return any(QT_OWN_PREFIX.match(b) for b in bases)


# ------------------------------------------------------------- reachability

def judge(code, style):
    """Return (kind, reason) if the code can never be tried under style, else None."""
    m = parse_code(code)
    lang, script, region, mod = m.group("lang"), m.group("script"), m.group("region"), m.group("mod")
    if "-" in code:
        return "hyphen", "Qt builds the locale part with '_' only, so a '-' name is never tried"
    if mod:
        return "modifier", "Qt locale names have no '@' modifier (that is a gettext/glibc form)"
    if style == "B":
        return None
    if script:
        return "script_code", "QLocale::name() never includes a script"
    if lang in LEGACY:
        return "legacy_code", "QLocale reads '%s' as the language it writes '%s'" % (lang, LEGACY[lang])
    if style == "A2" and region:
        return "region_code", "the code cuts the locale name to its language, so only '%s' is tried" % lang
    if region and region.isalpha() and not region.isupper():
        return "case", ("the string overload never lowercases: name() gives '%s_%s'; missed on "
                        "case-sensitive file systems and in Qt resources (:/)" % (lang, region.upper()))
    return None


def check(root):
    calls = find_calls(root)
    own_calls = [c for c in calls if not is_qt_call(c)]
    known = {literal_base(x) for c in own_calls for x in c["literals"]} - {""}
    units = find_units(root, known)
    styles = sorted({c["style"] for c in own_calls})
    report = {"units": [], "calls": calls, "findings": [], "notes": []}
    for (rel, prefix), codes in sorted(units.items()):
        hits = attribute(prefix, own_calls)
        how = "literal"
        if not hits and prefix == "qml_" and os.path.basename(rel) == "i18n":
            hits, how = [{"style": "B", "file": "(QQmlApplicationEngine)", "line": 0}], "qml_engine"
        if not hits and len(styles) == 1:
            hits, how = own_calls, "only_style_in_project"
        unit_styles = sorted({c["style"] for c in hits})
        unit = {"dir": rel, "prefix": prefix, "codes": sorted(codes), "styles": unit_styles,
                "attribution": how if hits else "none",
                "calls": ["%s:%d" % (c["file"], c["line"]) for c in hits]}
        report["units"].append(unit)
        if not hits:
            report["notes"].append({"kind": "no_load_call_found", "dir": rel, "prefix": prefix})
            continue
        modelled = [s for s in unit_styles if s in ("A", "A2", "B")]
        for s in unit_styles:
            if s not in ("A", "A2", "B"):
                report["notes"].append({"kind": "not_modelled", "dir": rel, "prefix": prefix,
                                        "style": s})
        if not modelled:
            continue
        for code in sorted(codes):
            verdicts = [judge(code, s) for s in modelled]
            if all(verdicts):
                kind, reason = verdicts[0]
                report["findings"].append({
                    "kind": kind, "dir": rel, "prefix": prefix, "code": code,
                    "files": sorted(codes[code]), "styles": modelled, "reason": reason,
                    "calls": unit["calls"]})
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any finding")
    a = ap.parse_args(argv)
    report = check(a.root)
    if a.json:
        print(json.dumps(report, indent=1, sort_keys=True))
    else:
        for u in report["units"]:
            print("unit %s/%s*: %d codes, styles %s (%s)" % (
                u["dir"], u["prefix"], len(u["codes"]), ",".join(u["styles"]) or "-",
                u["attribution"]))
        for f in report["findings"]:
            print("FINDING %s: %s/%s%s (%s) - %s" % (
                f["kind"], f["dir"], f["prefix"], f["code"], ",".join(f["styles"]), f["reason"]))
        for n in report["notes"]:
            print("note %s: %s/%s" % (n["kind"], n["dir"], n["prefix"]))
    if not report["units"]:
        return 2
    return 1 if (a.strict and report["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
