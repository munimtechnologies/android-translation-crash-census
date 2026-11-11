#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# list_components.py - MV2, Munim, Inc. (made with AI agents)
"""Stage 1 of the weblate-apple census: list every component on Hosted
Weblate whose translations are Apple .strings / .stringsdict / .xcstrings
files, with its repository URL. Reads only Weblate's public API (component
metadata); reads no repository and no project file.

usage: list_components.py <out_dir> [max_pages]
"""
import csv
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

API = 'https://hosted.weblate.org/api/components/?page_size=1000'
UA = 'MV2-l10n-census/1.0 (Munim, Inc.; mv2@munimtech.com; one-time public listing)'
APPLE_FORMATS = {'strings', 'strings-utf8', 'stringsdict', 'xcstrings'}
FIELDS = ['project', 'component', 'file_format', 'filemask', 'template', 'repo', 'branch',
          'repo_norm', 'apple']


def normalize_repo(url):
    if not url:
        return ''
    u = url.strip()
    m = re.match(r'^(?:ssh://)?git@([^:/]+)[:/](.+)$', u)
    if m:
        u = 'https://%s/%s' % (m.group(1), m.group(2))
    u = re.sub(r'^http://', 'https://', u)
    u = re.sub(r'^https://[^/@]+@', 'https://', u)
    if u.endswith('/'):
        u = u[:-1]
    if u.endswith('.git'):
        u = u[:-4]
    m = re.match(r'^https://([^/]+)(/.*)?$', u)
    if m:
        u = 'https://' + m.group(1).lower() + (m.group(2) or '')
    return u


def is_apple(fmt, filemask):
    return (fmt or '') in APPLE_FORMATS or '.lproj/' in (filemask or '')


def row_of(c):
    proj = c.get('project') or {}
    fmt = c.get('file_format') or ''
    mask = c.get('filemask') or ''
    repo = c.get('repo') or ''
    return {
        'project': proj.get('slug', '') if isinstance(proj, dict) else str(proj),
        'component': c.get('slug', ''),
        'file_format': fmt,
        'filemask': mask,
        'template': c.get('template') or '',
        'repo': repo,
        'branch': c.get('branch') or '',
        'repo_norm': '' if repo.startswith('weblate://') else normalize_repo(repo),
        'apple': '1' if is_apple(fmt, mask) else '0',
    }


def fetch(url, log):
    for attempt in range(6):
        req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode('utf-8')), r.status
        except urllib.error.HTTPError as e:
            log.append({'url': url, 'status': e.code, 'attempt': attempt,
                        'retry_after': e.headers.get('Retry-After')})
            if e.code == 429:
                try:
                    wait = int(e.headers.get('Retry-After') or 120)
                except ValueError:
                    wait = 120
                if wait > 1800:
                    return None, 429
                time.sleep(wait + 2)
                continue
            if e.code >= 500:
                time.sleep(60)
                continue
            return None, e.code
        except Exception as e:  # network errors
            log.append({'url': url, 'error': repr(e), 'attempt': attempt})
            time.sleep(60)
    return None, -1


def main(argv):
    out = argv[1]
    max_pages = int(argv[2]) if len(argv) > 2 else 200
    os.makedirs(out, exist_ok=True)
    log = []
    rows = []
    url = API
    pages = 0
    expected = None
    stop = 'done'
    while url and pages < max_pages:
        data, status = fetch(url, log)
        if data is None:
            stop = 'http %s at page %d' % (status, pages + 1)
            break
        pages += 1
        if expected is None:
            expected = data.get('count')
        for c in data.get('results', []):
            rows.append(row_of(c))
        url = data.get('next')
        print('page %d: %d rows so far (count %s)' % (pages, len(rows), expected), flush=True)
        time.sleep(3)
    if url and stop == 'done':
        stop = 'max_pages reached'
    with open(os.path.join(out, 'components.csv'), 'w', newline='', encoding='utf-8') as fp:
        w = csv.DictWriter(fp, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    apple = [r for r in rows if r['apple'] == '1']
    with open(os.path.join(out, 'apple_components.csv'), 'w', newline='', encoding='utf-8') as fp:
        w = csv.DictWriter(fp, fieldnames=FIELDS)
        w.writeheader()
        for r in apple:
            w.writerow(r)
    repos = {}
    for r in apple:
        key = r['repo_norm'] or ('linked:' + r['repo'])
        repos.setdefault(key, []).append('%s/%s' % (r['project'], r['component']))
    with open(os.path.join(out, 'apple_repos.csv'), 'w', newline='', encoding='utf-8') as fp:
        w = csv.writer(fp)
        w.writerow(['repo', 'components'])
        for k in sorted(repos):
            w.writerow([k, ' '.join(sorted(repos[k]))])
    fmt_counts = {}
    for r in apple:
        fmt_counts[r['file_format']] = fmt_counts.get(r['file_format'], 0) + 1
    hosts = {}
    for k in repos:
        m = re.match(r'^https://([^/]+)/', k)
        h = m.group(1) if m else 'other'
        hosts[h] = hosts.get(h, 0) + 1
    summary = {
        'stop': stop, 'pages': pages, 'api_count': expected, 'components_read': len(rows),
        'apple_components': len(apple), 'apple_repos': len(repos),
        'apple_formats': fmt_counts, 'apple_repo_hosts': hosts,
        'retries_and_errors': log[:50],
        'complete': stop == 'done' and expected is not None and len(rows) == expected,
    }
    with open(os.path.join(out, 'listing.json'), 'w', encoding='utf-8') as fp:
        json.dump(summary, fp, indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != 'retries_and_errors'}, indent=1))
    return 0 if pages > 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
