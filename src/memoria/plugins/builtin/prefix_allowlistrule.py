import re
from logging import getLogger
from typing import Iterable

from memoria.plugins.allowlist import AllowlistRule, Hostname, InputItem

_DOC_HTML = """<p>Matches a URL if the URL path segment begins with the given value.</p>
<p>If the value begins with "<code>i</code>", the match is case insensitive.</p>"""
_DOC_EXAMPLES = [
    ('/foo/', """All pages below <code>/foo/[…]</code>."""),
    ('i/foo/', """All pages below <code>/foo/[…]</code> (case insensitive). Note that this incudes <em>both</em> <code>/foo</code> and <code>/<u>F</u>oo</code>."""),
    ('/bar',
     """All pages below <code>/bar</code>. Note that this incudes <em>both</em> <code>/bar</code> and <code>/bar<u>ley</u></code>."""
     )
]

class PrefixAllowlistRule(AllowlistRule):
    _LOG = getLogger(__module__ + '.PrefixAllowlistRule')
    _rule_cache: dict[Hostname, list[re.Pattern[str]]]

    DISPLAY_OPTIONS = AllowlistRule.DisplayOptions(prefix='Starts With', color='#86b42b')

    LONG_DOCUMENTATION = _DOC_HTML
    LONG_DOC_EXAMPLES = _DOC_EXAMPLES

    async def __aenter__(self):
        self._rule_cache = {}
        return await super().__aenter__()

    async def __aexit__(self, *_, **__):
        del self._rule_cache

    @staticmethod
    def _compile_rules(definitions: Iterable[str]) -> Iterable[re.Pattern[str]]:
        for definition in definitions:
            if definition.startswith('i/'):
                yield re.compile(r'^' + re.escape(definition[1:]), re.IGNORECASE)
            elif definition.startswith('/'):
                yield re.compile(r'^' + re.escape(definition))

    async def matches(self, item: InputItem, rules: Iterable[str]) -> bool:
        if item[0] not in self._rule_cache:
            # Populate cache
            compiled_rules = self._rule_cache[item[0]] = list(self._compile_rules(rules))
        else:
            compiled_rules = self._rule_cache[item[0]]

        # Check if any of our rules match...
        return any(r.match(item[2].path) is not None for r in compiled_rules)
