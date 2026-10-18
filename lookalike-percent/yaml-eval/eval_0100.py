#!/usr/bin/env python3
"""Runs l10n-guard 0.10.0 (kinds: symfony, rails) on every translation of
five open-source projects, pinned to one commit each:

  SonataAdminBundle  src/Resources/translations/SonataAdminBundle.<lang>.xliff, against en
  Akeneo PIM         .../Enrichment/Bundle/Resources/translations/validators.<lang>.yml, against en_US
  OpenDXP            bundles/CoreBundle/translations/admin.<lang>.yaml, against en
  GOV.UK components  config/locales/<lang>.yml, against en
  OpenStreetMap      config/locales/{ar,ja}.yml, against en

Predictions, written before the run (census lookalike-percent/YAML-PREREG.md):
  P1 Sonata: lookalike-percent errors only in ja and zh_CN, only on
     flash_lock_error, exactly 3 in each.
  P2 Akeneo: the only lookalike-percent error is zh_TW family_variant_no_axis;
     tr_TR family_variant_no_axis has a placeholder-missing error naming %level%.
  P3 OpenDXP: lookalike-percent errors only in zh_Hans, only on
     workflow_change_email_notification_text, exactly 4.
  P4 GOV.UK: lookalike-percent errors only in ja, 7 of them, on exactly six
     keys (toggle_more, character_count.body, cookie_banner.confirmation_message.html,
     attachment.page.other, scoped_search_description, all_content_search_description).
  P5 OpenStreetMap: ar has lookalike-percent warnings and no lookalike-percent
     errors, on exactly three keys (about.heading_html, copyright.native.html,
     contributors_fi_credit_html); ja has exactly one lookalike-percent issue,
     an error on no_applications_html.
  P6 every lookalike-percent error is in a Chinese, Japanese or Arabic file.
  P7 every file present parses, and every source file has at least 50 string messages.

  python eval_0100.py --guard-dir /out/0100 --out-dir /out/0100-eval

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request

RAW = "https://raw.githubusercontent.com/"
PROJECTS = [
    {"name": "sonata", "kind": "symfony",
     "base": RAW + "sonata-project/SonataAdminBundle/0b36030299107e2069ee249a68ecd8830b37bf93/"
                   "src/Resources/translations/SonataAdminBundle.%s.xliff",
     "source": "en",
     "langs": "ar bg bs ca cs de es eu fa fr hr hu it ja lb lt lv nl no pl pt pt_BR ro ru sk sl "
              "sr_Cyrl sr_Latn sv_SE tr uk zh_CN zh_HK"},
    {"name": "akeneo", "kind": "symfony",
     "base": RAW + "akeneo/pim-community-dev/cfc810e6449651b7d3be4c7db3dd09c71011012c/"
                   "src/Akeneo/Pim/Enrichment/Bundle/Resources/translations/validators.%s.yml",
     "source": "en_US",
     "langs": "ca_ES da_DK de_DE en_AU en_GB en_NZ es_ES es_VE fi_FI fr_FR hr_HR it_IT ja_JP "
              "ko_KR nl_NL no_NO pl_PL pt_BR pt_PT ro_RO ru_RU sv_SE tl_PH tr_TR uk_UA vi_VN "
              "zh_CN zh_TW"},
    {"name": "opendxp", "kind": "symfony",
     "base": RAW + "open-dxp/opendxp/66f8e913af07e69e161d8ca13475537b2bf441fc/"
                   "bundles/CoreBundle/translations/admin.%s.yaml",
     "source": "en",
     "langs": "ca cs de es fr hu it ja nl pl pt pt_br ru sk sv sv_fi th tr uk zh_Hans"},
    {"name": "govuk", "kind": "rails",
     "base": RAW + "alphagov/govuk_publishing_components/05d2fbe80380190b285adba9346e071b0d3a7b57/"
                   "config/locales/%s.yml",
     "source": "en",
     "langs": "ar az be bg bn cs cy da de dr el es-419 es et fa fi fr gd gu he hi hr hu hy id is "
              "it ja ka kk ko ku ky lt lv ms mt ne nl no pa-pk pa pl ps pt ro ru si sk sl so sq "
              "sr sv sw ta th ti tk tr uk ur uz vi zh-hk zh-tw zh"},
    {"name": "osm", "kind": "rails",
     "base": RAW + "openstreetmap/openstreetmap-website/855cda765f5683628bed8a83cdf963958dadc7b7/"
                   "config/locales/%s.yml",
     "source": "en", "langs": "ar ja"},
]
GOVUK_JA = ("toggle_more", "character_count.body", "cookie_banner.confirmation_message.html",
            "attachment.page.other", "scoped_search_description", "all_content_search_description")
OSM_AR = ("about.heading_html", "copyright.native.html", "contributors_fi_credit_html")
CJK_ARABIC = ("zh", "ja", "ar", "fa", "ur", "ps", "ku", "sd", "ug", "ckb", "dr", "pa-pk")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fetch(url):
    """(bytes, text), or (None, None) when the file doesn't exist."""
    req = urllib.request.Request(url, headers={"User-Agent": "mv2-l10n-guard-eval"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = r.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None, None
        raise
    return data, data.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


def messages(g, project, text, name):
    if project["kind"] == "symfony":
        return g.parse_symfony(text, name)
    return g.flatten(g._rails_root(g.parse_yaml(text)))


def check(g, project, source_text, text, source_name, name):
    if project["kind"] == "symfony":
        return g.check_symfony(source_text, text, source_name, name)
    return g.check_rails(source_text, text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--guard-dir", default="/out/0100")
    parser.add_argument("--out-dir", default="/out/0100-eval")
    args = parser.parse_args()
    g = load(os.path.join(args.guard_dir, "l10n_guard.py"), "guard_0100")
    print("l10n-guard %s" % g.__version__)
    os.makedirs(args.out_dir, exist_ok=True)

    rows, lookalikes, parse_errors, source_keys, totals = [], [], [], {}, {}
    for project in PROJECTS:
        source_name = project["base"] % project["source"]
        data, source_text = fetch(source_name)
        if data is None:
            parse_errors.append({"project": project["name"], "lang": project["source"],
                                 "error": "source file not found"})
            continue
        try:
            source = messages(g, project, source_text, source_name)
        except Exception as exc:  # noqa: BLE001 - every failure is a parse result here
            parse_errors.append({"project": project["name"], "lang": project["source"],
                                 "error": "%s: %s" % (type(exc).__name__, exc)})
            continue
        strings = sum(1 for v in source.values() if isinstance(v, str))
        source_keys[project["name"]] = strings
        print("%s %s: %d string messages, sha256 %s" % (
            project["name"], project["source"], strings, hashlib.sha256(data).hexdigest()[:16]))
        for lang in project["langs"].split():
            row = {"project": project["name"], "lang": lang, "present": 0, "parsed": 0,
                   "string_messages": 0, "errors": 0, "warnings": 0,
                   "lookalike_percent_errors": 0, "lookalike_percent_error_keys": 0,
                   "lookalike_percent_warnings": 0, "lookalike_brace": 0,
                   "placeholder_missing_keys": 0, "sha256_16": ""}
            rows.append(row)
            name = project["base"] % lang
            data, text = fetch(name)
            if data is None:
                continue
            row["present"], row["sha256_16"] = 1, hashlib.sha256(data).hexdigest()[:16]
            try:
                target = messages(g, project, text, name)
                problems = check(g, project, source_text, text, source_name, name)
            except Exception as exc:  # noqa: BLE001 - every failure is a parse result here
                parse_errors.append({"project": project["name"], "lang": lang,
                                     "error": "%s: %s" % (type(exc).__name__, exc)})
                continue
            row["parsed"] = 1
            row["string_messages"] = sum(1 for v in target.values() if isinstance(v, str))
            row["errors"] = sum(1 for p in problems if p["level"] == g.ERROR)
            row["warnings"] = len(problems) - row["errors"]
            percent = [p for p in problems if p["code"] == "lookalike-percent"]
            errors = [p for p in percent if p["level"] == g.ERROR]
            row["lookalike_percent_errors"] = len(errors)
            row["lookalike_percent_error_keys"] = len({p["key"] for p in errors})
            row["lookalike_percent_warnings"] = len(percent) - len(errors)
            row["lookalike_brace"] = sum(1 for p in problems if p["code"] == "lookalike-brace")
            row["placeholder_missing_keys"] = len({p["key"] for p in problems
                                                   if p["code"] == "placeholder-missing"})
            for p in problems:
                totals.setdefault(project["name"], {}).setdefault(
                    "%s %s" % (p["level"], p["code"]), 0)
                totals[project["name"]]["%s %s" % (p["level"], p["code"])] += 1
                if p["code"] in ("lookalike-percent", "lookalike-brace") or (
                        p["code"] == "placeholder-missing" and project["name"] == "akeneo"
                        and p["key"].endswith("family_variant_no_axis")):
                    lookalikes.append(dict(p, project=project["name"], lang=lang))
            print("%s %s: %d messages, %d errors, %d warnings; lookalike-percent errors %d on "
                  "%d keys, warnings %d; sha256 %s" % (
                      project["name"], lang, row["string_messages"], row["errors"],
                      row["warnings"], row["lookalike_percent_errors"],
                      row["lookalike_percent_error_keys"], row["lookalike_percent_warnings"],
                      row["sha256_16"]))

    present = [r for r in rows if r["present"]]
    print("files: %d looked for, %d present, %d parsed; parse errors %d"
          % (len(rows), len(present), sum(r["parsed"] for r in present), len(parse_errors)))
    for e in parse_errors:
        print("parse error: %(project)s %(lang)s: %(error)s" % e)
    for p in lookalikes:
        print("%s %s %s %s [%s]: %s" % (p["project"], p["lang"], p["level"], p["code"], p["key"],
                                        p["message"]))
    for project, counts in sorted(totals.items()):
        print("%s totals: %s" % (project, ", ".join("%s %d" % kv for kv in sorted(counts.items()))))

    def percent(project, lang=None, level=None):
        return [p for p in lookalikes if p["project"] == project and p["code"] == "lookalike-percent"
                and (lang is None or p["lang"] == lang) and (level is None or p["level"] == level)]

    def langs_with_errors(project):
        return sorted({p["lang"] for p in percent(project, level=g.ERROR)})

    sonata_ok = (langs_with_errors("sonata") == ["ja", "zh_CN"]
                 and all(len(percent("sonata", lang, g.ERROR)) == 3
                         and {p["key"] for p in percent("sonata", lang, g.ERROR)} == {"flash_lock_error"}
                         for lang in ("ja", "zh_CN")))
    akeneo_errors = percent("akeneo", level=g.ERROR)
    tr_missing = [p for p in lookalikes if p["project"] == "akeneo" and p["lang"] == "tr_TR"
                  and p["code"] == "placeholder-missing" and "%level%" in p["message"]]
    opendxp = percent("opendxp", level=g.ERROR)
    govuk = percent("govuk", level=g.ERROR)
    govuk_keys = {p["key"] for p in govuk}
    osm_ar, osm_ja = percent("osm", "ar"), percent("osm", "ja")
    outside = sorted({"%s %s" % (p["project"], p["lang"]) for p in lookalikes
                      if p["code"] == "lookalike-percent" and p["level"] == g.ERROR
                      and not p["lang"].lower().startswith(CJK_ARABIC)})
    checks = [
        ("P1", "Sonata: lookalike-percent errors only in ja and zh_CN, only on flash_lock_error, "
               "3 in each", sonata_ok,
         "; ".join("%s %d %s" % (lang, len(percent("sonata", lang, g.ERROR)),
                                 sorted({p["key"] for p in percent("sonata", lang, g.ERROR)}))
                   for lang in langs_with_errors("sonata")) or "none"),
        ("P2", "Akeneo: only lookalike-percent error is zh_TW family_variant_no_axis; tr_TR "
               "placeholder-missing names %level%",
         len(akeneo_errors) == 1 and akeneo_errors[0]["lang"] == "zh_TW"
         and akeneo_errors[0]["key"].endswith("family_variant_no_axis") and bool(tr_missing),
         "%s; tr_TR missing %d" % ([(p["lang"], p["key"]) for p in akeneo_errors], len(tr_missing))),
        ("P3", "OpenDXP: lookalike-percent errors only in zh_Hans, only on "
               "workflow_change_email_notification_text, 4",
         len(opendxp) == 4 and all(p["lang"] == "zh_Hans" and p["key"] ==
                                   "workflow_change_email_notification_text" for p in opendxp),
         str(sorted({(p["lang"], p["key"]) for p in opendxp})) + " %d" % len(opendxp)),
        ("P4", "GOV.UK: lookalike-percent errors only in ja, 7, on exactly the six keys",
         len(govuk) == 7 and all(p["lang"] == "ja" for p in govuk) and len(govuk_keys) == 6
         and all(any(k.endswith(want) for k in govuk_keys) for want in GOVUK_JA),
         "%d errors, langs %s, keys %s" % (len(govuk), sorted({p["lang"] for p in govuk}),
                                           sorted(govuk_keys))),
        ("P5", "OpenStreetMap: ar only warnings, on the three keys; ja one error on "
               "no_applications_html",
         bool(osm_ar) and all(p["level"] == g.WARNING for p in osm_ar)
         and len({p["key"] for p in osm_ar}) == 3
         and all(any(p["key"].endswith(want) for p in osm_ar) for want in OSM_AR)
         and len(osm_ja) == 1 and osm_ja[0]["level"] == g.ERROR
         and osm_ja[0]["key"].endswith("no_applications_html"),
         "ar %s; ja %s" % (sorted({(p["level"], p["key"]) for p in osm_ar}),
                           [(p["level"], p["key"]) for p in osm_ja])),
        ("P6", "every lookalike-percent error is in a Chinese, Japanese or Arabic-script file",
         not outside, ", ".join(outside) or "none outside"),
        ("P7", "every file present parses, and every source has at least 50 string messages",
         not parse_errors and len(source_keys) == len(PROJECTS)
         and all(v >= 50 for v in source_keys.values()),
         "%d parse errors; %s" % (len(parse_errors), source_keys)),
    ]
    for name, text, held, value in checks:
        print("%s %s: %s (%s)" % (name, "HELD" if held else "FAILED", text, value))

    with open(os.path.join(args.out_dir, "yaml_files.csv"), "w", encoding="utf-8",
              newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    with open(os.path.join(args.out_dir, "yaml_eval.json"), "w", encoding="utf-8") as f:
        json.dump({"guard": g.__version__,
                   "projects": [{k: p[k] for k in ("name", "kind", "base", "source")}
                                for p in PROJECTS],
                   "source_string_messages": source_keys, "totals": totals,
                   "lookalikes": lookalikes, "parse_errors": parse_errors,
                   "predictions": [{"id": n, "text": t, "held": h, "value": str(v)}
                                   for n, t, h, v in checks]},
                  f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
