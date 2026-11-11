# SPDX-License-Identifier: Apache-2.0
# Tests for list_components.py - MV2, Munim, Inc. (made with AI agents)
import unittest

import list_components as lc


class Tests(unittest.TestCase):
    def test_normalize(self):
        self.assertEqual(lc.normalize_repo('git@github.com:p0deje/Maccy.git'),
                         'https://github.com/p0deje/Maccy')
        self.assertEqual(lc.normalize_repo('https://GitHub.com/a/b/'), 'https://github.com/a/b')
        self.assertEqual(lc.normalize_repo('http://user@gitlab.com/a/b.git'), 'https://gitlab.com/a/b')
        self.assertEqual(lc.normalize_repo('ssh://git@codeberg.org/a/b.git'), 'https://codeberg.org/a/b')
        self.assertEqual(lc.normalize_repo(''), '')

    def test_is_apple(self):
        self.assertTrue(lc.is_apple('strings-utf8', 'Maccy/*.lproj/Localizable.strings'))
        self.assertTrue(lc.is_apple('xcstrings', 'App/Localizable.xcstrings'))
        self.assertTrue(lc.is_apple('po', 'Res/*.lproj/x.po'))
        self.assertFalse(lc.is_apple('aresource', 'app/src/main/res/values-*/strings.xml'))
        self.assertFalse(lc.is_apple(None, None))

    def test_row_of(self):
        r = lc.row_of({'slug': 'app', 'project': {'slug': 'maccy'}, 'file_format': 'strings-utf8',
                       'filemask': 'Maccy/*.lproj/Localizable.strings', 'template': None,
                       'repo': 'https://github.com/p0deje/Maccy.git', 'branch': 'master'})
        self.assertEqual(r['project'], 'maccy')
        self.assertEqual(r['repo_norm'], 'https://github.com/p0deje/Maccy')
        self.assertEqual(r['apple'], '1')
        self.assertEqual(r['template'], '')
        linked = lc.row_of({'slug': 'b', 'project': {'slug': 'maccy'}, 'file_format': 'strings-utf8',
                            'filemask': 'x/*.lproj/a.strings', 'repo': 'weblate://maccy/app'})
        self.assertEqual(linked['repo_norm'], '')


if __name__ == '__main__':
    unittest.main()
