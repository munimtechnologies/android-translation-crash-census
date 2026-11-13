#!/usr/bin/env python3
# astro_locales: translated page folders that Astro's own i18n helpers disagree on.
# Standard library only, no network. Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
"""Check an Astro site (core i18n routing, not Starlight) for locale folders that
Astro.currentLocale and getRelativeLocaleUrl() treat differently.

What Astro does (read in withastro/astro at commit 5b7c327, astro 7.4.12; this is source
reading, not a build test):
- src/i18n/utils.ts, computeCurrentLocale() (Astro.currentLocale): for each path segment, a
  string locale is skipped unless `segment.includes(locale)` (case- and separator-sensitive),
  and only then compared after normalizeTheLocale(). An object locale matches if
  `locale.path === segment` (exact) or if any of its codes equals the segment after
  normalizeTheLocale(). No match in any segment means the default locale.
- src/i18n/path.ts, normalizeTheLocale(): `_` becomes `-`, then lower case.
- src/i18n/index.ts, getLocaleRelativeUrl() (getRelativeLocaleUrl, getAbsoluteLocaleUrl and the
  URL lists): `normalizeLocale = true` by default, so the URL segment is normalizeTheLocale() of
  the string locale, or of the object locale's `path`.
- src/core/config/schemas/refined-validators.ts: no check on the case or separators of locales.
So for a string locale such as 'pt-BR' or 'fr_CA', no folder name satisfies both helpers: a
folder named exactly like the locale (which the docs ask for) gets links to /pt-br/ or /fr-ca/,
and a folder named like those links gets Astro.currentLocale = the default locale. The object
form { path: 'pt-br', codes: ['pt-BR'] } satisfies both.

Usage: python astro_locales.py <site root> [--locales en,pt-BR,spanish=es|es-MX]
       [--default en] [--pages-dir src/pages] [--strict]
Prints one JSON report. Exit 0; with --strict, 1 if there is any finding; 2 if <root> has no
astro.config.* and --locales is not given.
"""
import argparse
import json
import os
import re
import sys

ASTRO_SHA = "5b7c3275cf2f4aa0d1685495f943cb19039a2e83"
ASTRO_VERSION = "7.4.12"

CONFIG_NAMES = ("astro.config.mjs", "astro.config.ts", "astro.config.mts", "astro.config.js",
                "astro.config.cjs", "astro.config.cts")
PAGE_EXTS = (".astro", ".md", ".mdx", ".markdown", ".html", ".js", ".ts")
SOURCE_EXTS = (".astro", ".ts", ".js", ".mjs", ".mts", ".tsx", ".jsx", ".mdx", ".vue",
               ".svelte")

# ISO 639-1 codes, plus a few common 3-letter primary tags.
LANG2 = frozenset((
    "aa ab ae af ak am an ar as av ay az ba be bg bh bi bm bn bo br bs ca ce ch co cr cs cu"
    " cv cy da de dv dz ee el en eo es et eu fa ff fi fj fo fr fy ga gd gl gn gu gv ha he hi"
    " ho hr ht hu hy hz ia id ie ig ii ik io is it iu ja jv ka kg ki kj kk kl km kn ko kr ks"
    " ku kv kw ky la lb lg li ln lo lt lu lv mg mh mi mk ml mn mr ms mt my na nb nd ne ng nl"
    " nn no nr nv ny oc oj om or os pa pi pl ps pt qu rm rn ro ru rw sa sc sd se sg si sk sl"
    " sm sn so sq sr ss st su sv sw ta te tg th ti tk tl tn to tr ts tt tw ty ug uk ur uz ve"
    " vi vo wa wo xh yi yo za zh zu").split())
LANG3 = frozenset("ast ckb fil haw kab yue".split())

