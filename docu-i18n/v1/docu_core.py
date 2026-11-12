# docu-i18n census v1: pure parsing and classification (no network, no git).
#
# Docusaurus builds only the locales listed in i18n.locales, and for each listed locale it
# reads translations from <site>/<i18n.path>/<localeConfigs[locale].path or locale>/ - and
# only if that exact folder exists (Docusaurus >= 3.9 silently sets translate=false
# otherwise). This module reads a docusaurus.config.{js,ts,mjs,cjs} text without running it
# and sorts the folders found under the i18n folder into: configured, mismatch (a listed
# locale whose exact folder is missing while a case/separator variant exists), variant-dup
# and orphan (not listed at all).
# Made with AI agents by MV2 of Munim, Inc. Apache-2.0.
import posixpath
import re

QUOTES = "'\"`"


def skip_string(code, i):
    """Index just past the string literal that starts at code[i]."""
    q = code[i]
    j = i + 1
    n = len(code)
    while j < n:
        c = code[j]
        if c == "\\":
            j += 2
            continue
        if c == q:
            return j + 1
        if q != "`" and c == "\n":
            return j
        j += 1
    return n


def split_js(text):
    """(code, comments): code has every // and /* */ comment replaced by spaces (string
    literals are kept intact); comments is the text of all comments joined by newlines."""
    out, com = [], []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in QUOTES:
            j = skip_string(text, i)
            out.append(text[i:j])
            i = j
            continue
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            com.append(text[i + 2:j])
            out.append(" " * (j - i))
            i = j
            continue
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            com.append(text[i + 2:j])
            out.append("".join("\n" if ch == "\n" else " " for ch in text[i:j]))
            i = j
            continue
        out.append(c)
        i += 1
    return "".join(out), "\n".join(com)


def balanced_end(code, i):
    """code[i] is an opening bracket; index just past its partner, or -1."""
    depth = 0
    n = len(code)
    while i < n:
        c = code[i]
        if c in QUOTES:
            i = skip_string(code, i)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def value_until_comma(body, i):
    """(value text, index of the comma or end) for a value starting at body[i]."""
    depth = 0
    j, n = i, len(body)
    while j < n:
        c = body[j]
        if c in QUOTES:
            j = skip_string(body, j)
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            break
        j += 1
    return body[i:j].strip(), j


_IDENT = re.compile(r"[A-Za-z_$][\w$]*")


def string_literal(v):
    """Content of a plain string literal, else None."""
    v = (v or "").strip()
    if len(v) < 2 or v[0] not in QUOTES or v[-1] != v[0]:
        return None
    if skip_string(v, 0) != len(v):
        return None
    inner = v[1:-1]
    if v[0] == "`" and "${" in inner:
        return None
    return re.sub(r"\\(.)", r"\1", inner)


def top_level_props(body):
    """List of (key, value_text or None) for an object literal's body (without braces).
    Spread entries get key '...'; computed keys get key '[]'; shorthand gets value None."""
    props = []
    i, n = 0, len(body)
    while i < n:
        while i < n and (body[i].isspace() or body[i] == ","):
            i += 1
        if i >= n:
            break
        if body.startswith("...", i):
            v, i = value_until_comma(body, i + 3)
            props.append(("...", v))
            continue
        c = body[i]
        if c in QUOTES:
            j = skip_string(body, i)
            key = string_literal(body[i:j])
            if key is None:
                key = "[]"
            i = j
        elif c == "[":
            j = balanced_end(body, i)
            key = "[]"
            i = n if j < 0 else j
        else:
            m = _IDENT.match(body, i)
            if not m:
                v, i = value_until_comma(body, i)
                props.append(("[]", v))
                continue
            key = m.group(0)
            i = m.end()
        while i < n and body[i].isspace():
            i += 1
        if i >= n or body[i] == ",":
            props.append((key, None))
            continue
        if body[i] == ":":
            v, i = value_until_comma(body, i + 1)
            props.append((key, v))
            continue
        # method shorthand or something else: take everything up to the next comma
        v, i = value_until_comma(body, i)
        props.append(("[]", v))
    return props


def parse_string_array(v):
    v = (v or "").strip()
    if not v.startswith("[") or balanced_end(v, 0) != len(v):
        return None
    body = v[1:-1]
    items = []
    i = 0
    while i < len(body):
        while i < len(body) and (body[i].isspace() or body[i] == ","):
            i += 1
        if i >= len(body):
            break
        item, i = value_until_comma(body, i)
        s = string_literal(item)
        if s is None:
            return None
        items.append(s)
    return items


def _object_body(v):
    v = (v or "").strip()
    if not v.startswith("{") or balanced_end(v, 0) != len(v):
        return None
    return v[1:-1]


def _clean_path(p):
    p = posixpath.normpath(p.replace("\\", "/"))
    if p.startswith("/") or p == ".." or p.startswith("../"):
        return None
    return p


_I18N_KEY = re.compile(r"(?<![\w$.])(?:i18n|'i18n'|\"i18n\")\s*:")
_I18N_ANY = re.compile(r"(?<![\w$])i18n(?![\w$])")


