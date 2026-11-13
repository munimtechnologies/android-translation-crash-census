#!/usr/bin/env python3
# flutter_l10n: Flutter translations that the app's own locale list or a platform leaves out.
# Standard library only, no network.
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
"""Check a Flutter project's ARB translations against the places that decide whether they show.

gen-l10n (flutter_tools, read on 13 November 2026) turns every ARB file in arb-dir into a locale.
The app then only ever uses a locale from MaterialApp's supportedLocales, and the generated
delegate is only loaded for a language that has an ARB file. iOS lists the app's languages
from the Xcode project's knownRegions (Flutter's docs ask you to add them there), and Android
13+ offers only the languages in the app's localeConfig. This checker reads all of these as
text and reports where they disagree. Source reading, not a build test.

Usage: python flutter_l10n.py <project root> [--arb-dir lib/l10n]
       [--template-arb-file app_en.arb] [--strict]
"""
import argparse
import json
import os
import plistlib
import re
import sys

__version__ = "0.1.0"

# ISO 639-1 codes, plus the two 3-letter codes gen-l10n's _iso639Languages also holds.
ISO639_1 = frozenset("""
aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce ch co cr cs cu cv cy
da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi ho hr ht hu
hy hz ia id ie ig ii ik io is it iu ja jv ka kg ki kj kk kl km kn ko kr ks ku kv kw ky la lb
lg li ln lo lt lu lv mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl nn no nr nv ny oc oj om
or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl sm sn so sq sr ss st su sv sw
ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve vi vo wa wo xh yi yo za zh zu
""".split()) | {"fil", "gsw"}
# Old codes Android, Apple and Flutter's Locale still accept for the same language.
ALIASES = {"iw": "he", "in": "id", "ji": "yi"}
# Language names that old Xcode projects use in knownRegions.
APPLE_NAMES = {"english": "en", "french": "fr", "german": "de", "japanese": "ja",
               "italian": "it", "spanish": "es", "dutch": "nl"}
GEN_MARKER = "delegate failed to load unsupported locale"


# ---------------------------------------------------------------- locales

def try_parse_locale(text):
    """Close port of package:intl Locale.tryParse: (lang, script, region) or None."""
    parts = re.split(r"[-_]", text or "")
    if not parts or not re.fullmatch(r"[A-Za-z]{2,3}|[A-Za-z]{5,8}", parts[0]):
        return None
    lang, script, region, i = parts[0].lower(), None, None, 1
    if i < len(parts) and re.fullmatch(r"[A-Za-z]{4}", parts[i]):
        script = parts[i][0].upper() + parts[i][1:].lower()
        i += 1
    if i < len(parts) and re.fullmatch(r"[A-Za-z]{2}|[0-9]{3}", parts[i]):
        region = parts[i].upper()
        i += 1
    while i < len(parts):
        if not re.fullmatch(r"[A-Za-z0-9]{5,8}|[0-9][A-Za-z0-9]{3}", parts[i]):
            return None
        i += 1
    return (lang, script, region)


def loc_str(loc):
    """Flutter's Locale.toString: subtags joined with '_'."""
    return "_".join(p for p in loc if p)


def language(code):
    """Primary language of a locale name in any of the ARB, Apple or Android spellings."""
    code = (code or "").strip()
    if code.lower().startswith("b+"):
        code = code[2:]
    first = re.split(r"[-_+]", code)[0].lower()
    first = APPLE_NAMES.get(first, first)
    return ALIASES.get(first, first)


def filename_locale(stem):
    """gen-l10n: try the whole file name, then the text after each '_'."""
    cands = [stem] + [stem[i + 1:] for i, ch in enumerate(stem) if ch == "_"]
    for cand in cands:
        loc = try_parse_locale(cand)
        if loc and loc[0] in ISO639_1:
            return loc
    return None


def lookup(sup, active):
    """The generated lookup<Class>(locale): which ARB locale a supported locale gets."""
    lang, script, region = sup
    if script and region and sup in active:
        return sup
    if script and (lang, script, None) in active:
        return (lang, script, None)
    if region and (lang, None, region) in active:
        return (lang, None, region)
    if (lang, None, None) in active:
        return (lang, None, None)
    return None


