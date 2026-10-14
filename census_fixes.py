#!/usr/bin/env python3
"""Census 0.3.1: census.py 0.3.0 and l10n_guard 0.5.1 with two false-positive
fixes, found by reading Wikipedia's 11 "crash" rows by hand (none crash).

1. Markup that is text in strings.xml stays in the runtime string. A
   <![CDATA[... <a href="%2$s">...</a>]]> or &lt;a href="%2$s"&gt; reaches the
   app as written (apps run it through Html.fromHtml after formatting), so the
   %2$s in its href is a real argument. l10n_guard 0.5.1's _android_text
   dropped every <...>, so the source looked like it passed one argument fewer
   and well-meant translations that kept the link looked like crashes. Only
   real child elements lose their markup (and attributes) at runtime;
   parse_android writes those as bare <name>...</name>.
2. values-qq is translatewiki.net's message documentation (notes for
   translators), not a language any device loads.

  python census_fixes.py --data-dir /data --out-dir /out   # same options as census.py

Licensed under the Apache License, Version 2.0 (Apache-2.0).
Made by MV2 of Munim, Inc. with AI agents.
"""

import re
import sys

import census
import l10n_guard as g

__version__ = "0.3.1"

# How parse_android writes a child element: <name> or </name>, no attributes.
_ELEMENT_RE = re.compile(r"</?[A-Za-z][\w:.-]*/?>")
_TEXT_LT_RE = re.compile(r"<(?!/?[A-Za-z][\w:.-]*/?>)")
_LT = ""  # private use; stands in for a text "<" while 0.5.1 strips tags
NOT_LOCALES = {"qq", "qqq"}

_android_text_051 = g._android_text


def android_text(raw):
    """The string an app gets at runtime from parse_android's text: as
    l10n_guard 0.5.1 computes it, except that markup which is text in the
    XML (CDATA, &lt;...&gt;) is kept, placeholders in its attributes included."""
    return _android_text_051(_TEXT_LT_RE.sub(_LT, raw)).replace(_LT, "<")


def apply():
    """Points census.py at the fixed functions. Safe to call twice."""
    g._android_text = android_text
    census.NOT_LOCALES.update(NOT_LOCALES)
    census.__version__ = __version__
    census.USER_AGENT = ("mv2-translation-crash-census/%s (Munim, Inc.; munimversion2@gmail.com)"
                         % __version__)


if __name__ == "__main__":
    apply()
    sys.exit(census.main())
