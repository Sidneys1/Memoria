import re
from typing import Iterable

from memoria.plugins.allowlist import AllowlistRule, Hostname, InputItem

_DOC_HTML = """<p>Matches a URL if the entire URL matches the given regular expression.<p>
<p>If the value begins with "<code>i</code>", the match is case insensitive.</p>"""
_DOC_EXAMPLES = [
    ('https?://[^/]+/$', """Matches an <samp>http</samp> or <samp>https</samp> URL at the root path (e.g., <code>https://example.com/</code>)."""),
]

class RegexAllowlistRule(AllowlistRule):
    _rule_cache: dict[Hostname, list[re.Pattern[str]]]

    DISPLAY_OPTIONS = AllowlistRule.DisplayOptions(prefix='RegEx', color='#ac6218')

    LONG_DOCUMENTATION = _DOC_HTML
    LONG_DOC_EXAMPLES = _DOC_EXAMPLES

    async def __aenter__(self):
        self._rule_cache = {}
        return await super().__aenter__()

    async def __aexit__(self, *_, **__):
        del self._rule_cache

    @staticmethod
    def _compile_rules(definitions: Iterable[str]) -> Iterable[re.Pattern[str]]:
        if definitions is None:
            return
        for definition in definitions:
            if definition.startswith('i'):
                yield re.compile(definition[1:], re.IGNORECASE)
            else:
                yield re.compile(definition)

    async def matches(self, item: InputItem, rules: Iterable[str]) -> bool:
        if item[0] not in self._rule_cache:
            # Populate cache
            compiled_rules = self._rule_cache[item[0]] = list(self._compile_rules(rules))
        else:
            compiled_rules = self._rule_cache[item[0]]

        # Check if any of our rules match...
        return any(r.search(item[1]) is not None for r in compiled_rules)
