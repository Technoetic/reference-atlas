"""Parse the real mount markup to verify the catalog's plugins are selectable."""
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SelectOptions(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current_select = None
        self.options = {}

    def handle_starttag(self, tag, attributes):
        attributes = dict(attributes)
        if tag == 'select':
            self.current_select = attributes.get('id')
            self.options[self.current_select] = []
        elif tag == 'option' and self.current_select is not None:
            self.options[self.current_select].append(attributes.get('value'))

    def handle_endtag(self, tag):
        if tag == 'select':
            self.current_select = None


class SourceFilterMarkupTests(unittest.TestCase):
    def test_every_catalog_plugin_has_a_real_selectable_option(self):
        module = (ROOT / 'src/screens/sources.mjs').read_text(encoding='utf-8')
        match = re.search(r'\bmount\(\)\s*\{\s*this\.element\.innerHTML\s*=\s*`(.*?)`;', module, re.S)
        self.assertIsNotNone(match, 'Expected the actual static mount template')
        parser = SelectOptions()
        parser.feed(match[1])
        catalog = json.loads((ROOT / 'data/catalog.json').read_text(encoding='utf-8'))
        plugin_ids = {use['plugin'] for source in catalog['sources'] for use in source['uses']}
        expected = plugin_ids | {'all', 'shared'}
        actual = parser.options['plugin-filter']
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(expected), 'Plugin options must not be duplicated')


if __name__ == '__main__':
    unittest.main()
