import codecs
import re
import os
import sys

import configuration

from github import Github

CATEGORIES = ["Advantageous", "Disadvantageous", "Game Breaking", "Graphical Issue", "Non-Functional ability"]

if sys.stdout.encoding != 'utf-8':
  sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def main():
    if configuration.get("github_user") is None or configuration.get("github_password") is None:
        print('Invalid Config')
        exit(1)

    github = Github(configuration.get("github_user"), configuration.get("github_password"))
    repo = github.get_repo("PennyDreadfulMTG/modo-bugs")

    issues = repo.get_issues()
    # if os.path.exists('bugs.tsv'):
    #     os.remove('bugs.tsv')
    csv = open('bugs.tsv', mode='w')
    csv.write("Card Name\tBug Description\tCategorization\tLast Confirmed\n")
    csv.close()
    for issue in issues:
        print(issue.title)
        if issue.state == "open":
            process_issue(issue)

def process_issue(issue):
    cards = re.findall(r'\[?\[([^\]]*)\]\]?', issue.title)
    cards = [c for c in cards]

    msg = issue.title
    while msg.startswith('['):
        msg = msg[msg.find(']')+1:].strip()

    categories = [c.name for c in issue.labels if c.name in CATEGORIES]
    if not categories:
        cat = "Unconfirmed"
    else:
        cat = categories.pop()

    csv = open('bugs.tsv', mode='a')
    for card in cards:
        csv.write(card + '\t')
        csv.write(msg + '\t')
        csv.write(cat + '\t')
        csv.write(str(issue.updated_at) + '\n')
    csv.close()

if __name__ == "__main__":
    main()