TAG_RE = re.compile(r"^([A-Za-z]{2,3})(?:[-_]([A-Za-z]{4}))?(?:[-_]([A-Za-z]{2}|[0-9]{3}))?$")
I18N_RE = re.compile(r"(?<![\w$.])i18n\s*:\s*\{")
I18N_REF_RE = re.compile(r"(?<![\w$.])i18n\b")
LOCALES_ARR_RE = re.compile(r"(?<![\w$.])locales\s*:\s*\[")
DEFAULT_RE = re.compile(r"(?<![\w$.])defaultLocale\s*:\s*(['\"`])")
PREFIX_DEFAULT_RE = re.compile(r"(?<![\w$.])prefixDefaultLocale\s*:\s*true\b")
PATH_RE = re.compile(r"(?<![\w$.])path\s*:\s*(['\"`])")
CODES_RE = re.compile(r"(?<![\w$.])codes\s*:\s*\[")
NORMALIZE_FALSE_RE = re.compile(r"normalizeLocale\s*:\s*false\b")
FINDINGS = ("current_locale_wrong", "links_miss", "links_case_only")


# ---- ports of Astro's own functions (withastro/astro@5b7c327, MIT) ----

def normalize_the_locale(locale):
    """Port of normalizeTheLocale() in src/i18n/path.ts."""
    return locale.replace("_", "-").lower()


def normalize_the_path(path):
    """Port of normalizeThePath() in src/i18n/path.ts."""
    return path[:-5] if path.endswith(".html") else path


def _first_code(entry):
    codes = entry.get("codes") or []
    return codes[0] if codes else None


def compute_current_locale(pathname, locales, default_locale):
    """Port of computeCurrentLocale() in src/i18n/utils.ts (Astro.currentLocale)."""
    for segment in [normalize_the_path(s) for s in pathname.split("/")]:
        for locale in locales:
            if isinstance(locale, str):
                if locale not in segment:
                    continue
                if normalize_the_locale(locale) == normalize_the_locale(segment):
                    return locale
            else:
                if locale["path"] == segment:
                    return _first_code(locale)
                for code in locale.get("codes") or []:
                    if normalize_the_locale(code) == normalize_the_locale(segment):
                        return code
    for locale in locales:
        if isinstance(locale, str):
            if locale == default_locale:
                return locale
        elif locale["path"] == default_locale:
            return _first_code(locale)
    return None


def link_segment(entry, normalize=True):
    """The URL segment getRelativeLocaleUrl() writes for a locale entry (getLocaleRelativeUrl:
    peekCodePathToUse gives the string, or the object's path; normalizeLocale defaults to true)."""
    raw = entry if isinstance(entry, str) else entry["path"]
    return normalize_the_locale(raw) if normalize else raw


# ---- reading the config as text (no JavaScript is run) ----

def mask_code(text):
    """Blank out comments and string contents (quotes kept), keeping length and newlines."""
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            j = text.find("\n", i)
            if j < 0:
                j = n
            for k in range(i, j):
                out[k] = " "
            i = j
        elif c == "/" and i + 1 < n and text[i + 1] == "*":
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if text[k] != "\n":
                    out[k] = " "
            i = j
        elif c in "'\"`":
            j = i + 1
            while j < n and text[j] != c:
                if text[j] == "\\":
                    j += 1
                elif c != "`" and text[j] == "\n":
                    break
                j += 1
            for k in range(i + 1, min(j, n)):
                if text[k] != "\n":
                    out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


def match_close(masked, start):
    """Index of the bracket closing the one at masked[start] (any of {[( counted)."""
    depth = 0
    for i in range(start, len(masked)):
        ch = masked[i]
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
            if depth == 0:
                return i
    return len(masked)


def _rel_depth(masked, lo, pos):
    depth = 0
    for ch in masked[lo:pos]:
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
    return depth


def _first_at_depth0(regex, masked, lo, hi):
    for m in regex.finditer(masked, lo, hi):
        if _rel_depth(masked, lo, m.start()) == 0:
            return m
    return None


def _string_value(raw):
    """Value of a whole string literal, or None (template literals with ${} are None)."""
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] in "'\"`" and raw[-1] == raw[0]:
        val = raw[1:-1]
        if raw[0] == "`" and "${" in val:
            return None
        return val
    return None


