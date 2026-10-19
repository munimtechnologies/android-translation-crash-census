#!/usr/bin/env python3
"""Grades l10n-guard 0.11.0's reading-leak warning against the predictions
written before any code (census mt-artifacts/READING-LEAK-PREREG.md):

  P1 nostrmo lib/l10n/intl_ja.arb at 94b8c643, checked against intl_en.arb
     at the same commit: reading-leak on exactly these 18 keys and no others:
     Block, Blocks, Custom, Data, Delete, Login, Members, Method, Note, Notes,
     Posts, Private, Quote, Setting, Soft, Topic, Topics, Url.
  P2 it does not flag nostrmo's Search (検索けんさく), the known miss.
  P3 0 reading-leak warnings on the Japanese files the census already checked,
     at the commits those studies pinned: laravel-eval (Akaunting, UNIT3D,
     Snipe-IT), resx-eval (ONLYOFFICE) and yaml-eval (Sonata, Akeneo, OpenDXP,
     GOV.UK components, OpenStreetMap).
  P4 the unit cases: flagged ロード＃ロード＃ (source load) and 削除＃サクジョ＃
     (source Delete); not flagged ルール＃1, ＃タグ, {count, plural, other
     {＃件}}, ＃サクジョ＃ at the start, and 削除＃サクジョ＃ when the source is
     "Delete #tag".

  python eval_0110.py --guard-dir /out/0110 --out-dir /out/0110-eval

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request

RAW = "https://raw.githubusercontent.com/"
NOSTRMO = RAW + "haorendashu/nostrmo/94b8c643cc8e7f48b5d13f245695fe5fe99a306e/lib/l10n/intl_%s.arb"
P1_KEYS = {"Block", "Blocks", "Custom", "Data", "Delete", "Login", "Members", "Method", "Note",
           "Notes", "Posts", "Private", "Quote", "Setting", "Soft", "Topic", "Topics", "Url"}

AKAUNTING = RAW + "akaunting/akaunting/06dfa473e0d71a5262a58f6f0759c6badf34d5d2/resources/lang/%s/%s.php"
UNIT3D = RAW + "HDInnovations/UNIT3D/8b88f4c8182eb3d3912ffef425c3224dcfd596f4/lang/%s/%s.php"
SNIPEIT = RAW + "grokability/snipe-it/d98baec311438e0818988c130eefa8e813a34c22/resources/lang/%s/%s.php"
ONLYOFFICE = (RAW + "ONLYOFFICE/CommunityServer/fe1fa7babd093969e939ba6ff45a9fee1299dc93/"
              "module/ASC.AuditTrail/AuditReportResource%s.resx")
SONATA = (RAW + "sonata-project/SonataAdminBundle/0b36030299107e2069ee249a68ecd8830b37bf93/"
          "src/Resources/translations/SonataAdminBundle.%s.xliff")
AKENEO = (RAW + "akeneo/pim-community-dev/cfc810e6449651b7d3be4c7db3dd09c71011012c/"
          "src/Akeneo/Pim/Enrichment/Bundle/Resources/translations/validators.%s.yml")
OPENDXP = (RAW + "open-dxp/opendxp/66f8e913af07e69e161d8ca13475537b2bf441fc/"
           "bundles/CoreBundle/translations/admin.%s.yaml")
GOVUK = (RAW + "alphagov/govuk_publishing_components/05d2fbe80380190b285adba9346e071b0d3a7b57/"
         "config/locales/%s.yml")
OSM = (RAW + "openstreetmap/openstreetmap-website/855cda765f5683628bed8a83cdf963958dadc7b7/"
       "config/locales/%s.yml")

# (study, project, kind, source URL, Japanese URL)
P3_FILES = (
    [("laravel-eval", "akaunting", "laravel", AKAUNTING % ("en-GB", "validation"),
      AKAUNTING % ("ja-JP", "validation"))]
    + [("laravel-eval", "unit3d", "laravel", UNIT3D % ("en", name), UNIT3D % ("ja", name))
       for name in ("email", "page", "common", "user", "torrent")]
    + [("laravel-eval", "snipe-it", "laravel", SNIPEIT % ("en-US", "validation"),
        SNIPEIT % ("ja-JP", "validation")),
       ("resx-eval", "onlyoffice", "resx", ONLYOFFICE % "", ONLYOFFICE % ".ja"),
       ("yaml-eval", "sonata", "symfony", SONATA % "en", SONATA % "ja"),
       ("yaml-eval", "akeneo", "symfony", AKENEO % "en_US", AKENEO % "ja_JP"),
       ("yaml-eval", "opendxp", "symfony", OPENDXP % "en", OPENDXP % "ja"),
       ("yaml-eval", "govuk", "rails", GOVUK % "en", GOVUK % "ja"),
       ("yaml-eval", "osm", "rails", OSM % "en", OSM % "ja")])

# P4, as written: (source, target, flagged?)
P4_CASES = [("load", "ロード＃ロード＃", True),
            ("Delete", "削除＃サクジョ＃", True),
            ("Rule 1", "ルール＃1", False),
            ("Tag", "＃タグ", False),
            ("{count, plural, other {{count} items}}", "{count, plural, other {＃件}}", False),
            ("Delete", "＃サクジョ＃", False),
            ("Delete #tag", "削除＃サクジョ＃", False)]


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


def check(g, kind, source_text, text, source_name, name):
    if kind == "laravel":
        return g.check_laravel(source_text, text)
    if kind == "resx":
        return g.check_resx(source_text, text)
    if kind == "symfony":
        return g.check_symfony(source_text, text, source_name, name)
    return g.check_rails(source_text, text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--guard-dir", default="/out/0110")
    parser.add_argument("--out-dir", default="/out/0110-eval")
    args = parser.parse_args()
    g = load(os.path.join(args.guard_dir, "l10n_guard.py"), "guard_0110")
    print("l10n-guard %s" % g.__version__)
    os.makedirs(args.out_dir, exist_ok=True)
    result = {"guard": g.__version__}

    # P1, P2: nostrmo.
    en_data, en_text = fetch(NOSTRMO % "en")
    ja_data, ja_text = fetch(NOSTRMO % "ja")
    en, ja = json.loads(en_text), json.loads(ja_text)
    problems = g.check_arb(en, ja)
    leaks = [p for p in problems if p["code"] == "reading-leak"]
    flagged = {p["key"] for p in leaks}
    with_sign = sorted(k for k, v in g.arb_messages(ja).items() if isinstance(v, str) and "＃" in v)
    print("nostrmo en sha256 %s, ja sha256 %s; %d Japanese values contain ＃"
          % (hashlib.sha256(en_data).hexdigest()[:16], hashlib.sha256(ja_data).hexdigest()[:16],
             len(with_sign)))
    for p in leaks:
        print("nostrmo ja %s [%s]: %s | %s" % (p["level"], p["key"], ja.get(p["key"]), p["message"]))
    other = {}
    for p in problems:
        if p["code"] != "reading-leak":
            other["%s %s" % (p["level"], p["code"])] = other.get("%s %s" % (p["level"], p["code"]), 0) + 1
    print("nostrmo ja other issues: %s" % (other or "none"))
    result["nostrmo"] = {"en_sha256_16": hashlib.sha256(en_data).hexdigest()[:16],
                         "ja_sha256_16": hashlib.sha256(ja_data).hexdigest()[:16],
                         "values_with_fullwidth_number_sign": with_sign,
                         "reading_leak": [{"key": p["key"], "value": ja.get(p["key"]),
                                           "source": en.get(p["key"]), "message": p["message"]}
                                          for p in leaks],
                         "other_issues": other,
                         "search_value": ja.get("Search")}

    # P3: Japanese files of earlier studies.
    p3_rows, p3_leaks, p3_unchecked = [], [], []
    for study, project, kind, source_url, ja_url in P3_FILES:
        row = {"study": study, "project": project, "file": ja_url.split("/")[-1],
               "url": ja_url, "checked": False, "issues": 0, "reading_leak": 0,
               "fullwidth_number_signs": 0, "sha256_16": ""}
        p3_rows.append(row)
        sdata, stext = fetch(source_url)
        tdata, ttext = fetch(ja_url)
        if sdata is None or tdata is None:
            p3_unchecked.append("%s %s: %s not found" % (project, row["file"],
                                                         "source" if sdata is None else "Japanese file"))
            continue
        row["sha256_16"] = hashlib.sha256(tdata).hexdigest()[:16]
        row["fullwidth_number_signs"] = ttext.count("＃")
        try:
            found = check(g, kind, stext, ttext, source_url, ja_url)
        except Exception as exc:  # noqa: BLE001 - every failure is a result here
            p3_unchecked.append("%s %s: %s: %s" % (project, row["file"], type(exc).__name__, exc))
            continue
        row["checked"] = True
        row["issues"] = len(found)
        hits = [dict(p, project=project, file=row["file"]) for p in found if p["code"] == "reading-leak"]
        row["reading_leak"] = len(hits)
        p3_leaks.extend(hits)
        print("P3 %s %s %s: %d issues, %d reading-leak, %d ＃ in the file; sha256 %s"
              % (study, project, row["file"], row["issues"], row["reading_leak"],
                 row["fullwidth_number_signs"], row["sha256_16"]))
    for line in p3_unchecked:
        print("P3 not checked: %s" % line)
    for p in p3_leaks:
        print("P3 reading-leak %s %s [%s]: %s" % (p["project"], p["file"], p.get("key"), p["message"]))
    result["p3_files"] = p3_rows
    result["p3_reading_leak"] = p3_leaks
    result["p3_unchecked"] = p3_unchecked

    # P4: the unit cases.
    p4 = []
    for source, target, want in P4_CASES:
        got = any(p["code"] == "reading-leak" for p in g.check_pair(source, target, "k"))
        p4.append({"source": source, "target": target, "expected": want, "flagged": got})
        print("P4 %r -> %r: expected %s, flagged %s" % (source, target, want, got))

    checks = [
        ("P1", "nostrmo ja: reading-leak on exactly the 18 named keys", flagged == P1_KEYS,
         "%d flagged; missing %s; extra %s" % (len(flagged), sorted(P1_KEYS - flagged) or "none",
                                               sorted(flagged - P1_KEYS) or "none")),
        ("P2", "nostrmo Search (検索けんさく) not flagged",
         "Search" in ja and "Search" not in flagged,
         "Search = %r, flagged %s" % (ja.get("Search"), "Search" in flagged)),
        ("P3", "0 reading-leak warnings on the Japanese files of laravel-eval, resx-eval and "
               "yaml-eval", not p3_leaks and not p3_unchecked,
         "%d files checked, %d not checked, %d reading-leak"
         % (sum(r["checked"] for r in p3_rows), len(p3_unchecked), len(p3_leaks))),
        ("P4", "the seven unit cases", all(c["expected"] == c["flagged"] for c in p4),
         "%d of %d as expected" % (sum(c["expected"] == c["flagged"] for c in p4), len(p4))),
    ]
    for name, text, held, value in checks:
        print("%s %s: %s (%s)" % (name, "HELD" if held else "FAILED", text, value))
    result["p4_cases"] = p4
    result["predictions"] = [{"id": n, "text": t, "held": h, "value": v} for n, t, h, v in checks]
    with open(os.path.join(args.out_dir, "reading_leak_eval.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
