import codecs
import re
import sys
import datetime
import urllib.parse
import json
from typing import Any, Dict, List

import requests
from github import Github

import configuration
from helpers import remove_smartquotes



CATEGORIES = ["Advantageous", "Disadvantageous", "Game Breaking", "Graphical", "Non-Functional ability"]
BADCATS = ["Game Breaking"]

LEGAL_CARDS: List[str] = []

ALL_BUGS: List[Dict] = []

ALL_CSV: List[str] = []
ALL_BANNED: List[str] = []
PD_BANNED: List[str] = []

AFFECTS_REGEX = r'^Affects: (.*)$'
DISCORD_REGEX = r'^Reported on Discord by (\w+#[0-9]+)$'
IMAGES_REGEX = r'^<!-- Images --> (.*)$'

BAD_AFFECTS_REGEX = r'Affects: (\[Card Name\]\(, \[Second Card name\], etc\)\r?\n)\['

if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def fetch_pd_legal() -> None:
    print('Fetching http://pdmtgo.com/legal_cards.txt')
    for card in requests.get('http://pdmtgo.com/legal_cards.txt').text.split('\n'):
        LEGAL_CARDS.append(card)


def main() -> None:
    if configuration.get("github_user") is None or configuration.get("github_password") is None:
        print('Invalid Config')
        exit(1)

    fetch_pd_legal()

    github = Github(configuration.get("github_user"), configuration.get("github_password"))
    repo = github.get_repo("PennyDreadfulMTG/modo-bugs")

    issues = repo.get_issues()
    # if os.path.exists('bugs.tsv'):
    #     os.remove('bugs.tsv')
    for issue in issues:
        print(issue.title)
        if issue.state == "open":
            process_issue(issue)

    csv = open('bugs.tsv', mode='w')
    csv.write("Card Name\tBug Description\tCategorization\tLast Confirmed\n")
    ALL_CSV.sort()
    for line in ALL_CSV:
        csv.write(line + '\n')
    csv.close()

    txt = open('bannable.txt', mode='w')
    ALL_BANNED.sort()
    for line in ALL_BANNED:
        txt.write(line + '\n')
    txt.close()

    txt = open('pd_bannable.txt', mode='w')
    PD_BANNED.sort()
    for line in PD_BANNED:
        txt.write(line + '\n')
    txt.close()

    bugsjson = open('bugs.json', mode='w')
    json.dump(ALL_BUGS, bugsjson, indent=2)
    bugsjson.close()

def process_issue(issue):
    age = (datetime.datetime.now() - issue.updated_at).days
    if age < 5:
        fix_user_errors(issue)
    labels = [c.name for c in issue.labels]
    affects = re.search(AFFECTS_REGEX, issue.body, re.MULTILINE)
    if affects is None:
        affects = issue.title
    else:
        affects = affects.group(1)

    cards = re.findall(r'\[?\[([^\]]*)\]\]?', affects)
    cards = [c for c in cards]

    images = re.search(IMAGES_REGEX, issue.body, re.MULTILINE)
    if len(cards) > 1:
        width = '200px'
    else:
        width = '300px'
    expected = '<!-- Images --> ' + ''.join(['<img src="https://api.scryfall.com/cards/named?exact={0}&format=image" width="{1}">'.format(urllib.parse.quote(c), width) for c in cards])
    if age < 5:
        if not images:
            print('Adding Images...')
            body = issue.body + '\n' + expected
            issue.edit(body=body)
        elif images.group(0) != expected:
            print('Updating images...')
            body = issue.body.replace(images.group(0), expected)
            issue.edit(body=body)

    pd_legal = ([True for c in cards if c in LEGAL_CARDS] or [False])[0]

    if pd_legal and not "Affects PD" in labels:
        issue.add_to_labels("Affects PD")
    elif not pd_legal and "Affects PD" in labels:
        issue.remove_from_labels("Affects PD")

    msg = issue.title
    #while msg.startswith('['):
    #    msg = msg[msg.find(']')+1:].strip()

    categories = [c for c in labels if c in CATEGORIES]
    if not categories:
        if "From Bug Blog" in labels:
            cat = "Unclassified"
        else:
            cat = "Unconfirmed"
            if re.match(DISCORD_REGEX, issue.body) and not issue.comments:
                print('Issue #{id} was reported {days} ago via Discord, and has had no followup.'.format(id=issue.number, days=age))
                if age > 1:
                    issue.create_comment('Closing due to lack of followup.')
                    issue.edit(state='closed')
                    return

        if not "Unclassified" in labels:
            issue.add_to_labels("Unclassified")
    elif "Unclassified" in labels:
        print('Removing Unclassified from Issue #{id}'.format(id=issue.number))
        issue.remove_from_labels("Unclassified")
        cat = categories.pop()
    else:
        cat = categories.pop()

    for card in cards:
        csv_line = card + '\t'
        csv_line += msg + '\t'
        csv_line += cat + '\t'
        csv_line += str(issue.updated_at)
        csv_line = remove_smartquotes(csv_line)
        ALL_CSV.append(csv_line)
        if cat in BADCATS:
            ALL_BANNED.append(card)
            if card in LEGAL_CARDS:
                PD_BANNED.append(card)
        bug = {
            'card': card,
            'description': msg,
            'category': cat,
            'last_updated': str(issue.updated_at),
            'pd_legal': card in LEGAL_CARDS,
            'bug_blog': "From Bug Blog" in labels,
            'breaking': cat in BADCATS,
            'url': issue.html_url,
            }
        ALL_BUGS.append(bug)

def fix_user_errors(issue):
    body = issue.body
    body = re.sub(BAD_AFFECTS_REGEX, 'Affects: [', body)
    if not re.match(AFFECTS_REGEX, body):
        cards = re.findall(r'\[?\[([^\]]*)\]\]?', issue.title)
        cards = [c for c in cards]
        body = body + '\nAffects: ' + ''.join(['[' + c + ']' for c in cards])
    issue.edit(body=body)

if __name__ == "__main__":
    main()
