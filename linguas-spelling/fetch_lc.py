# Fetches linguas census v1 (linguas/linguas_census.py) unchanged from the public census repo,
# so linguas_spelling.py reuses exactly the code that produced linguas/v1/.
# Made with AI agents by MV2 of Munim, Inc. Licence: Apache-2.0.
import hashlib
import sys
import urllib.request

URL = ("https://raw.githubusercontent.com/munimtechnologies/android-translation-crash-census/"
       "main/linguas/linguas_census.py")

req = urllib.request.Request(URL, headers={"User-Agent": "linguas-spelling (MV2, Munim, Inc.)"})
data = urllib.request.urlopen(req, timeout=120).read()
if b"linguas census PREREG v1" not in data:
    sys.exit("unexpected linguas_census.py")
with open("linguas_census.py", "wb") as fh:
    fh.write(data)
print("linguas_census.py sha256", hashlib.sha256(data).hexdigest(), len(data), "bytes")
