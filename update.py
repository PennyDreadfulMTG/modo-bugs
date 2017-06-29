import codecs
import re
import sys

import configuration
import requests

from github import Github

CATEGORIES = ["Advantageous", "Disadvantageous", "Game Breaking", "Graphical", "Non-Functional ability"]
BADCATS = ["Game Breaking"]

LEGAL_CARDS = []

ALL_CSV = []
PD_CSV = []
ALL_BANNED = []
PD_BANNED = []

if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def fetch_pd_legal():
    print('Fetching http://pdmtgo.com/legal_cards.txt')
    for card in requests.get('http://pdmtgo.com/legal_cards.txt').text.split('\n'):
        LEGAL_CARDS.append(card)


def main():
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

    csv = open('pd_bugs.tsv', mode='w')
    csv.write("Card Name\tBug Description\tCategorization\tLast Confirmed\n")
    PD_CSV.sort()
    for line in PD_CSV:
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

def process_issue(issue):
    labels = [c.name for c in issue.labels]
    cards = re.findall(r'\[?\[([^\]]*)\]\]?', issue.title)
    cards = [c for c in cards]

    pd_legal = ([True for c in cards if c in LEGAL_CARDS] or [False])[0]

    if pd_legal and not "Affects PD" in labels:
        issue.add_to_labels("Affects PD")
    elif not pd_legal and "Affects PD" in labels:
        issue.remove_from_labels("Affects PD")

    msg = issue.title
    while msg.startswith('['):
        msg = msg[msg.find(']')+1:].strip()

    categories = [c for c in labels if c in CATEGORIES]
    if not categories:
        if "From Bug Blog" in labels:
            cat = "Unclassified"
        else:
            cat = "Unconfirmed"
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
        ALL_CSV.append(csv_line)
        if card in LEGAL_CARDS:
            PD_CSV.append(csv_line)
        if cat in BADCATS:
            ALL_BANNED.append(card)
            if card in LEGAL_CARDS:
                PD_BANNED.append(card)

if __name__ == "__main__":
    main()