# ---------------------------------------------------------------- config and ARB files

def _read(path):
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def _yaml_value(text, key):
    m = re.search(r"(?m)^[ \t]*" + re.escape(key) + r"[ \t]*:[ \t]*(.*)$", text or "")
    if not m:
        return None
    value = re.sub(r"\s+#.*$", "", m.group(1)).strip().strip("'\"")
    return value or None


def find_config(root, arb_dir=None, template=None):
    l10n = _read(os.path.join(root, "l10n.yaml"))
    pubspec = _read(os.path.join(root, "pubspec.yaml")) or ""
    source = "default"
    if l10n is not None:
        source = "l10n.yaml"
        arb_dir = arb_dir or _yaml_value(l10n, "arb-dir")
        template = template or _yaml_value(l10n, "template-arb-file")
    else:
        m = re.search(r"(?m)^flutter_intl[ \t]*:[ \t]*\n((?:[ \t]+.*\n?|[ \t]*\n)*)", pubspec)
        if m:
            source = "pubspec flutter_intl"
            arb_dir = arb_dir or _yaml_value(m.group(1), "arb_dir")
            main = _yaml_value(m.group(1), "main_locale") or "en"
            template = template or "intl_%s.arb" % main
    return {"source": source, "arb_dir": arb_dir or "lib/l10n",
            "template_arb_file": template or "app_en.arb"}


def read_arbs(root, cfg):
    adir = os.path.join(root, *cfg["arb_dir"].split("/"))
    names = sorted(n for n in os.listdir(adir)
                   if os.path.isfile(os.path.join(adir, n)) and re.search(r"\w\.arb$", n))
    data = {}
    for name in names:
        text = _read(os.path.join(adir, name))
        try:
            obj = json.loads(text.strip() or "{}")
            data[name] = obj if isinstance(obj, dict) else None
        except ValueError:
            data[name] = None
    tmpl = data.get(cfg["template_arb_file"]) or {}
    tmsgs = {k: v for k, v in tmpl.items() if not k.startswith("@")}
    arbs = []
    for name in names:
        obj = data[name]
        rec = {"file": name, "locale": None, "status": "ok", "messages": 0, "translated": 0}
        arbs.append(rec)
        if obj is None:
            rec["status"] = "invalid_json"
            continue
        floc = filename_locale(name[:-4])
        at = obj.get("@@locale")
        aloc = try_parse_locale(at.replace("-", "_")) if isinstance(at, str) else None
        loc = aloc or floc
        if loc is None:
            rec["status"] = "no_locale"
            continue
        rec["locale"] = loc_str(loc)
        if aloc and floc and aloc != floc:
            rec["status"] = "conflict"
            continue
        rec["_loc"] = loc
        msgs = {k: v for k, v in obj.items() if not k.startswith("@")}
        rec["messages"] = len(msgs)
        if name == cfg["template_arb_file"]:
            rec["template"] = True
            rec["translated"] = len(msgs)
            continue
        rec["translated"] = sum(1 for k, v in msgs.items()
                                if not (k in tmsgs and tmsgs[k] == v))
        if not msgs:
            rec["status"] = "empty"
        elif rec["translated"] == 0:
            rec["status"] = "same_as_template"
    return arbs


# ---------------------------------------------------------------- Dart: supportedLocales

_DART_TOKEN = re.compile(r"r?'''[\s\S]*?'''|r?\"\"\"[\s\S]*?\"\"\"|r?'(?:\\.|[^'\\\n])*'"
                         r"|r?\"(?:\\.|[^\"\\\n])*\"|//[^\n]*|/\*[\s\S]*?\*/")


def strip_comments(src):
    def repl(m):
        t = m.group(0)
        return "\n" * t.count("\n") if t.startswith("/") else t
    return _DART_TOKEN.sub(repl, src)