def _read_string_at(text, q):
    """Value of the string literal whose opening quote is text[q]."""
    c = text[q]
    j = text.find(c, q + 1)
    if j < 0:
        return None
    val = text[q + 1:j]
    if c == "`" and "${" in val:
        return None
    return val


def _split_top(masked, lo, hi):
    """(start, end) of each comma-separated entry at depth 0 in masked[lo:hi]."""
    out = []
    depth = 0
    start = lo
    for i in range(lo, hi):
        ch = masked[i]
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        elif ch == "," and depth == 0:
            out.append((start, i))
            start = i + 1
    out.append((start, hi))
    return [(a, b) for a, b in out if masked[a:b].strip()]


def _parse_entry(text, masked, a, b):
    """One entry of i18n.locales: a string, {"path": ..., "codes": [...]}, or None."""
    s = _string_value(text[a:b])
    if s is not None:
        return s
    seg = masked[a:b]
    if not seg.strip().startswith("{"):
        return None
    ob = a + (len(seg) - len(seg.lstrip()))
    cb = match_close(masked, ob)
    pm = _first_at_depth0(PATH_RE, masked, ob + 1, cb)
    cm = _first_at_depth0(CODES_RE, masked, ob + 1, cb)
    if pm is None or cm is None:
        return None
    path = _read_string_at(text, pm.end() - 1)
    ao = cm.end() - 1
    ac = match_close(masked, ao)
    codes = []
    for x, y in _split_top(masked, ao + 1, ac):
        code = _string_value(text[x:y])
        if code is None:
            return None
        codes.append(code)
    if path is None or not codes:
        return None
    return {"path": path, "codes": codes}


def find_config(root):
    for name in CONFIG_NAMES:
        path = os.path.join(root, name)
        if os.path.isfile(path):
            return path
    return None


def read_config(root):
    """Locales, defaultLocale and prefixDefaultLocale from astro.config.* (best effort)."""
    info = {"config": None, "locales": None, "complete": True, "default": None,
            "prefix_default": False, "warnings": []}
    path = find_config(root)
    if path is None:
        info["warnings"].append("no astro.config.* in the given root")
        return info
    info["config"] = os.path.basename(path)
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    masked = mask_code(text)
    m = I18N_RE.search(masked)
    if m is None:
        if I18N_REF_RE.search(masked):
            info["complete"] = False
            info["warnings"].append("i18n is set but not as an object literal: pass --locales "
                                    "and --default")
        else:
            info["warnings"].append("no i18n in %s" % info["config"])
        return info
    ob = m.end() - 1
    cb = match_close(masked, ob)
    lm = _first_at_depth0(LOCALES_ARR_RE, masked, ob + 1, cb)
    if lm is None:
        info["complete"] = False
        info["warnings"].append("i18n.locales is not an array literal: pass --locales")
    else:
        ao = lm.end() - 1
        ac = match_close(masked, ao)
        locales = []
        for a, b in _split_top(masked, ao + 1, ac):
            entry = _parse_entry(text, masked, a, b)
            if entry is None:
                info["complete"] = False
            else:
                locales.append(entry)
        info["locales"] = locales
        if not info["complete"]:
            info["warnings"].append("i18n.locales has entries that are not literals (spread, "
                                    "variables or computed values): pass --locales")
    dm = _first_at_depth0(DEFAULT_RE, masked, ob + 1, cb)
    if dm is not None:
        info["default"] = _read_string_at(text, dm.end() - 1)
    if PREFIX_DEFAULT_RE.search(masked, ob, cb):
        info["prefix_default"] = True
    return info


def parse_locales_arg(value):
    """'en,pt-BR,spanish=es|es-MX' -> ['en', 'pt-BR', {'path': 'spanish', 'codes': [...]}]."""
    out = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            path, codes = part.split("=", 1)
            out.append({"path": path.strip(),
                        "codes": [c.strip() for c in codes.split("|") if c.strip()]})
        else:
            out.append(part)
    return out


