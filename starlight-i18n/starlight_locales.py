#!/usr/bin/env python3
# starlight_locales: translations an Astro Starlight site serves under the wrong language.
# Standard library only, no network. Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
"""Check an Astro Starlight site for translations its `locales` config never matches.

What Starlight does (read in withastro/starlight at commit ad19424, @astrojs/starlight 0.42.11,
and withastro/astro main; this is source reading, not a build test):
- Page ids. Starlight's docsLoader() passes no generateId to Astro's glob loader unless the site
  gives one, so Astro's generateIdDefault() is used: a frontmatter `slug` if set, else the path
  with each segment run through github-slugger's slug(), which lowercases it
  (astro/src/content/utils.ts, getContentEntryIdAndSlug). src/content/docs/pt-BR/a.md -> pt-br/a.
- A page's locale (src/integrations/shared/slugToLocale.ts): the first segment of its id if
  Object.hasOwn(locales, segment); otherwise undefined (the root locale) when a `root` locale
  exists, else defaultLocale. The match is exact and case-sensitive.
- The locales schema (src/utils/user-config.ts) never checks keys, so a key such as 'pt-BR' is
  accepted. It can never equal a lowercased id segment, so that locale gets no pages: its
  translations are served as root/default-language pages, and every default page is copied
  into the locale as an "untranslated" fallback (src/utils/routing/index.ts). Starlight issue
  #3099 is one user report of this (zh-CN); #2487 explains the lowercasing.
- A folder that is not a locale key at all (de/ when only fr is configured) is served the same
  way: as root/default-language pages, with that locale's lang, dir, UI strings and sidebar.
- `dir` defaults to 'ltr' (src/schemas/locale.ts) and is never derived from `lang`, so an
  Arabic, Hebrew, Persian or Urdu locale without dir: 'rtl' is laid out left to right.
- UI strings (src/utils/translations.ts, createTranslationSystem.ts): files in
  src/content/i18n are keyed by their file name, case kept, and looked up by each locale's
  exact lang, whose region Starlight upper-cases (pt-br -> pt-BR). User files get no
  base-language fallback. So pt-br.json, pt_BR.json, or pt.json for lang pt-BR are never read.

Usage: python starlight_locales.py <site root holding astro.config.*> [--locales root=en,fr]
       [--default-locale en] [--docs-dir src/content/docs] [--strict]
--locales entries are key[=lang[=dir]]. Prints one JSON report. Exit 0; with --strict, 1 if
there is any finding; 2 if <root> has no astro.config file.
"""
import argparse
import json
import os
import re
import sys

STARLIGHT_SHA = "ad19424b2bb2b3290a13064cec28bf653d7730dd"
STARLIGHT_VERSION = "0.42.11"

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
# Languages written right to left by default, and right-to-left scripts.
RTL_LANGS = frozenset("ar arc ckb dv fa he iw ks ps sd syr ug ur yi".split())
RTL_SCRIPTS = frozenset("adlm arab hebr nkoo rohg syrc thaa".split())

TAG_RE = re.compile(r"^([A-Za-z]{2,3})(?:[-_]([A-Za-z]{4}))?(?:[-_]([A-Za-z]{2}|[0-9]{3}))?$")
CONFIG_NAMES = ("astro.config.mjs", "astro.config.ts", "astro.config.mts", "astro.config.js",
                "astro.config.cjs", "astro.config.cts")
CONTENT_CONFIGS = ("src/content.config.ts", "src/content.config.mts", "src/content.config.mjs",
                   "src/content.config.js", "src/content/config.ts", "src/content/config.mts",
                   "src/content/config.mjs", "src/content/config.js")
DOC_EXTS = (".markdown", ".mdown", ".mkdn", ".mkd", ".mdwn", ".md", ".mdx", ".mdoc")
I18N_EXTS = (".json", ".yml", ".yaml")
STARLIGHT_CALL_RE = re.compile(r"(?<![\w$.])starlight\s*\(")
LOCALES_RE = re.compile(r"(?<![\w$.])locales\s*:\s*\{")
LOCALES_VAR_RE = re.compile(r"(?<![\w$.])locales\s*(?::\s*([A-Za-z_$][\w$]*)\s*)?[,}\n]")
DEFAULT_RE = re.compile(r"""(?<![\w$.])defaultLocale\s*:\s*(['"])([^'"\n]+)\1""")
PROP_RE = re.compile(r"""(?<![\w$.])(lang|dir)\s*:\s*(?:(['"])([^'"\n]*)\2)?""")
GENERATE_ID_RE = re.compile(r"(?<![\w$.])generateId\b")
I18N_COLLECTION_RE = re.compile(r"(?<![\w$.])(?:i18nLoader|i18n\s*:)")
IDENT_RE = re.compile(r"[A-Za-z_$][\w$]*")
SLUG_DROP_RE = re.compile(r"[^\w\- ]")
FM_SLUG_RE = re.compile(r"""^slug:[ \t]*(['"]?)(.*?)\1[ \t]*$""", re.M)
DIR_FINDINGS = ("key_case", "separator_mismatch", "unlisted")
UI_FINDINGS = ("case_mismatch", "separator_mismatch", "base_only")


