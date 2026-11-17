# Copyright 2026 Munim, Inc. Licensed under the Apache License, Version 2.0 (Apache-2.0).
# Made with AI agents by MV2 of Munim, Inc.
"""Write a minimal Starlight site with one page per locale (see PREREG.md)."""
import json
import os
import sys

# folder key -> lang (None = root)
LOCALES = [
    ("root", "en"),
    ("zh-tw", "zh-TW"),
    ("zh-cn", "zh-CN"),
    ("es-mx", "es-MX"),
    ("zh-hant", "zh-Hant"),
    ("zh-hans", "zh-Hans"),
    ("zh-hk", "zh-HK"),
    ("es-419", "es-419"),
    ("zh-hant-tw", "zh-Hant-TW"),
]

PAGE = """---
title: Test page {key}
---

Test page for the locale {key} (lang {lang}).

## Section one

First section.

## Section two

Second section.
"""

CONTENT_CONFIG = """import { defineCollection } from 'astro:content';
import { docsLoader } from '@astrojs/starlight/loaders';
import { docsSchema } from '@astrojs/starlight/schema';

export const collections = {
  docs: defineCollection({ loader: docsLoader(), schema: docsSchema() }),
};
"""


def main(site):
    os.makedirs(site, exist_ok=True)
    locales = {}
    for key, lang in LOCALES:
        locales[key] = {"label": "L " + key, "lang": lang}
    cfg = (
        "import { defineConfig } from 'astro/config';\n"
        "import starlight from '@astrojs/starlight';\n\n"
        "export default defineConfig({\n"
        "  integrations: [\n"
        "    starlight({\n"
        "      title: 'Script tag test',\n"
        "      locales: " + json.dumps(locales, indent=2) + ",\n"
        "    }),\n"
        "  ],\n"
        "});\n"
    )
    with open(os.path.join(site, "astro.config.mjs"), "w", encoding="utf-8") as f:
        f.write(cfg)
    with open(os.path.join(site, "package.json"), "w", encoding="utf-8") as f:
        json.dump({"name": "starlight-script-test", "private": True, "type": "module"}, f, indent=2)
    os.makedirs(os.path.join(site, "src", "content", "docs"), exist_ok=True)
    with open(os.path.join(site, "src", "content.config.ts"), "w", encoding="utf-8") as f:
        f.write(CONTENT_CONFIG)
    for key, lang in LOCALES:
        if key == "root":
            d = os.path.join(site, "src", "content", "docs")
        else:
            d = os.path.join(site, "src", "content", "docs", key)
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as f:
            f.write(PAGE.format(key=key, lang=lang))
    print("site written:", site, "locales:", len(LOCALES))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "site")