def take_expr(src, i):
    """Text of the expression starting at i, up to a top-level ',', ')', ']', '}' or ';'."""
    depth, j, n = 0, i, len(src)
    while j < n:
        ch = src[j]
        if ch in "'\"":
            m = _DART_TOKEN.match(src, j)
            if m:
                j = m.end()
                continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth == 0:
                break
            depth -= 1
        elif ch in ",;" and depth == 0:
            break
        j += 1
    return src[i:j].strip()


def split_top(text):
    out, depth, cur, j = [], 0, [], 0
    while j < len(text):
        ch = text[j]
        if ch in "'\"":
            m = _DART_TOKEN.match(text, j)
            if m:
                cur.append(m.group(0))
                j = m.end()
                continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
        j += 1
    out.append("".join(cur))
    return [x.strip() for x in out if x.strip()]


_STR = r"""(?:'([^'\\]*)'|"([^"\\]*)")"""


def _s(m, k):
    return m.group(k) if m.group(k) is not None else m.group(k + 1)


def parse_locale_expr(e):
    """A Locale(...) or Locale.fromSubtags(...) literal, with case kept as Flutter keeps it.

    Flutter's Locale maps deprecated language codes (iw, in, ji) to current ones and treats an
    empty country code as none; it changes nothing else, and its lookups are case-sensitive.
    """
    e = re.sub(r"^const\s+", "", e.strip())
    m = re.fullmatch(r"Locale\s*\(\s*" + _STR + r"\s*(?:,\s*" + _STR + r"\s*)?,?\s*\)", e)
    if m:
        lang = _s(m, 1)
        region = m.group(3) if m.group(3) is not None else m.group(4)
        return (ALIASES.get(lang, lang), None, region or None)
    m = re.fullmatch(r"Locale\.fromSubtags\s*\(([\s\S]*)\)", e)
    if m:
        args = {}
        for part in split_top(m.group(1)):
            a = re.fullmatch(r"(languageCode|scriptCode|countryCode)\s*:\s*" + _STR, part)
            if not a:
                return None
            args[a.group(1)] = _s(a, 2)
        lang = args.get("languageCode") or "und"
        return (ALIASES.get(lang, lang), args.get("scriptCode") or None,
                args.get("countryCode") or None)
    return None


def parse_list(expr):
    """(locales, complete) for a list literal, or None when expr is not one."""
    e = re.sub(r"^const\s+", "", expr.strip())
    e = re.sub(r"^<\s*Locale\s*>\s*", "", e)
    if not (e.startswith("[") and e.endswith("]")):
        return None
    locs, complete = [], True
    for item in split_top(e[1:-1]):
        loc = parse_locale_expr(item)
        if loc is None:
            complete = False
        else:
            locs.append(loc)
    return locs, complete


def dart_files(root):
    lib = os.path.join(root, "lib")
    for dirpath, dirnames, filenames in os.walk(lib):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for f in sorted(filenames):
            if f.endswith(".dart") and not re.search(r"\.(g|freezed|gr)\.dart$", f):
                yield os.path.join(dirpath, f)


def scan_dart(root):
    files = {}
    for path in dart_files(root):
        src = _read(path) or ""
        if GEN_MARKER in src:
            continue
        files[os.path.relpath(path, root).replace(os.sep, "/")] = strip_comments(src)
    args = []
    for rel, src in files.items():
        for m in re.finditer(r"(?<![.\w$])supportedLocales\s*:(?!:)", src):
            expr = take_expr(src, m.end())
            line = src.count("\n", 0, m.start()) + 1
            rec = {"file": rel, "line": line, "expr": expr[:120],
                   "custom_resolution": bool(re.search(
                       r"\blocale(List)?ResolutionCallback\s*:", src)),
                   "easy_localization": "EasyLocalization(" in src}
            parsed = parse_list(expr)
            if parsed is None and re.fullmatch(r"[A-Za-z_$][\w$]*", expr):
                rec["kind"] = "unresolved"
                pat = re.compile(r"\b" + re.escape(expr) + r"\s*=(?![=>])")
                for rel2, src2 in files.items():
                    for d in pat.finditer(src2):
                        p = parse_list(take_expr(src2, d.end()))
                        if p is not None:
                            parsed = p
                            rec["defined_in"] = "%s:%d" % (rel2, src2.count("\n", 0, d.start()) + 1)
                            break
                    if parsed is not None:
                        break
            if parsed is not None:
                rec["kind"] = "literal" if parsed[1] else "partial_literal"
                rec["locales"] = [loc_str(x) for x in parsed[0]]
                rec["_locs"] = parsed[0]
            elif "kind" not in rec:
                rec["kind"] = "expression"
            args.append(rec)
    app_widget = any(re.search(r"\b(?:Material|Cupertino|Widgets)App\s*(?:\.router\s*)?\(", s)
                     for s in files.values())
    return args, app_widget


