#!/usr/bin/env python3
# check.py for astro-mech: grade PREREG P1-P5 on a built Astro site. Always exits 0.
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import json
import os
import re
import sys

LANG_RE = re.compile(r"<html[^>]*\slang=\"([^\"]*)\"")
LINK_RE = re.compile(r"<a[^>]*data-code=\"([^\"]+)\"[^>]*href=\"([^\"]*)\"|"
                     r"<a[^>]*href=\"([^\"]*)\"[^>]*data-code=\"([^\"]+)\"")


def page(dist, rel):
    path = os.path.join(dist, *rel.split("/"), "index.html")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        html = fh.read()
    m = LANG_RE.search(html)
    links = {}
    for g in LINK_RE.finditer(html):
        if g.group(1):
            links[g.group(1)] = g.group(2)
        else:
            links[g.group(4)] = g.group(3)
    return {"lang": m.group(1) if m else None, "links": links}


def main(site, out):
    os.makedirs(out, exist_ok=True)
    dist = os.path.join(site, "dist")
    seen = sorted(os.path.relpath(os.path.join(d, f), dist).replace(os.sep, "/")
                  for d, _, fs in os.walk(dist) for f in fs if f.endswith(".html"))
    pt, fr = page(dist, "pt-BR"), page(dist, "fr-ca")
    es, de = page(dist, "spanish"), page(dist, "blog/de")
    res = {"html_files": seen, "pt-BR": pt, "fr-ca": fr, "spanish": es, "blog/de": de}
    res["P1"] = bool(pt and pt["lang"] == "pt-BR" and pt["links"].get("pt-BR") == "/pt-br/"
                     and not os.path.isdir(os.path.join(dist, "pt-br")))
    res["P2"] = bool(fr and fr["lang"] == "en" and fr["links"].get("fr_CA") == "/fr-ca/")
    res["P3"] = bool(es and es["lang"] == "es" and es["links"].get("es") == "/spanish/")
    res["P4"] = bool(de and de["lang"] == "de")
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import astro_locales
        rep = astro_locales.analyse_site(site)
        st = dict((f["dir"], f["status"]) for e in rep["entries"] for f in e["folders"])
        res["checker"] = {"statuses": st, "later": rep["later_segment_pages"],
                          "findings": rep["findings"]}
        res["P5"] = (st.get("pt-BR") == "links_case_only"
                     and st.get("fr-ca") == "current_locale_wrong"
                     and any(x["page"] == "blog/de.astro" for x in rep["later_segment_pages"])
                     and rep["findings"] == 2)
    except Exception as exc:  # report, never crash
        res["checker_error"] = repr(exc)
        res["P5"] = False
    with open(os.path.join(out, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
