# android_localefilters: translated values-* folders that an Android app's own
# resConfigs / resourceConfigurations / localeFilters list keeps out of the build,
# and moko-resources locale folders whose script is lost on Android.
# Standard library only, no network. Source reading, not a build test.
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
"""Find Android translations that the app's locale filter drops.

The Android Gradle Plugin passes resConfigs / resourceConfigurations /
androidResources.localeFilters to aapt2's -c option. aapt2 (frameworks/base
tools/aapt2/filter/ConfigFilter.cpp, AxisConfigFilter::Match) keeps a locale
folder only if:
  * its locale equals a filter entry exactly, or
  * the folder names a language with no region and no variant, a filter entry
    has the same language, and the scripts match (ScriptsMatch: a missing
    script is computed from language + region; unknown -> match).
So a filter of "pt" drops values-pt-rBR, "zh" drops values-zh-rTW and
values-b+zh+Hant, and "sr" drops values-b+sr+Latn.

moko-resources (dev.icerock.mobile.multiplatform-resources, LanguageType.kt)
turns a locale folder such as moko-resources/zh-Hant into the Android folder
values-<language>[-r<COUNTRY>] built from java.util.Locale.forLanguageTag, so
the script is dropped: zh-Hant becomes values-zh, and zh-Hans + zh-Hant in one
source set both write values-zh/multiplatform_strings.xml.
"""
import argparse
import json
import os
import re
import sys

__version__ = "0.2.0"

KEY_RE = re.compile(r"\b(resConfigs|resConfig|resourceConfigurations|localeFilters)\b")
GEN_RE = re.compile(r"\bgenerateLocaleConfig\s*(?:=\s*)?true\b")
APP_RE = re.compile(r"android[.-]application")
PROJ_RE = re.compile(r"project\(\s*(?:path\s*[:=]\s*)?[\"'](:[^\"']*)[\"']")
PROJECTS_RE = re.compile(r"\bprojects((?:\.[A-Za-z_][A-Za-z0-9_]*)+)")
MOKO_RE = re.compile(r"moko|multiplatform-resources", re.I)
MOKO_NAME_RE = re.compile(r"[A-Za-z]{2,3}(?:[-_+].*)?|b\+.*")
MOKO_ROOTS = (("moko-resources",), ("resources", "MR"))
MOKO_LEGACY = {"he": "iw", "yi": "ji", "id": "in"}
LC_RE = re.compile(r"android:localeConfig\s*=\s*\"@xml/([A-Za-z0-9_]+)\"")
LOCALE_TAG_RE = re.compile(r"<locale\s[^>]*?android:name\s*=\s*\"([^\"]+)\"")
DENSITY_RE = re.compile(r"ldpi|mdpi|tvdpi|hdpi|xhdpi|xxhdpi|xxxhdpi|nodpi|anydpi|\d+dpi")
LIT_RE = re.compile(r"\"x*\"|'x*'")
IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
ALLOWED_IDENTS = {"listOf", "setOf", "mutableListOf", "mutableSetOf", "arrayOf",
                  "addAll", "add", "plus", "plusAssign"}
NAMED_BLOCK_CALLS = {"create", "register", "getByName", "maybeCreate", "named"}
SKIP_DIRS = {"build", "node_modules"}
LEGACY = {"iw": "he", "in": "id", "ji": "yi"}