# ---------------------------------------------------------------- iOS and Android metadata

def read_ios(root):
    out = {"pbxproj": False, "known_regions": None, "info_plist": False,
           "cf_bundle_localizations": None}
    pbx = _read(os.path.join(root, "ios", "Runner.xcodeproj", "project.pbxproj"))
    if pbx is not None:
        out["pbxproj"] = True
        m = re.search(r"knownRegions\s*=\s*\(([^)]*)\)", pbx)
        if m:
            out["known_regions"] = [t.strip().strip('"') for t in m.group(1).split(",")
                                    if t.strip().strip('"')]
    path = os.path.join(root, "ios", "Runner", "Info.plist")
    if os.path.isfile(path):
        out["info_plist"] = True
        try:
            with open(path, "rb") as fh:
                pl = plistlib.load(fh)
            val = pl.get("CFBundleLocalizations")
            if isinstance(val, list):
                out["cf_bundle_localizations"] = [str(x) for x in val]
        except Exception:  # an unreadable plist is reported, not fatal
            out["info_plist_error"] = True
    return out


def read_android(root):
    out = {"manifest": False, "locale_config": None, "config_file": None, "locales": None,
           "generate_locale_config": False}
    main = os.path.join(root, "android", "app", "src", "main")
    man = _read(os.path.join(main, "AndroidManifest.xml"))
    for g in ("build.gradle", "build.gradle.kts"):
        if "generateLocaleConfig" in (_read(os.path.join(root, "android", "app", g)) or ""):
            out["generate_locale_config"] = True
    if man is None:
        return out
    out["manifest"] = True
    m = re.search(r"android:localeConfig\s*=\s*\"@xml/([\w.]+)\"", man)
    if not m:
        return out
    out["locale_config"] = "@xml/" + m.group(1)
    rel = "android/app/src/main/res/xml/%s.xml" % m.group(1)
    out["config_file"] = rel
    xml = _read(os.path.join(root, *rel.split("/")))
    if xml is not None:
        xml = re.sub(r"<!--[\s\S]*?-->", "", xml)
        out["locales"] = re.findall(r"<locale\s[^>]*\bandroid:name\s*=\s*\"([^\"]+)\"", xml)
    return out


# ---------------------------------------------------------------- the check

