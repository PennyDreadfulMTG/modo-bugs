import re

CATEGORIES = ["Advantageous", "Disadvantageous", "Game Breaking", "Avoidable Game Breaking", "Graphical", "Non-Functional ability"]
BADCATS = ["Game Breaking"]

AFFECTS_REGEX = r'^Affects: (.*)$'
DISCORD_REGEX = r'^Reported on Discord by (\w+#[0-9]+)$'
IMAGES_REGEX = r'^<!-- Images --> (.*)$'
REGEX_CARDREF = r'\[?\[([^\]]*)\]\]?'

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