def looks_like_lang(name):
    """True if a folder name has the shape of a language tag with a known primary language."""
    m = TAG_RE.match(name)
    if not m:
        return False
    primary = m.group(1).lower()
    return primary in LANG2 or primary in LANG3


def slug_segment(seg):
    """github-slugger's slug(): lowercase, drop punctuation, spaces to '-'."""
    return SLUG_DROP_RE.sub("", seg.lower()).replace(" ", "-")


def rel_to_id(rel):
    """Astro's default id for a docs file path ('/'-separated, relative to the docs folder)."""
    stem = rel.rsplit(".", 1)[0] if "." in rel.rsplit("/", 1)[-1] else rel
    sid = "/".join(slug_segment(s) for s in stem.split("/"))
    if sid.endswith("/index"):
        sid = sid[:-len("/index")]
    return sid


def normalize_lang(lang):
    """Starlight's lang normalisation: the region subtag is upper-cased (pt-br -> pt-BR)."""
    parts = lang.split("-")
    out = [parts[0]]
    done = False
    for p in parts[1:]:
        if not done and re.fullmatch(r"[A-Za-z]{2}|[0-9]{3}", p):
            out.append(p.upper())
            done = True
        else:
            out.append(p)
    return "-".join(out)


def is_rtl(lang):
    """True if a language tag is written right to left (by script subtag, else by language)."""
    parts = lang.replace("_", "-").split("-")
    script = next((p.lower() for p in parts[1:] if len(p) == 4 and p.isalpha()), None)
    if script:
        return script in RTL_SCRIPTS
    return parts[0].lower() in RTL_LANGS


def _norm_tag(s):
    return s.lower().replace("_", "-")


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


def _depth(masked, lo, pos):
    return masked.count("{", lo, pos) - masked.count("}", lo, pos)