def check(root, arb_dir=None, template=None):
    cfg = find_config(root, arb_dir, template)
    adir = os.path.join(root, *cfg["arb_dir"].split("/"))
    if not os.path.isdir(adir):
        return None
    arbs = read_arbs(root, cfg)
    # known: every locale gen-l10n generates a class for (an ARB file with no messages of its
    # own still gets one). active: those with at least one message that differs from the
    # template; only these count as translations a platform should offer.
    known, active = {}, {}
    for rec in arbs:
        loc = rec.pop("_loc", None)
        if loc:
            known[loc] = rec["file"]
            if rec["status"] == "ok":
                active[loc] = rec["file"]
    langs = {}
    for loc in sorted(active, key=loc_str):
        langs.setdefault(ALIASES.get(loc[0], loc[0]), []).append(loc_str(loc))
    findings = []

    # Dart: the locales MaterialApp may pick.
    dart, app_widget = scan_dart(root)
    for rec in dart:
        rec["unsupported"] = []
        if rec["easy_localization"] or rec["custom_resolution"] or "_locs" not in rec:
            continue
        for loc in rec["_locs"]:
            if lookup(loc, known) is None:
                rec["unsupported"].append(loc_str(loc))
                findings.append({"kind": "unsupported_language", "locale": loc_str(loc),
                                 "where": "%s:%d" % (rec["file"], rec["line"])})
    usable = [r for r in dart if not r["easy_localization"]]
    unreachable = []
    if usable and all(r["kind"] == "literal" and not r["custom_resolution"] for r in usable):
        reached = {lookup(loc, known) for r in usable for loc in r["_locs"]}
        unreachable = sorted(loc_str(x) for x in active if x not in reached)
        for loc in unreachable:
            findings.append({"kind": "unreachable", "locale": loc,
                             "where": ", ".join("%s:%d" % (r["file"], r["line"])
                                                for r in usable)})
    if not dart and app_widget and len(active) > 1:
        # No supportedLocales anywhere: MaterialApp, CupertinoApp and WidgetsApp then default
        # to <Locale>[Locale('en', 'US')].
        reached = {lookup(("en", None, "US"), known)}
        unreachable = sorted(loc_str(x) for x in active if x not in reached)
        for loc in unreachable:
            findings.append({"kind": "default_supported_locales", "locale": loc,
                             "where": "no supportedLocales argument under lib/"})
    dart_status = (("default_en_US" if app_widget else "no_app_widget") if not dart else
                   "no_supported_locales_argument" if not usable else
                   "checked" if all(r["kind"] == "literal" and not r["custom_resolution"]
                                    for r in usable) else "not_all_literal")
    for rec in dart:
        rec.pop("_locs", None)

    # iOS: knownRegions, and CFBundleLocalizations when the app sets it.
    ios = read_ios(root)
    ios["not_declared"], ios["plist_not_declared"], ios["no_translation"] = [], [], []
    if ios["known_regions"] is not None:
        have = {language(t) for t in ios["known_regions"] if t != "Base"}
        for lang in sorted(langs):
            if lang not in have:
                ios["not_declared"].append(lang)
                findings.append({"kind": "ios_not_declared", "language": lang,
                                 "arb_locales": langs[lang]})
        ios["no_translation"] = sorted(have - set(langs))
    if ios["cf_bundle_localizations"] is not None:
        have = {language(t) for t in ios["cf_bundle_localizations"]}
        for lang in sorted(langs):
            if lang not in have:
                ios["plist_not_declared"].append(lang)
                findings.append({"kind": "plist_not_declared", "language": lang,
                                 "arb_locales": langs[lang]})

    # Android 13+: the per-app language list.
    android = read_android(root)
    android["not_declared"], android["no_translation"] = [], []
    if android["locales"] is not None:
        have = {language(t) for t in android["locales"]}
        for lang in sorted(langs):
            if lang not in have:
                android["not_declared"].append(lang)
                findings.append({"kind": "android_not_declared", "language": lang,
                                 "arb_locales": langs[lang]})
        android["no_translation"] = sorted(have - set(langs))

    by_kind = {}
    for f in findings:
        by_kind[f["kind"]] = by_kind.get(f["kind"], 0) + 1
    return {"tool": "flutter_l10n", "version": __version__, "config": cfg, "arb": arbs,
            "active_locales": sorted(loc_str(x) for x in active),
            "dart": {"status": dart_status, "supported_locales_arguments": dart,
                     "unreachable": unreachable},
            "ios": ios, "android": android,
            "findings": findings, "findings_by_kind": by_kind}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("root")
    ap.add_argument("--arb-dir")
    ap.add_argument("--template-arb-file")
    ap.add_argument("--strict", action="store_true", help="exit 1 when there is a finding")
    a = ap.parse_args(argv)
    if not os.path.isfile(os.path.join(a.root, "pubspec.yaml")):
        print(json.dumps({"error": "no pubspec.yaml in %s" % a.root}))
        return 2
    res = check(a.root, a.arb_dir, a.template_arb_file)
    if res is None:
        print(json.dumps({"error": "no ARB directory"}))
        return 2
    print(json.dumps(res, indent=1, ensure_ascii=False))
    return 1 if a.strict and res["findings"] else 0


if __name__ == "__main__":
    sys.exit(main())