# Likely script of a language (CLDR likely subtags), for aapt2's ScriptsMatch.
# A language missing here is treated as "script unknown", which aapt2 counts as
# a match, so a gap in this table can only hide a finding, never invent one.
LIKELY_SCRIPT = {
    "af": "Latn", "am": "Ethi", "ar": "Arab", "as": "Beng", "az": "Latn",
    "be": "Cyrl", "bg": "Cyrl", "bn": "Beng", "bo": "Tibt", "br": "Latn",
    "bs": "Latn", "ca": "Latn", "ckb": "Arab", "cs": "Latn", "cy": "Latn",
    "da": "Latn", "de": "Latn", "el": "Grek", "en": "Latn", "eo": "Latn",
    "es": "Latn", "et": "Latn", "eu": "Latn", "fa": "Arab", "fi": "Latn",
    "fil": "Latn", "fr": "Latn", "ga": "Latn", "gl": "Latn", "gu": "Gujr",
    "ha": "Latn", "he": "Hebr", "hi": "Deva", "hr": "Latn", "hu": "Latn",
    "hy": "Armn", "id": "Latn", "is": "Latn", "it": "Latn", "ja": "Jpan",
    "ka": "Geor", "kk": "Cyrl", "km": "Khmr", "kn": "Knda", "ko": "Kore",
    "ks": "Arab", "ky": "Cyrl", "lo": "Laoo", "lt": "Latn", "lv": "Latn",
    "mk": "Cyrl", "ml": "Mlym", "mn": "Cyrl", "mr": "Deva", "ms": "Latn",
    "my": "Mymr", "nb": "Latn", "ne": "Deva", "nl": "Latn", "nn": "Latn",
    "no": "Latn", "oc": "Latn", "or": "Orya", "pa": "Guru", "pl": "Latn",
    "ps": "Arab", "pt": "Latn", "ro": "Latn", "ru": "Cyrl", "sd": "Arab",
    "si": "Sinh", "sk": "Latn", "sl": "Latn", "sq": "Latn", "sr": "Cyrl",
    "sv": "Latn", "sw": "Latn", "ta": "Taml", "te": "Telu", "th": "Thai",
    "tk": "Latn", "tr": "Latn", "tt": "Cyrl", "ug": "Arab", "uk": "Cyrl",
    "ur": "Arab", "uz": "Latn", "vi": "Latn", "yi": "Hebr", "yue": "Hant",
    "zh": "Hans", "zu": "Latn",
}
REGION_SCRIPT = {
    ("zh", "TW"): "Hant", ("zh", "HK"): "Hant", ("zh", "MO"): "Hant",
    ("sr", "ME"): "Latn", ("uz", "AF"): "Arab", ("az", "IR"): "Arab",
    ("pa", "PK"): "Arab", ("sd", "IN"): "Deva", ("mn", "CN"): "Mong",
    ("kk", "CN"): "Arab", ("yue", "CN"): "Hans",
}


# ---------------------------------------------------------------- Gradle text

def strip_comments(text):
    """Blank out // and /* */ comments (newlines kept), leaving strings alone."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join("\n" if ch == "\n" else " " for ch in text[i:j]))
            i = j
            continue
        if c in "\"'":
            j = _string_end(text, i)
            out.append(text[i:j])
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out)


def _string_end(text, i):
    """Index just past the string literal that opens at i."""
    n = len(text)
    q = text[i] * 3 if text.startswith(text[i] * 3, i) else text[i]
    j = i + len(q)
    while j < n:
        if text.startswith(q, j):
            return j + len(q)
        if len(q) == 1 and text[j] == "\n":
            return j
        j += 2 if text[j] == "\\" else 1
    return n


def mask_strings(text):
    """Replace every character inside string literals with 'x' (same length)."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        if text[i] in "\"'":
            q = 3 if text.startswith(text[i] * 3, i) else 1
            j = _string_end(text, i)
            closed = j <= n and text[j - q:j] == text[i] * q and j - q > i
            stop = j - q if closed else j
            for k in range(i + q, stop):
                if out[k] != "\n":
                    out[k] = "x"
            i = max(j, i + 1)
            continue
        i += 1
    return "".join(out)


def _block_name(masked, clean, i):
    """Name of the block whose '{' is at i: 'defaultConfig', or 'play' for create("play")."""
    j = i - 1
    while j >= 0 and masked[j] in " \t\r\n":
        j -= 1
    args = ""
    if j >= 0 and masked[j] == ")":
        depth, k = 0, j
        while k >= 0:
            if masked[k] == ")":
                depth += 1
            elif masked[k] == "(":
                depth -= 1
                if depth == 0:
                    break
            k -= 1
        args = clean[k + 1:j]
        j = k - 1
        while j >= 0 and masked[j] in " \t":
            j -= 1
    end = j + 1
    while j >= 0 and (masked[j].isalnum() or masked[j] == "_"):
        j -= 1
    name = masked[j + 1:end]
    if name in NAMED_BLOCK_CALLS:
        m = re.search(r"[\"']([^\"']+)[\"']", args)
        if m:
            name = m.group(1)
    return name


