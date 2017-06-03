import codecs
import re
import sys

import configuration
import requests

from github import Github

CATEGORIES = ["Advantageous", "Disadvantageous", "Game Breaking", "Graphical", "Non-Functional ability"]
BADCATS = ["Advantageous", "Game Breaking"]

LEGAL_CARDS = []


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
    csv = open('bugs.tsv', mode='w')
    csv.write("Card Name\tBug Description\tCategorization\tLast Confirmed\n")
    csv.close()

    csv = open('pd_bugs.tsv', mode='w')
    csv.write("Card Name\tBug Description\tCategorization\tLast Confirmed\n")
    csv.close()


    txt = open('bannable.txt', mode='w')
    txt.write('')
    txt.close()

    txt = open('pd_bannable.txt', mode='w')
    txt.write('')
    txt.close()

    for issue in issues:
        print(issue.title)
        if issue.state == "open":
            process_issue(issue)

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
    else:
        cat = categories.pop()

    csv = open('bugs.tsv', mode='a')
    pd_csv = open('pd_bugs.tsv', mode='a')
    #refactor this
    for card in cards:
        csv.write(card + '\t')
        csv.write(msg + '\t')
        csv.write(cat + '\t')
        csv.write(str(issue.updated_at) + '\n')
        if card in LEGAL_CARDS:
            pd_csv.write(card + '\t')
            pd_csv.write(msg + '\t')
            pd_csv.write(cat + '\t')
            pd_csv.write(str(issue.updated_at) + '\n')
        if cat in BADCATS:
            txt = open('bannable.txt', mode='a')
            txt.write(card + '\n')
            txt.close()
            if card in LEGAL_CARDS:
                txt = open('pd_bannable.txt', mode='a')
                txt.write(card + '\n')
                txt.close()

    csv.close()
    pd_csv.close()

if __name__ == "__main__":
    main()