def call_span(masked, paren):
    """Index of the ')' closing the '(' at index paren (or the end of the text)."""
    depth = 0
    for i in range(paren, len(masked)):
        if masked[i] == "(":
            depth += 1
        elif masked[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return len(masked)


def pick_brace(masked, regex, lo, hi):
    """Index of the '{' ending the shallowest match of regex in masked[lo:hi], or None."""
    best = None
    for m in regex.finditer(masked, lo, hi):
        d = _depth(masked, lo, m.start())
        if best is None or d < best[0]:
            best = (d, m.end() - 1)
    return None if best is None else best[1]


def _segment_key(text, masked, a, b):
    """Classify one top-level entry text[a:b] of an object literal.

    Returns ("key", name), ("unknown", None) for spread or computed entries, or ("none", None).
    """
    seg = masked[a:b]
    stop = len(seg)
    for j, ch in enumerate(seg):
        if ch in ":{[(":
            stop = j
            break
    head = seg[:stop]
    lead = len(head) - len(head.lstrip())
    trail = len(head.rstrip())
    if trail <= lead:
        if stop < len(seg) and seg[stop] == "[":
            return ("unknown", None)
        return ("none", None)
    raw = text[a + lead:a + trail]
    if raw.startswith("..."):
        return ("unknown", None)
    if raw[0] in "'\"`" and len(raw) >= 2 and raw[-1] == raw[0]:
        if stop < len(seg) and seg[stop] != ":":
            return ("none", None)
        return ("key", raw[1:-1])
    if IDENT_RE.fullmatch(raw):
        if stop == len(seg) or seg[stop] == ":":
            return ("key", raw)
    return ("none", None)


def object_entries(text, masked, brace):
    """Top-level entries (key, start, end) of the object literal whose '{' is at index brace.

    Returns (entries, has_unknown); has_unknown is True if a spread (...x) or computed ([k])
    entry was seen, so the list may be incomplete.
    """
    entries = []
    unknown = False
    depth = 0
    seg_start = brace + 1
    for i in range(brace, len(masked)):
        ch = masked[i]
        end_segment = closing = False
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
            if depth == 0:
                end_segment = closing = True
        elif ch == "," and depth == 1:
            end_segment = True
        if end_segment:
            kind, key = _segment_key(text, masked, seg_start, i)
            if kind == "key" and all(k != key for k, _, _ in entries):
                entries.append((key, seg_start, i))
            elif kind == "unknown":
                unknown = True
            seg_start = i + 1
        if closing:
            break
    return entries, unknown


def entry_props(text, masked, a, b):
    """lang and dir of one locale entry text[a:b] (string literals only)."""
    props = {"lang": None, "dir": None, "unknown": []}
    for m in PROP_RE.finditer(text, a, b):
        if masked[m.start()] != text[m.start()] or _depth(masked, a, m.start()) != 1:
            continue
        name = m.group(1)
        if m.group(2) is None:
            if name not in props["unknown"]:
                props["unknown"].append(name)
        elif props[name] is None:
            props[name] = m.group(3)
    return props


def _rel(path, root):
    return os.path.relpath(path, root).replace(os.sep, "/")


def find_config(root):
    for name in CONFIG_NAMES:
        path = os.path.join(root, name)
        if os.path.isfile(path):
            return path
    return None


def read_config(root):
    """Locales, defaultLocale and warnings from astro.config.* (best effort, no JS run).

    Returns None if root has no astro.config file.
    """
    path = find_config(root)
    if path is None:
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    masked = mask_code(text)
    info = {"config": _rel(path, root), "entries": None, "unknown": False,
            "default_locale": None, "warnings": []}
    m = STARLIGHT_CALL_RE.search(masked)
    if m:
        lo = m.end() - 1
        hi = call_span(masked, lo)
    else:
        lo, hi = 0, len(masked)
        info["warnings"].append("no starlight( call found in %s: read the whole file"
                                % info["config"])
    brace = pick_brace(masked, LOCALES_RE, lo, hi)
    if brace is None:
        var = LOCALES_VAR_RE.search(masked, lo, hi)
        if var is not None:
            name = var.group(1) or "locales"
            const_re = re.compile(r"(?<![\w$.])(?:const|let|var)\s+" + re.escape(name)
                                  + r"\s*(?::[^=\n]+)?=\s*\{")
            brace = pick_brace(masked, const_re, 0, len(masked))
            if brace is None:
                info["unknown"] = True
                info["warnings"].append("locales is set from %s, which is not an object "
                                        "literal in this file: pass --locales" % name)
    if brace is not None:
        ents, unknown = object_entries(text, masked, brace)
        info["entries"] = dict((k, entry_props(text, masked, a, b)) for k, a, b in ents)
        info["unknown"] = unknown
    best = None
    for dm in DEFAULT_RE.finditer(text, lo, hi):
        if masked[dm.start()] != text[dm.start()]:
            continue
        d = _depth(masked, lo, dm.start())
        if best is None or d < best[0]:
            best = (d, dm.group(2))
    if best is not None:
        info["default_locale"] = best[1]
    return info


def read_content_config(root):
    """(path, custom generateId?, i18n collection?) from the site's content config, or Nones."""
    for rel in CONTENT_CONFIGS:
        path = os.path.join(root, *rel.split("/"))
        if os.path.isfile(path):
            with open(path, encoding="utf-8", errors="replace") as fh:
                masked = mask_code(fh.read())
            return (rel, bool(GENERATE_ID_RE.search(masked)),
                    bool(I18N_COLLECTION_RE.search(masked)))
    return (None, None, None)


def frontmatter_slug(path):
    """The frontmatter `slug` of a docs file, or None."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        head = fh.read(8192)
    head = head.lstrip(chr(0xFEFF))
    if not head.startswith("---"):
        return None
    end = head.find("\n---", 3)
    if end < 0:
        return None
    m = FM_SLUG_RE.search(head[3:end])
    if not m or not m.group(2).strip():
        return None
    return m.group(2).strip().strip("/")


def list_pages(docs_dir):
    """Docs pages as dicts {rel, id}, sorted by rel. Dot folders and _files are skipped."""
    pages = []
    for dirpath, dirnames, filenames in os.walk(docs_dir):
        dirnames[:] = sorted(d for d in dirnames
                             if not d.startswith(".") and d != "node_modules")
        for name in filenames:
            if name.startswith(("_", ".")) or not name.endswith(DOC_EXTS):
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, docs_dir).replace(os.sep, "/")
            pages.append({"rel": rel, "id": frontmatter_slug(full) or rel_to_id(rel)})
    return sorted(pages, key=lambda p: p["rel"])


def page_locale(page_id, keys, has_root, default_locale):
    """Port of slugToLocale(): the locale key of a page id, or None for the root locale."""
    base = page_id.split("/")[0]
    if base and base in keys:
        return base
    if not has_root:
        return default_locale
    return None


def analyse(docs_dir, entries, default_locale, custom_ids):
    """Classify every top-level docs folder that is, or looks like, a locale."""
    keys = list(entries)
    has_root = "root" in entries
    multilingual = len(keys) > 1 or (len(keys) == 1 and not has_root)
    if not multilingual or (has_root and default_locale in (None, "root")):
        default_locale = None
    active = keys if multilingual else []
    loc_keys = [k for k in active if k != "root"]
    pages = list_pages(docs_dir) if os.path.isdir(docs_dir) else []
    by_top = {}
    for p in pages:
        if "/" in p["rel"]:
            by_top.setdefault(p["rel"].split("/", 1)[0], []).append(p)
    status_of, near_of = {}, {}
    for top in sorted(by_top):
        t = slug_segment(top)
        status = near = None
        if t in loc_keys:
            status = "listed"
        else:
            near = next((k for k in loc_keys if k.lower() == t), None)
            if near is not None:
                status = "key_case_custom_ids" if custom_ids else "key_case"
            else:
                near = next((k for k in loc_keys if _norm_tag(k) == _norm_tag(t)), None)
                if near is not None:
                    status = "separator_mismatch"
                elif looks_like_lang(t):
                    status = "lang_like"
        if status is not None:
            status_of[top], near_of[top] = status, near
    if default_locale is None:
        tree = set(rel_to_id(p["rel"]) for p in pages
                   if "/" not in p["rel"] or p["rel"].split("/", 1)[0] not in status_of)
    else:
        tree = set(rel_to_id(p["rel"].split("/", 1)[1]) for top, ps in by_top.items()
                   if slug_segment(top) == default_locale for p in ps)
    dirs = []
    for top in sorted(status_of):
        ps = by_top[top]
        status = status_of[top]
        mirrored = None
        if status == "lang_like":
            rests = [rel_to_id(p["rel"].split("/", 1)[1]) for p in ps]
            mirrored = sum(1 for r in rests if r in tree)
            mirrors = mirrored >= 2 and mirrored * 2 >= len(rests)
            status = "unlisted" if mirrors else "lang_like_not_mirrored"
        served = page_locale(ps[0]["id"], active, has_root, default_locale)
        dirs.append({"dir": top, "id_segment": slug_segment(top), "status": status,
                     "near_key": near_of[top], "pages": len(ps), "mirrored_pages": mirrored,
                     "served_as": served if served is not None else "root"})
    empty = [k for k in loc_keys
             if not any(p["id"] == k or p["id"].startswith(k + "/") for p in pages)]
    return {"multilingual": multilingual, "default_locale": default_locale or "root",
            "pages": len(pages), "dirs": dirs, "empty_locales": empty}


def entry_lang(key, props):
    """A locale's lang as Starlight resolves it (lang, else the key; root needs lang)."""
    if props.get("lang"):
        return props["lang"]
    return None if key == "root" else key


def rtl_without_dir(entries):
    out = []
    for key, props in entries.items():
        unknown = props.get("unknown") or []
        if "lang" in unknown or "dir" in unknown:
            continue
        lang = entry_lang(key, props)
        if lang and is_rtl(lang) and (props.get("dir") or "ltr") != "rtl":
            out.append({"locale": key, "lang": lang, "dir": props.get("dir") or "ltr (default)"})
    return out


def ui_files(i18n_dir, entries):
    """Classify the UI-string files in src/content/i18n against the configured langs."""
    langs = []
    for key, props in entries.items():
        lang = entry_lang(key, props)
        if lang and normalize_lang(lang) not in langs:
            langs.append(normalize_lang(lang))
    if not langs:
        langs = ["en"]
    out = []
    if not os.path.isdir(i18n_dir):
        return out
    for name in sorted(os.listdir(i18n_dir)):
        if name.startswith(("_", ".")) or not name.endswith(I18N_EXTS):
            continue
        if not os.path.isfile(os.path.join(i18n_dir, name)):
            continue
        stem = name.rsplit(".", 1)[0]
        if stem in langs:
            status, near = "used", stem
        else:
            near = next((l for l in langs if l.lower() == stem.lower()), None)
            if near is not None:
                status = "case_mismatch"
            else:
                near = next((l for l in langs if _norm_tag(l) == _norm_tag(stem)), None)
                if near is not None:
                    status = "separator_mismatch"
                else:
                    near = next((l for l in langs
                                 if "-" in l and l.split("-")[0].lower() == stem.lower()), None)
                    status = "base_only" if near is not None else "unused"
        out.append({"file": name, "status": status, "lang": near})
    return out


def parse_locales_arg(s):
    """--locales 'root=en,fr,ar=ar=rtl' -> entries."""
    entries = {}
    for item in s.split(","):
        item = item.strip()
        if not item:
            continue
        parts = item.split("=")
        entries[parts[0]] = {"lang": parts[1] if len(parts) > 1 and parts[1] else None,
                             "dir": parts[2] if len(parts) > 2 and parts[2] else None,
                             "unknown": []}
    return entries


def analyse_site(root, locales=None, default_locale=None, docs_dir=None):
    """Full report for one site, or None if root has no astro.config file."""
    cfg = read_config(root)
    if cfg is None:
        return None
    warnings = list(cfg["warnings"])
    if locales is not None:
        entries, entries_from, complete = parse_locales_arg(locales), "--locales", True
    elif cfg["entries"] is not None:
        entries, entries_from, complete = cfg["entries"], cfg["config"], not cfg["unknown"]
        if not complete:
            warnings.append("locales has spread or computed entries, so its keys may be "
                            "incomplete: pass --locales")
    else:
        entries, entries_from, complete = {}, None, not cfg["unknown"]
        if complete:
            warnings.append("no Starlight locales in the config: the site has one language")
    if default_locale is None:
        default_locale = cfg["default_locale"]
    content_cfg, custom_ids, i18n_collection = read_content_config(root)
    if content_cfg is None:
        warnings.append("no content config (src/content.config.*) found")
    if custom_ids:
        warnings.append("%s sets generateId: page ids are not modelled, so key_case folders "
                        "are reported as key_case_custom_ids and not counted" % content_cfg)
    has_root = "root" in entries
    if len(entries) > 1 and not has_root and default_locale is None:
        warnings.append("several locales, no root and no defaultLocale: Starlight stops "
                        "with 'Could not determine the default locale'")
    if docs_dir is None:
        docs_dir = "src/content/docs"
    docs = os.path.normpath(os.path.join(root, docs_dir))
    if not os.path.isdir(docs):
        warnings.append("docs folder %s does not exist" % docs_dir)
    report = {"tool": "starlight_locales",
              "starlight_source": "withastro/starlight@%s (%s)" % (STARLIGHT_SHA,
                                                                   STARLIGHT_VERSION),
              "config": cfg["config"], "locales": list(entries), "locales_from": entries_from,
              "keys_complete": complete, "locale_settings": entries,
              "content_config": content_cfg, "custom_generate_id": bool(custom_ids),
              "docs_dir": docs_dir.replace(os.sep, "/"), "warnings": warnings}
    report.update(analyse(docs, entries, default_locale, custom_ids))
    report["rtl_without_dir"] = rtl_without_dir(entries)
    i18n_dir = os.path.join(root, "src", "content", "i18n")
    report["ui_files"] = ui_files(i18n_dir, entries)
    if report["ui_files"] and content_cfg is not None and not i18n_collection:
        warnings.append("src/content/i18n has files but %s defines no i18n collection, so "
                        "Starlight reads none of them" % content_cfg)
    kinds = {}
    for d in report["dirs"]:
        if d["status"] in DIR_FINDINGS:
            kinds[d["status"]] = kinds.get(d["status"], 0) + 1
    if report["rtl_without_dir"]:
        kinds["rtl_without_dir"] = len(report["rtl_without_dir"])
    for u in report["ui_files"]:
        if u["status"] in UI_FINDINGS:
            k = "ui_" + u["status"]
            kinds[k] = kinds.get(k, 0) + 1
    report["findings_by_kind"] = kinds
    report["findings"] = sum(kinds.values())
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Find translations an Astro Starlight site serves under the wrong language.")
    ap.add_argument("root", help="site root, the folder that holds astro.config.*")
    ap.add_argument("--locales", help="key[=lang[=dir]],... overriding the config")
    ap.add_argument("--default-locale", help="defaultLocale, overriding the config")
    ap.add_argument("--docs-dir", help="docs folder relative to root (src/content/docs)")
    ap.add_argument("--strict", action="store_true", help="exit 1 if there is any finding")
    args = ap.parse_args(argv)
    report = analyse_site(args.root, args.locales, args.default_locale, args.docs_dir)
    if report is None:
        print(json.dumps({"error": "no astro.config file in the given root"}))
        return 2
    print(json.dumps(report, indent=1, ensure_ascii=False))
    if args.strict and report["findings"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
