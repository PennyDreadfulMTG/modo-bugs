import re

from bs4 import BeautifulSoup, Comment
from github import Github
import requests

import configuration

LEGAL_CARDS = []

github = Github(configuration.get("github_user"), configuration.get("github_password"))
repo = github.get_repo("PennyDreadfulMTG/modo-bugs")

def scrape():
    print('Fetching http://pdmtgo.com/legal_cards.txt')
    for card in requests.get('http://pdmtgo.com/legal_cards.txt').text.split('\n'):
        LEGAL_CARDS.append(card)
    print('Fetching http://magic.wizards.com/en/articles/archive/184956')
    soup = BeautifulSoup(requests.get('http://magic.wizards.com/en/articles/archive/184956').text, 'html.parser')
    articles = [parse_article_item_extended(a) for a in soup.find_all('div', class_='article-item-extended')]
    bug_blogs = [a for a in articles if str(a[0].string).startswith('Magic Online Bug Blog')]
    print('scraping {0}'.format(bug_blogs[0][0]))
    scrape_bb(bug_blogs[0][1])

def parse_article_item_extended(a):
    title = a.find_all('h3')[0]
    link = 'http://magic.wizards.com' + a.find_all('a')[0]['href']
    return (title, link)

def scrape_bb(url):
    soup = BeautifulSoup(requests.get(url).text, 'html.parser')
    for b in soup.find_all('div', class_='collapsibleBlock'):
        parse_block(b)

def parse_block(b):
    title = b.find_all('h2')[0].get_text()
    print(title)
    handle_autocards(b)
    if title == "Change Log":
        parse_changelog(b)
    elif title == "Known Issues List":
        pass
    else:
        print("Unknown block: {0}".format(title))

def parse_changelog(b):
    # They never show Fixed bugs in the Bug Blog anymore.  Fixed bugs are now listed on the Build Notes section of MTGO weekly announcements.
    # This is frustrating.
    added = b.find_all('ul')[0]
    for item in added.find_all('li'):
        print(item)
        code = item.find_all(string=lambda text: isinstance(text, Comment))[0]
        cards = re.findall(r'\[?\[([^\]]*)\]\]?', item.get_text())
        cards = [c for c in cards]

        relevant = ([True for c in cards if c in LEGAL_CARDS] or [False])[0]
        if not relevant:
            continue # Temporary measure.

        issue = find_issue(cards)
        if issue is not None:
            print(issue.body)
            reported = code in issue.body

            if not reported:
                for comment in issue.get_comments():
                    print(comment.body)
                    if code in comment.body:
                        reported = True

            if not reported:
                print("Adding report to existing issue.")
                issue.create_comment('From Bug Blog:\n{0}\nCode: {1}'.format(item.get_text(), code))

            if not ("From Bug Blog" in [i.name for i in issue.labels]):
                print("Adding Bug Blog to labels")
                issue.add_to_labels("From Bug Blog")
        else:
            print('Creating new issue')
            repo.create_issue(item.get_text(), body="From Bug Blog:\nCode: {0}".format(code), labels=["From Bug Blog"])

def handle_autocards(soup):
    for link in soup.find_all('a', class_='autocard-link'):
        name = link.get_text()
        link.replace_with('[{0}]'.format(name))

def find_issue(cards):
    all_issues = repo.get_issues()
    relevant_issues = []
    for card in cards:
        for issue in all_issues:
            if '[{0}]'.format(card) in issue.title and not issue in relevant_issues:
                relevant_issues.append(issue)

    print(relevant_issues)
    if len(relevant_issues) > 1:
        # Do something smart.
        print("Error: Too many issues")
        return relevant_issues[0]
    elif len(relevant_issues) == 1:
        return relevant_issues[0]
    else:
        print("No issue for this card.")
        return None

scrape()