def scan_normalize_false(root):
    """Source files under src/ that pass normalizeLocale: false somewhere."""
    hits = []
    src = os.path.join(root, "src")
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith(".") and d != "node_modules")
        for name in sorted(filenames):
            if not name.endswith(SOURCE_EXTS):
                continue
            path = os.path.join(dirpath, name)
            with open(path, encoding="utf-8", errors="replace") as fh:
                if NORMALIZE_FALSE_RE.search(fh.read()):
                    hits.append(os.path.relpath(path, root).replace(os.sep, "/"))
    return hits


# ---- the pages ----

def looks_like_lang(name):
    """True if a folder name has the shape of a language tag with a known primary language."""
    m = TAG_RE.match(name)
    if not m:
        return False
    primary = m.group(1).lower()
    return primary in LANG2 or primary in LANG3


def list_pages(pages_dir):
    """Page files under pages_dir as sorted '/'-separated paths. Like Astro, names starting
    with '_' are skipped; this checker also skips names starting with '.'."""
    pages = []
    for dirpath, dirnames, filenames in os.walk(pages_dir):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith((".", "_")) and d != "node_modules")
        for name in filenames:
            if name.startswith((".", "_")) or name.endswith(".d.ts"):
                continue
            if not name.lower().endswith(PAGE_EXTS):
                continue
            rel = os.path.relpath(os.path.join(dirpath, name), pages_dir)
            pages.append(rel.replace(os.sep, "/"))
    return sorted(pages)


def _stem(rel):
    return rel.rsplit(".", 1)[0]


def page_route(rel):
    """URL path of a page file: '/' + path without extension, index pages end in '/'."""
    stem = _stem(rel)
    if stem == "index":
        return "/"
    if stem.endswith("/index"):
        return "/" + stem[:-len("index")]
    return "/" + stem


def _ident(entry):
    return entry if isinstance(entry, str) else entry["path"]


def _codes(entry):
    return [entry] if isinstance(entry, str) else list(entry.get("codes") or [])


def analyse(pages_dir, locales, default, prefix_default=False):
    """Classify the folders of every locale entry, unlisted language folders, and pages
    whose later path segment Astro.currentLocale reads as a locale."""
    pages = list_pages(pages_dir) if os.path.isdir(pages_dir) else []
    default_current = compute_current_locale("/", locales, default)
    by_top = {}
    for p in pages:
        if "/" in p:
            top, rest = p.split("/", 1)
            by_top.setdefault(top, []).append(rest)
    entries = []
    claimed = set()
    default_dirs = []
    for e in locales:
        idn = _ident(e)
        expected = _codes(e)
        norms = set([normalize_the_locale(idn)] + [normalize_the_locale(c) for c in expected])
        is_default = idn == default
        link = None if (is_default and not prefix_default) else link_segment(e)
        if link is None:
            spelling_ok = True
        else:
            spelling_ok = compute_current_locale("/" + link + "/", locales, default) in expected
        folders = []
        for d in sorted(by_top):
            if d != idn and normalize_the_locale(d) not in norms:
                continue
            claimed.add(d)
            if is_default:
                default_dirs.append(d)
            cur = compute_current_locale("/" + d + "/", locales, default)
            if link is None or d == link:
                link_state = "ok"
            elif d.lower() == link:
                link_state = "case_only"
            else:
                link_state = "differs"
            if cur not in expected:
                status = "current_locale_wrong"
            elif link_state == "case_only":
                status = "links_case_only"
            elif link_state == "differs":
                status = "links_miss"
            else:
                status = "ok"
            folders.append({"dir": d, "status": status, "current_locale": cur,
                            "pages": len(by_top[d])})
        item = {"locale": e, "link_segment": link, "spelling_ok": spelling_ok,
                "folders": folders}
        if not spelling_ok:
            item["suggested_entry"] = {"path": link, "codes": expected}
        entries.append(item)

    lang_dirs = set(d for d in by_top if looks_like_lang(d)) | claimed
    base = set(_stem(p) for p in pages
               if "/" not in p or p.split("/", 1)[0] not in lang_dirs)
    for d in default_dirs:
        base.update(_stem(r) for r in by_top[d])
    unlisted = []
    for d in sorted(by_top):
        if d in claimed or not looks_like_lang(d):
            continue
        rest = by_top[d]
        mirrored = sum(1 for r in rest if _stem(r) in base)
        mirrors = mirrored >= 2 and mirrored * 2 >= len(rest)
        unlisted.append({"dir": d, "status": "unlisted" if mirrors else "lang_like_not_mirrored",
                         "pages": len(rest), "mirrored_pages": mirrored,
                         "current_locale": compute_current_locale("/" + d + "/", locales,
                                                                  default)})

    later = []
    for p in pages:
        if "/" in p and p.split("/", 1)[0] in lang_dirs:
            continue
        route = page_route(p)
        first = route.strip("/").split("/")[0]
        if not first:
            continue
        if compute_current_locale("/" + first + "/", locales, default) != default_current:
            continue
        cur = compute_current_locale(route, locales, default)
        if cur != default_current:
            later.append({"page": p, "current_locale": cur})

    dynamic = [d for d in sorted(by_top) if d.startswith("[")]
    findings = (sum(1 for it in entries for f in it["folders"] if f["status"] in FINDINGS)
                + sum(1 for u in unlisted if u["status"] == "unlisted"))
    return {"pages": len(pages), "default_current_locale": default_current, "entries": entries,
            "unlisted_dirs": unlisted, "later_segment_pages": later,
            "dynamic_top_dirs": dynamic, "findings": findings}


