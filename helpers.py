import itertools
import re
from typing import Any, Iterable

CATEGORIES = ["Advantageous", "Disadvantageous", "Game Breaking", "Avoidable Game Breaking", "Graphical", "Non-Functional ability"]
BADCATS = ["Game Breaking"]

AFFECTS_REGEX = r'^Affects: (.*)$'
SEEALSO_REGEX = r'^See Also: (.*)$'
DISCORD_REGEX = r'^Reported on Discord by (\w+#[0-9]+)$'
IMAGES_REGEX = r'^<!-- Images --> (.*)$'
REGEX_CARDREF = r'\[?\[([^\]]*)\]\]?'
REGEX_SEARCHREF = r'\{([\w:/^$]+)\}'


BAD_AFFECTS_REGEX = r'Affects: (\[Card Name\]\(, \[Second Card name\], etc\)\r?\n)\['

CODE_REGEX = r'^Code: (.*)$'
BBT_REGEX = r'^Bug Blog Text: (.*)$'

def remove_smartquotes(text: str) -> str:
    return text.replace('’', "'").replace('“', '"').replace('”', '"')

def strip_squarebrackets(title: str) -> str:
    def get_name(match):
        return match.group(1).strip()
    title = re.sub(REGEX_CARDREF, get_name, title)
    return title

def grouper(n: int, iterable: Iterable, fillvalue: Any = None):
    "grouper(3, 'ABCDEFG', 'x') --> ABC DEF Gxx"
    args = [iter(iterable)] * n
    return itertools.zip_longest(*args, fillvalue=fillvalue)