def parse_config(text):
    """Read the i18n settings of a docusaurus config without running it.
    Returns a dict with status 'ok' (literal i18n object), 'default' (no i18n key: Docusaurus
    defaults, en only) or 'unparsed' (reason in 'why'), plus default_locale, locales,
    i18n_path, paths (locale -> folder), code and comments."""
    code, comments = split_js(text)
    res = {"status": "unparsed", "why": "", "default_locale": "", "locales": [],
           "i18n_path": "i18n", "paths": {}, "code": code, "comments": comments}
    keys = list(_I18N_KEY.finditer(code))
    if not keys:
        if _I18N_ANY.search(code):
            res["why"] = "i18n is not an object literal"
            return res
        res.update(status="default", default_locale="en", locales=["en"])
        return res
    if len(keys) > 1:
        res["why"] = "more than one i18n key"
        return res
    i = keys[0].end()
    while i < len(code) and code[i].isspace():
        i += 1
    if i >= len(code) or code[i] != "{":
        res["why"] = "i18n value is not an object literal"
        return res
    end = balanced_end(code, i)
    if end < 0:
        res["why"] = "unbalanced i18n object"
        return res
    props = top_level_props(code[i + 1:end - 1])
    d = {}
    for k, v in props:
        if k in ("...", "[]") or v is None:
            res["why"] = "i18n has a spread, computed or shorthand entry"
            return res
        d[k] = v
    default = "en"
    if "defaultLocale" in d:
        default = string_literal(d["defaultLocale"])
        if default is None:
            res["why"] = "defaultLocale is not a string literal"
            return res
    locales = [default]
    if "locales" in d:
        locales = parse_string_array(d["locales"])
        if locales is None:
            res["why"] = "locales is not an array of string literals"
            return res
    i18n_path = "i18n"
    if "path" in d:
        p = string_literal(d["path"])
        p = _clean_path(p) if p is not None else None
        if p is None:
            res["why"] = "i18n.path is not a plain relative string"
            return res
        i18n_path = p
    paths = {}
    if "localeConfigs" in d:
        body = _object_body(d["localeConfigs"])
        if body is None:
            res["why"] = "localeConfigs is not an object literal"
            return res
        for k, v in top_level_props(body):
            if k in ("...", "[]") or v is None:
                res["why"] = "localeConfigs has a spread, computed or shorthand entry"
                return res
            lb = _object_body(v)
            if lb is None:
                res["why"] = "localeConfigs entry is not an object literal"
                return res
            for k2, v2 in top_level_props(lb):
                if k2 in ("...", "[]"):
                    res["why"] = "localeConfigs entry has a spread or computed entry"
                    return res
                if k2 == "path":
                    p = string_literal(v2)
                    p = _clean_path(p) if p is not None else None
                    if p is None:
                        res["why"] = "localeConfigs path is not a plain relative string"
                        return res
                    paths[k] = p
    res.update(status="ok", why="", default_locale=default, locales=locales,
               i18n_path=i18n_path, paths=paths)
    return res


def locale_folder(cfg, locale):
    return cfg["paths"].get(locale, locale)


def norm(name):
    return name.lower().replace("_", "-")


def classify(cfg, folders):
    """Sort the folder names found directly under the i18n folder.
    Returns a list of dicts: folder, cls, locale. cls is one of
      configured  - the exact folder of a listed locale (or of defaultLocale)
      mismatch    - a listed locale's exact folder is missing and this folder differs from it
                    only in case or '_' vs '-' (on Linux the listed locale gets no translation)
      variant-dup - such a variant while the exact folder also exists
      orphan      - matches no listed locale at all (never built by `docusaurus build`)
      missing     - (folder '') a listed non-default locale with no folder and no variant."""
    folders = sorted(set(folders))
    listed = list(dict.fromkeys(cfg["locales"] + [cfg["default_locale"]]))
    exact = {locale_folder(cfg, loc): loc for loc in listed}
    out = []
    matched_locales = set()
    for f in folders:
        if f in exact:
            out.append({"folder": f, "cls": "configured", "locale": exact[f]})
            matched_locales.add(exact[f])
            continue
        hits = [loc for loc in listed if norm(locale_folder(cfg, loc)) == norm(f)]
        if hits:
            loc = hits[0]
            cls = "variant-dup" if locale_folder(cfg, loc) in folders else "mismatch"
            out.append({"folder": f, "cls": cls, "locale": loc})
            matched_locales.add(loc)
        else:
            out.append({"folder": f, "cls": "orphan", "locale": ""})
    for loc in listed:
        if loc != cfg["default_locale"] and loc not in matched_locales:
            out.append({"folder": "", "cls": "missing", "locale": loc})
    return out


def english_candidates(site, rel):
    """Repository paths that may hold the English source of i18n file rel (relative to
    i18n/<folder>/), most likely first. Empty when the plugin folder is not a standard one."""
    return list(dict.fromkeys(_english_candidates(site, rel)))


def _english_candidates(site, rel):
    pre = site + "/" if site else ""
    parent = posixpath.dirname(site) if site else ""
    ppre = parent + "/" if parent else ""
    parts = rel.split("/")
    if len(parts) >= 3 and parts[0] == "docusaurus-plugin-content-docs":
        sub = "/".join(parts[2:])
        if parts[1] == "current":
            return [pre + "docs/" + sub, ppre + "docs/" + sub]
        if parts[1].startswith("version-"):
            return [pre + "versioned_docs/" + parts[1] + "/" + sub]
        return []
    if len(parts) >= 2 and parts[0] == "docusaurus-plugin-content-blog":
        sub = "/".join(parts[1:])
        return [pre + "blog/" + sub, ppre + "blog/" + sub]
    if len(parts) >= 2 and parts[0] == "docusaurus-plugin-content-pages":
        sub = "/".join(parts[1:])
        return [pre + "src/pages/" + sub]
    return []


def squash(text):
    return re.sub(r"\s+", "", text)


def cli_mentions(texts, folder):
    """True when any text builds or starts this locale by name on the command line."""
    pat = re.compile(r"--locale(?:=|\s+)['\"]?" + re.escape(folder) + r"(?![\w-])")
    return any(pat.search(t or "") for t in texts)


def quoted_in(text, folder):
    pat = re.compile(r"""(['"`])""" + re.escape(folder) + r"\1")
    return bool(pat.search(text or ""))
