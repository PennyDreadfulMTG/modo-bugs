import codecs
import datetime
import json
import re
import sys
import urllib.parse
from typing import Dict, List

import requests
from github import Github
from github.Issue import Issue

import configuration
import fetcher
from helpers import (AFFECTS_REGEX, BAD_AFFECTS_REGEX, BADCATS, CATEGORIES,
                     DISCORD_REGEX, IMAGES_REGEX, REGEX_CARDREF,
                     remove_smartquotes, strip_squarebrackets)
import helpers

CARDNAMES: List[str] = fetcher.catalog_cardnames()

LEGAL_CARDS: List[str] = []

ALL_BUGS: List[Dict] = []

ALL_CSV: List[str] = []



if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer) # type: ignore

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
    pd = open('pd_bannable.txt', mode='w')
    for bug in ALL_BUGS:
        if bug['bannable']:
            txt.write(bug['card'] + '\n')
            if bug['pd_legal']:
                pd.write(bug['card'] + '\n')
    txt.close()
    pd.close()

    bugsjson = open('bugs.json', mode='w')
    json.dump(ALL_BUGS, bugsjson, indent=2)
    bugsjson.close()

def process_issue(issue: Issue) -> None:
    age = (datetime.datetime.now() - issue.updated_at).days
    if age < 5:
        fix_user_errors(issue)
    labels = [c.name for c in issue.labels]
    affects = re.search(AFFECTS_REGEX, issue.body, re.MULTILINE)
    if affects is None:
        affects = issue.title
    else:
        affects = affects.group(1)

    cards = re.findall(REGEX_CARDREF, affects)
    cards = [c for c in cards]

    fail = False
    for c in cards:
        if '//' in c:
            pass
        elif not c in CARDNAMES:
            fail = True
    if fail and not 'Invalid Card Name' in labels:
        issue.add_to_labels('Invalid Card Name')
    elif not fail and 'Invalid Card Name' in labels:
        issue.remove_from_labels('Invalid Card Name')

    expected = '<!-- Images --> '
    images = re.search(IMAGES_REGEX, issue.body, re.MULTILINE)
    for row in helpers.grouper(5, cards):
        expected = expected + '<img src="http://magic.bluebones.net/proxies/index2.php?c={0}" height="300px">'.format('|'.join([urllib.parse.quote(c) for c in row if c is not None]))
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
            if re.match(DISCORD_REGEX, issue.body, re.MULTILINE) and not issue.comments:
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
        bannable = cat in BADCATS and "Multiplayer" not in labels
        bug = {
            'card': card,
            'description': msg,
            'category': cat,
            'last_updated': str(issue.updated_at),
            'pd_legal': card in LEGAL_CARDS,
            'bug_blog': "From Bug Blog" in labels,
            'breaking': cat in BADCATS,
            'bannable': bannable,
            'url': issue.html_url,
            }
        if "Multiplayer" in labels:
            bug['multiplayer_only'] = True

        age = datetime.datetime.now() - issue.updated_at
        if "Help Wanted" in labels:
            bug['help_wanted'] = True
        elif age.days > 120:
            bug['help_wanted'] = True

        ALL_BUGS.append(bug)

def fix_user_errors(issue: Issue) -> None:
    body = issue.body
    # People sometimes put the affected cards on the following line. Account for that.
    body = re.sub(BAD_AFFECTS_REGEX, 'Affects: [', body)
    # People sometimes neglect Affects all-together, and only put cards in the title.
    affects = re.search(AFFECTS_REGEX, body, re.MULTILINE)
    if affects is None:
        cards = re.findall(REGEX_CARDREF, issue.title)
        cards = [c for c in cards]
        body = body + '\nAffects: ' + ''.join(['[' + c + ']' for c in cards])
    # We had a bug where the above triggered infinitely.  Clean it up.
    extra_affects = re.findall(AFFECTS_REGEX, body, re.MULTILINE)
    if len(extra_affects) > 1:
        lines = body.split('\n')
        if re.match(AFFECTS_REGEX, lines[-1]):
            body = '\n'.join(lines[:-1])
    # People are missing the bullet points, and putting info on the following line instead.
    body = re.sub(r' - \r?\n', '', body)
    # Push changes.
    if body != issue.body:
        issue.edit(body=body)
    # People are putting [cardnames] in square quotes, despite the fact we prefer Affects: now.
    title = strip_squarebrackets(issue.title)
    if title != issue.title:
        print("Changing title of #{0} to \"{1}\"".format(issue.number, title))
        issue.edit(title=title)

if __name__ == "__main__":
    main()