def analyse_site(root, locales=None, default=None, pages_dir=None):
    """Full report for one site, or None if it has no astro.config.* and no --locales."""
    cfg = read_config(root)
    if cfg["config"] is None and locales is None:
        return None
    warnings = list(cfg["warnings"])
    if locales is not None:
        locs, locs_from, complete = parse_locales_arg(locales), "--locales", True
    else:
        locs = cfg["locales"] or []
        locs_from = cfg["config"] if cfg["locales"] is not None else None
        complete = cfg["complete"]
    if default is None:
        default = cfg["default"]
    if default is None and locs:
        warnings.append("no defaultLocale found: pass --default")
    if pages_dir is None:
        pages_dir = "src/pages"
    pdir = os.path.normpath(os.path.join(root, pages_dir))
    if not os.path.isdir(pdir):
        warnings.append("pages folder %s does not exist" % pages_dir)
    for rel in scan_normalize_false(root):
        warnings.append("normalizeLocale: false is passed in %s: links from those calls keep "
                        "the configured spelling, but this report assumes the default" % rel)
    report = {"tool": "astro_locales",
              "astro_source": "withastro/astro@" + ASTRO_SHA + " (astro " + ASTRO_VERSION + ")",
              "config": cfg["config"], "locales": locs, "locales_from": locs_from,
              "locales_complete": complete, "default_locale": default,
              "prefix_default_locale": cfg["prefix_default"],
              "pages_dir": pages_dir.replace(os.sep, "/"), "warnings": warnings}
    report.update(analyse(pdir, locs, default, cfg["prefix_default"]))
    if report["dynamic_top_dirs"]:
        report["warnings"].append("top-level dynamic route folders (%s): their locale paths "
                                  "come from getStaticPaths and are not checked"
                                  % ", ".join(report["dynamic_top_dirs"]))
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Find locale folders that Astro.currentLocale and getRelativeLocaleUrl() "
                    "disagree on.")
    ap.add_argument("root", help="site root, the folder that holds astro.config.*")
    ap.add_argument("--locales", help="comma-separated locales, path=code|code for objects")
    ap.add_argument("--default", help="defaultLocale, overriding the config")
    ap.add_argument("--pages-dir", help="pages folder relative to root (default src/pages)")
    ap.add_argument("--strict", action="store_true", help="exit 1 if there is any finding")
    args = ap.parse_args(argv)
    report = analyse_site(args.root, args.locales, args.default, args.pages_dir)
    if report is None:
        print(json.dumps({"error": "no astro.config.* in the given root; pass --locales"}))
        return 2
    print(json.dumps(report, indent=1, ensure_ascii=False))
    if args.strict and report["findings"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