def _statement_end(masked, q):
    depth, i, n = 0, q, len(masked)
    while i < n:
        c = masked[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                break
            depth -= 1
        elif c == ";" and depth == 0:
            break
        elif c == "\n" and depth == 0:
            before = masked[q:i].rstrip()
            if not before or before[-1] not in ",+=(":
                break
        i += 1
    return i


def extract_filters(text):
    """Literal locale-filter entries in one Gradle build file (Groovy or Kotlin DSL)."""
    clean = strip_comments(text)
    masked = mask_strings(clean)
    res = {"global": [], "flavors": {}, "dynamic": [],
           "generate_locale_config": bool(GEN_RE.search(masked))}
    keys = [(m.start(), m.end()) for m in KEY_RE.finditer(masked)]
    found = []
    ki, stack = 0, []
    for i, c in enumerate(masked):
        while ki < len(keys) and keys[ki][0] == i:
            found.append((keys[ki], list(stack)))
            ki += 1
        if c == "{":
            stack.append(_block_name(masked, clean, i))
        elif c == "}" and stack:
            stack.pop()
    for (start, end), path in found:
        stop = _statement_end(masked, end)
        smask, sclean = masked[end:stop], clean[end:stop]
        literals, dynamic = [], False
        for m in LIT_RE.finditer(smask):
            lit = sclean[m.start() + 1:m.end() - 1]
            if "$" in lit:
                dynamic = True
            for part in lit.split(","):
                if part.strip():
                    literals.append(part.strip())
        rest = [w for w in IDENT_RE.findall(LIT_RE.sub(" ", smask)) if w not in ALLOWED_IDENTS]
        if rest:
            dynamic = True
        scope = "global"
        if "productFlavors" in path:
            k = path.index("productFlavors")
            if k + 1 < len(path):
                scope = "flavor:" + path[k + 1]
        if dynamic:
            snippet = " ".join((masked[start:end] + sclean).split())[:100]
            res["dynamic"].append({"scope": scope, "statement": snippet})
        elif not literals:
            continue  # a read such as println(resourceConfigurations)
        elif scope == "global":
            res["global"].extend(literals)
        else:
            res["flavors"].setdefault(scope[len("flavor:"):], []).extend(literals)
    return res


def variants(filters):
    """Entries in force per variant: defaultConfig entries plus each flavor's own."""
    g, fl = filters["global"], filters["flavors"]
    if not fl:
        return {"all variants": list(g)} if g else {}
    out = {name: list(g) + list(f) for name, f in fl.items()}
    if g:
        out["flavors without their own list"] = list(g)
    return out


def is_app_module(text):
    for line in strip_comments(text).splitlines():
        if APP_RE.search(line) and "apply false" not in line:
            return True
    return False


# ------------------------------------------------------------- locales, aapt2

def _parse_locale_tokens(tokens, i):
    """Parse an aapt2 locale qualifier starting at tokens[i]: (lang, script, region, variant)."""
    if i >= len(tokens):
        return None, i
    tok = tokens[i]
    if tok[:2].lower() == "b+":
        parts = tok[2:].split("+")
        if not re.fullmatch(r"[A-Za-z]{2,3}", parts[0]):
            return None, i
        lang, script, region, variant = parts[0].lower(), "", "", ""
        for p in parts[1:]:
            if re.fullmatch(r"[A-Za-z]{4}", p) and not script and not region:
                script = p.title()
            elif re.fullmatch(r"[A-Za-z]{2}|\d{3}", p) and not region:
                region = p.upper()
            else:
                variant = p.lower()
        return (lang, script, region, variant), i + 1
    if re.fullmatch(r"[A-Za-z]{2,3}", tok) and tok.lower() != "car":
        lang, region, j = tok.lower(), "", i + 1
        if j < len(tokens) and re.fullmatch(r"[rR](?:[A-Za-z]{2}|\d{3})", tokens[j]):
            region = tokens[j][1:].upper()
            j += 1
        return (lang, "", region, ""), j
    return None, i


def parse_folder_locale(qualifiers):
    """Locale of a values-<qualifiers> folder, or None. MCC/MNC come first."""
    tokens = qualifiers.split("-")
    i = 0
    while i < len(tokens) and re.fullmatch(r"(?:mcc|mnc)\d+", tokens[i].lower()):
        i += 1
    return _parse_locale_tokens(tokens, i)[0]


def parse_filter_entry(entry):
    """('locale', tuple) | ('density', s) | ('invalid', s) | ('other', s)."""
    e = entry.strip()
    if DENSITY_RE.fullmatch(e):
        return "density", e
    tokens = e.split("-")
    loc, used = _parse_locale_tokens(tokens, 0)
    if loc and used == len(tokens):
        return "locale", loc
    if loc and all(re.fullmatch(r"[A-Za-z]{2}|\d{3}|[A-Z][a-z]{3}", t) for t in tokens[used:]):
        return "invalid", e  # BCP-47 form such as en-US: aapt2 -c wants en-rUS or b+en+US
    if re.fullmatch(r"[a-z]{2,3}_[A-Za-z0-9]{2,4}", e):
        return "invalid", e
    return "other", e


def parse_bcp47(tag):
    parts = [p for p in re.split(r"[-_]", tag.strip()) if p]
    if not parts:
        return None
    return _parse_locale_tokens(["b+" + "+".join(parts)], 0)[0]


def fmt(loc):
    lang, script, region, variant = loc
    if script or variant:
        return "b+" + "+".join(p for p in (lang, script, region, variant) if p)
    return lang + ("-r" + region if region else "")


def norm(loc):
    return (LEGACY.get(loc[0], loc[0]),) + tuple(loc[1:])


def likely_script(lang, region=""):
    lang = LEGACY.get(lang, lang)
    return REGION_SCRIPT.get((lang, region)) or LIKELY_SCRIPT.get(lang, "")


def scripts_match(cfg, ent):
    """aapt2 ScriptsMatch(config=folder, entry=filter)."""
    cs, es = cfg[1], ent[1]
    if not cs and not es:
        return True
    if not cs:
        cs = likely_script(cfg[0], cfg[2])
        if not cs:
            return True
    elif not es:
        es = likely_script(ent[0], ent[2])
        if not es:
            return True
    return cs == es


def kept(loc, filters):
    """aapt2 AxisConfigFilter::Match on the locale axis."""
    nl = norm(loc)
    for f in filters:
        if nl == norm(f):
            return True
        if (not loc[2] and not loc[3] and nl[0] == norm(f)[0]
                and scripts_match(loc, f)):
            return True
    return False


def drop_reason(loc, filters):
    same = [f for f in filters if norm(f)[0] == norm(loc)[0]]
    if not same:
        return "language_not_listed"
    if loc[2]:
        return "region_not_listed"
    if loc[1] or any(f[1] for f in same):
        return "script_mismatch"
    return "variant_not_listed"


def analyse_variant(entries, locales):
    out = {"locale_entries": [], "density": [], "invalid": [], "other": [], "dropped": {}}
    for e in entries:
        kind, val = parse_filter_entry(e)
        out["locale_entries" if kind == "locale" else kind].append(val)
    if out["other"]:
        out["dropped"] = None  # other axes (night, land, ...) are not modelled
    elif out["locale_entries"]:
        for loc in locales:
            if not kept(loc, out["locale_entries"]):
                out["dropped"][loc] = drop_reason(loc, out["locale_entries"])
    return out


# ------------------------------------------------------------- moko-resources

def java_locale(tag):
    """(language, script, country) as java.util.Locale.forLanguageTag reads tag.

    The first ill-formed subtag and everything after it are ignored, so an
    ill-formed first subtag (pt_BR, b+zh+Hant) gives ('', '', '').
    Extlang subtags are not modelled.
    """
    subs = tag.split("-")
    if not re.fullmatch(r"[A-Za-z]{2,8}", subs[0]):
        return "", "", ""
    lang, script, country, i = subs[0].lower(), "", "", 1
    if i < len(subs) and re.fullmatch(r"[A-Za-z]{4}", subs[i]):
        script = subs[i].title()
        i += 1
    if i < len(subs) and re.fullmatch(r"[A-Za-z]{2}|\d{3}", subs[i]):
        country = subs[i].upper()
    return lang, script, country


def moko_android(name):
    """For a moko locale folder name: (Android values folder, locale tuple, java locale).

    None for the base folder. Mirrors LanguageType.fromFileName (replace "-r"
    with "-") and Locale.androidResourcesDir (language, then -r + country).
    """
    if name == "base":
        return None
    jl = java_locale(name.replace("-r", "-"))
    lang = MOKO_LEGACY.get(jl[0], jl[0])
    folder = "values-" + lang + ("-r" + jl[2] if jl[2] else "")
    return folder, (lang, "", jl[2], ""), jl


def moko_dirs(mod_dir, text):
    """moko-resources roots of a module whose build file mentions moko."""
    if not MOKO_RE.search(strip_comments(text)):
        return []
    src = os.path.join(mod_dir, "src")
    out = []
    if os.path.isdir(src):
        for ss in sorted(os.listdir(src)):
            for parts in MOKO_ROOTS:
                d = os.path.join(src, ss, *parts)
                if os.path.isdir(d):
                    out.append(d)
    return out


def _has_moko_strings(d):
    for fn in sorted(os.listdir(d)):
        p = os.path.join(d, fn)
        if fn.endswith(".xml") and os.path.isfile(p):
            t = _read(p)
            if "<string" in t or "<plural" in t:
                return True
    return False


def moko_locales(dirs, root):
    """Translations moko generates for Android, and what happens to each folder.

    Returns (translations {locale: [folder]}, entries [dict]) where each entry
    is one translated moko folder with the Android folder it becomes.
    """
    trans, entries = {}, []
    for r in dirs:
        for name in sorted(os.listdir(r)):
            d = os.path.join(r, name)
            if not os.path.isdir(d) or not MOKO_NAME_RE.fullmatch(name):
                continue
            m = moko_android(name)
            if m is None or not _has_moko_strings(d):
                continue
            folder, loc, jl = m
            entries.append({"root": _rel(r, root), "folder": _rel(d, root), "name": name,
                            "android": folder, "java": jl})
            if loc[0]:
                trans.setdefault(loc, []).append(_rel(d, root))
    return trans, entries


def moko_findings(entries):
    """script_dropped, collision and unparsable cases among moko folders."""
    out, groups = [], {}
    for e in entries:
        groups.setdefault((e["root"], e["android"]), []).append(e)
    for e in entries:
        lang, script, country = e["java"]
        if not lang:
            out.append({"kind": "moko_unparsable", "folder": e["folder"],
                        "android_folder": e["android"]})
            continue
        if script and likely_script(lang, country) != script:
            # zh-Hans -> values-zh or zh-Hant-TW -> values-zh-rTW loses nothing:
            # Android infers that same script from language + region.
            out.append({"kind": "moko_script_dropped", "folder": e["folder"],
                        "script": script, "android_folder": e["android"]})
    for (root, android), group in sorted(groups.items()):
        if android == "values-":
            continue
        if len({tuple(e["java"]) for e in group}) > 1:
            out.append({"kind": "moko_collision", "android_folder": android, "root": root,
                        "folders": [e["folder"] for e in group]})
    return out


# ------------------------------------------------------------------ the tree

def _read(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _rel(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def find_build_files(root):
    out = []
    for dp, dns, fns in os.walk(root):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not d.startswith("."))
        for fn in ("build.gradle", "build.gradle.kts"):
            if fn in fns:
                out.append(os.path.join(dp, fn))
    return out


def _build_file(d):
    for fn in ("build.gradle.kts", "build.gradle"):
        p = os.path.join(d, fn)
        if os.path.isfile(p):
            return p
    return None


def gradle_root(mod_dir, root):
    """Nearest folder at or above mod_dir (up to root) holding a settings file."""
    d, root = os.path.normpath(mod_dir), os.path.normpath(root)
    while True:
        for fn in ("settings.gradle.kts", "settings.gradle"):
            if os.path.isfile(os.path.join(d, fn)):
                return d
        if d == root or os.path.dirname(d) == d:
            return root
        d = os.path.dirname(d)


def _accessor_key(name):
    """Gradle's type-safe accessor turns some-lib and some_lib into someLib."""
    return re.sub(r"[-_.]", "", name).lower()


def resolve_accessor(groot, segments):
    """Folder of projects.a.bC (a/b-c), or None. The deepest folder with a build file wins."""
    cur, best = groot, None
    for seg in segments:
        nxt = None
        try:
            names = sorted(os.listdir(cur))
        except OSError:
            break
        for n in names:
            p = os.path.join(cur, n)
            if (n not in SKIP_DIRS and not n.startswith(".") and os.path.isdir(p)
                    and _accessor_key(n) == seg.lower()):
                nxt = p
                break
        if nxt is None:
            break
        cur = nxt
        if _build_file(cur):
            best = cur
    return best


def dep_modules(mod_dir, root, text):
    """Project modules reached through project(":a:b") or projects.a.b (transitively)."""
    groot = gradle_root(mod_dir, root)
    bases = [os.path.dirname(mod_dir), groot, os.path.normpath(root)]
    seen, queue = [], [text]
    while queue:
        t = strip_comments(queue.pop(0))
        cands = []
        for m in PROJ_RE.finditer(t):
            parts = [p for p in m.group(1).split(":") if p]
            if not parts:
                continue
            for base in bases:
                d = os.path.normpath(os.path.join(base, *parts))
                if os.path.isdir(d):
                    cands.append(d)
                    break
        for m in PROJECTS_RE.finditer(t):
            d = resolve_accessor(groot, m.group(1).split(".")[1:])
            if d:
                cands.append(os.path.normpath(d))
        for d in cands:
            if d in seen or d == os.path.normpath(mod_dir):
                continue
            seen.append(d)
            bf = _build_file(d)
            if bf:
                queue.append(_read(bf))
    return seen


def module_res_dirs(mod_dir):
    src = os.path.join(mod_dir, "src")
    out = []
    if os.path.isdir(src):
        for ss in sorted(os.listdir(src)):
            r = os.path.join(src, ss, "res")
            if os.path.isdir(r):
                out.append(r)
    return out


def _has_strings(d):
    for fn in sorted(os.listdir(d)):
        p = os.path.join(d, fn)
        if fn.endswith(".xml") and os.path.isfile(p):
            t = _read(p)
            if "<string" in t or "<plurals" in t:
                return True
    return False


def translated_locales(res_dirs, root):
    found = {}
    for r in res_dirs:
        for name in sorted(os.listdir(r)):
            d = os.path.join(r, name)
            if not name.startswith("values-") or not os.path.isdir(d):
                continue
            loc = parse_folder_locale(name[len("values-"):])
            if loc is None or not _has_strings(d):
                continue
            found.setdefault(loc, []).append(_rel(d, root))
    return found


def declared_locales(mod_dir, root):
    """(path, [locale]) from the manifest's android:localeConfig file, or (None, None)."""
    man = os.path.join(mod_dir, "src", "main", "AndroidManifest.xml")
    if not os.path.isfile(man):
        return None, None
    m = LC_RE.search(re.sub(r"<!--.*?-->", "", _read(man), flags=re.S))
    if not m:
        return None, None
    cands = [os.path.join(mod_dir, "src", "main", "res", "xml", m.group(1) + ".xml")]
    cands += [os.path.join(r, "xml", m.group(1) + ".xml") for r in module_res_dirs(mod_dir)]
    for p in cands:
        if os.path.isfile(p):
            body = re.sub(r"<!--.*?-->", "", _read(p), flags=re.S)
            return _rel(p, root), [parse_bcp47(t) for t in LOCALE_TAG_RE.findall(body)]
    return None, None


def check(root):
    root = os.path.abspath(root)
    rep = {"tool": "android_localefilters " + __version__, "modules": [],
           "findings": [], "notes": []}
    moko_seen = set()
    for bf in find_build_files(root):
        text = _read(bf)
        if not is_app_module(text):
            continue
        mod_dir = os.path.dirname(bf)
        mrel = _rel(mod_dir, root) if mod_dir != root else "."
        filters = extract_filters(text)
        deps = dep_modules(mod_dir, root, text)
        res_dirs = module_res_dirs(mod_dir) + [r for d in deps for r in module_res_dirs(d)]
        trans = translated_locales(res_dirs, root)
        mdirs = moko_dirs(mod_dir, text)
        for d in deps:
            dbf = _build_file(d)
            if dbf:
                mdirs += moko_dirs(d, _read(dbf))
        mtrans, mentries = moko_locales(mdirs, root)
        for loc, folders in mtrans.items():
            trans.setdefault(loc, []).extend(folders)
        mod = {"module": mrel, "build_file": _rel(bf, root),
               "filters": {"global": filters["global"], "flavors": filters["flavors"]},
               "generate_locale_config": filters["generate_locale_config"],
               "dependency_modules": [_rel(d, root) for d in deps],
               "translations": {fmt(k): v for k, v in sorted(trans.items())},
               "moko": {e["folder"]: e["android"] for e in mentries},
               "variants": {}}
        rep["modules"].append(mod)
        for f in moko_findings(mentries):
            key = json.dumps(f, sort_keys=True)
            if key not in moko_seen:
                moko_seen.add(key)
                rep["findings"].append(dict(f, module=mrel))
        if filters["dynamic"]:
            rep["notes"].append({"kind": "dynamic_filter", "module": mrel,
                                 "statements": filters["dynamic"]})
            continue
        lc_path, declared = declared_locales(mod_dir, root)
        seen_notes = set()
        for vname, entries in sorted(variants(filters).items()):
            a = analyse_variant(entries, trans)
            mod["variants"][vname] = {
                "entries": entries,
                "dropped": None if a["dropped"] is None else
                {fmt(k): r for k, r in sorted(a["dropped"].items())}}
            for e in a["invalid"]:
                if ("invalid", e) not in seen_notes:
                    seen_notes.add(("invalid", e))
                    rep["notes"].append({"kind": "invalid_entry", "module": mrel, "entry": e})
            if a["dropped"] is None:
                rep["notes"].append({"kind": "not_modelled", "module": mrel,
                                     "variant": vname, "entries": a["other"]})
                continue
            for loc, reason in sorted(a["dropped"].items()):
                rep["findings"].append({"kind": "filtered_out", "module": mrel,
                                        "variant": vname, "locale": fmt(loc),
                                        "reason": reason, "folders": trans[loc]})
            for d in declared or []:
                if d is None:
                    continue
                same = [k for k in trans if norm(k)[0] == norm(d)[0]]
                if same and all(k in a["dropped"] for k in same):
                    rep["findings"].append({"kind": "declared_but_filtered", "module": mrel,
                                            "variant": vname, "locale": fmt(d),
                                            "locale_config": lc_path})
    return rep


def render(rep):
    lines = [rep["tool"]]
    for m in rep["modules"]:
        lines.append("app module %s (%s)" % (m["module"], m["build_file"]))
        lines.append("  translations: %s" % (", ".join(m["translations"]) or "none"))
        if m["generate_locale_config"]:
            lines.append("  generateLocaleConfig is on")
        for v, d in m["variants"].items():
            lines.append("  %s: %s" % (v, ", ".join(d["entries"])))
    for f in rep["findings"]:
        k = f["kind"]
        if k == "filtered_out":
            lines.append("FILTERED OUT %s [%s] %s: %s (%s)" % (
                f["locale"], f["variant"], f["module"], ", ".join(f["folders"]), f["reason"]))
        elif k == "declared_but_filtered":
            lines.append("DECLARED BUT FILTERED %s [%s] %s: listed in %s, no folder of "
                         "that language survives" % (f["locale"], f["variant"], f["module"],
                                                     f["locale_config"]))
        elif k == "moko_script_dropped":
            lines.append("MOKO SCRIPT DROPPED %s: becomes %s on Android, without %s" % (
                f["folder"], f["android_folder"], f["script"]))
        elif k == "moko_collision":
            lines.append("MOKO COLLISION %s: %s all write it; only one survives" % (
                f["android_folder"], ", ".join(f["folders"])))
        else:
            lines.append("MOKO UNPARSABLE %s: becomes %s, which aapt2 rejects" % (
                f["folder"], f["android_folder"]))
    for n in rep["notes"]:
        lines.append("note: " + json.dumps(n, sort_keys=True))
    lines.append("findings: %d" % len(rep["findings"]))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("root")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 on any finding")
    a = ap.parse_args(argv)
    rep = check(a.root)
    print(json.dumps(rep, indent=1, sort_keys=True) if a.json else render(rep))
    if not rep["modules"]:
        return 2
    if a.strict and rep["findings"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
