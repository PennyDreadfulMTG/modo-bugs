import re

from helpers import remove_smartquotes

from bs4 import BeautifulSoup, Comment
from github import Github
import requests

import configuration

CODE_REGEX = r'^Code: (.*)$'
BBT_REGEX = r'^Bug Blog Text: (.*)$'

ISSUE_CODES = {}

github = Github(configuration.get("github_user"), configuration.get("github_password"))
repo = github.get_repo("PennyDreadfulMTG/modo-bugs")

def scrape():
    print('Fetching http://magic.wizards.com/en/articles/archive/184956')
    soup = BeautifulSoup(requests.get('http://magic.wizards.com/en/articles/archive/184956').text, 'html.parser')
    articles = [parse_article_item_extended(a) for a in soup.find_all('div', class_='article-item-extended')]
    bug_blogs = [a for a in articles if str(a[0].string).startswith('Magic Online Bug Blog')]
    print('scraping {0} ({1})'.format(bug_blogs[0][0], bug_blogs[0][1]))
    update_redirect(bug_blogs[0][0].text, bug_blogs[0][1])
    scrape_bb(bug_blogs[0][1])

def update_redirect(title, redirect):
    text = "---\ntitle: {title}\nredirect_to:\n - {url}\n---\n".format(title=title, url=redirect)
    bb_jekyl = open('bug_blog.md', mode='w')
    bb_jekyl.write(text)
    bb_jekyl.close()

def parse_article_item_extended(a):
    title = a.find_all('h3')[0]
    link = 'http://magic.wizards.com' + a.find_all('a')[0]['href']
    return (title, link)

def scrape_bb(url):
    soup = BeautifulSoup(requests.get(url).text, 'html.parser')
    for b in soup.find_all('div', class_='collapsibleBlock'):
        parse_block(b)

def parse_block(collapsibleBlock):
    title = collapsibleBlock.find_all('h2')[0].get_text()
    print(title)
    handle_autocards(collapsibleBlock)
    if title == "Change Log":
        parse_changelog(collapsibleBlock)
    elif title == "Known Issues List":
        parse_knownbugs(collapsibleBlock)
    else:
        print("Unknown block: {0}".format(title))

def parse_changelog(collapsibleBlock):
    # They never show Fixed bugs in the Bug Blog anymore.  Fixed bugs are now listed on the Build Notes section of MTGO weekly announcements.
    # This is frustrating.
    for added in collapsibleBlock.find_all('ul'):
        for item in added.find_all('li'):
            print(item)
            try:
                code = str(item.find_all(string=lambda text: isinstance(text, Comment))[0]).replace('\t', ' ')
            except IndexError:
                print('No code!')
                code = None
            cards = get_cards_from_string(item.get_text())

            if not cards and not code:
                continue

            issue = find_issue_by_code(code)
            if issue is None:
                issue = find_issue(cards)
            if issue is not None:
                if code is None:
                    continue
                print(issue.body)
                reported = code in issue.body

                if not reported:
                    for comment in issue.get_comments():
                        print(comment.body)
                        if code in comment.body:
                            reported = True

                if not reported:
                    print("Adding report to existing issue.")
                    if code is not None:
                        create_comment(issue, 'Added to Bug Blog.\n{0}\nCode: {1}'.format(item.get_text(), code))
                    else:
                        create_comment(issue, 'Added to Bug Blog.\nBug Blog Text: {0}'.format(remove_smartquotes(item.get_text())))

                if not ("From Bug Blog" in [i.name for i in issue.labels]):
                    print("Adding Bug Blog to labels")
                    issue.add_to_labels("From Bug Blog")
            elif find_issue_by_code(code):
                print('Already closed.')
            elif find_issue_by_name(item.get_text()):
                print('Already exists.')
            else:
                print('Creating new issue')
                if code is not None:
                    text = "From Bug Blog.\nCode: {0}".format(code)
                else:
                    text = "From Bug Blog.\nBug Blog Text: {0}".format(remove_smartquotes(item.get_text()))
                repo.create_issue(remove_smartquotes(item.get_text()), body=remove_smartquotes(text), labels=["From Bug Blog"])

def get_cards_from_string(item):
    cards = re.findall(r'\[?\[([^\]]*)\]\]?', item)
    cards = [c for c in cards]
    return cards

def parse_knownbugs(b):
    # attempt to find all the fixed bugs
    all_codes = b.find_all(string=lambda text: isinstance(text, Comment))
    all_codes = [str(code).replace('\t', ' ') for code in all_codes]
    for issue in repo.get_issues():
        code = re.search(CODE_REGEX, issue.body, re.MULTILINE)
        if code is None:
            for comment in issue.get_comments():
                code = re.search(CODE_REGEX, comment.body, re.MULTILINE)
                if code is not None:
                    break
            else:
                cards = get_cards_from_string(issue.title)
                if "From Bug Blog" in [i.name for i in issue.labels]:
                    print("Issue #{id} {cards} has no Bug Blog code!".format(id=issue.number, cards=cards))
                    # TODO: Scan bugblog for issue title.
                    continue
                if not cards:
                    continue
                lines = b.find_all(string=re.compile(r'\[' + cards[0] + '\]'))
                if not lines:
                    continue
                for line in lines:
                    parent = line.parent
                    try:
                        code = str(parent.find_all(string=lambda text: isinstance(text, Comment))[0]).replace('\t', ' ')
                    except IndexError:
                        code = parent.get_text()
                    print(code)
                    if find_issue_by_code(code) is not None:
                        print("Already assigned.")
                        continue
                    text = ''.join(parent.strings)
                    print(text)
                    create_comment(issue, 'Found in bug blog.\n{0}\nCode: {1}'.format(text, code))
                    if not ("From Bug Blog" in [i.name for i in issue.labels]):
                        issue.add_to_labels("From Bug Blog")
                continue

        code = code.group(1).strip()
        # print(repr(code))
        if code in all_codes:
            # print('{id} is still bugged'.format(id=issue.number))
            pass
        else:
            print('{id} is fixed!'.format(id=issue.number))
            create_comment(issue, 'This bug has been removed from the bug blog!')
            issue.edit(state='closed')

def create_comment(issue, body):
    ISSUE_CODES[issue.id] = None
    return issue.create_comment(remove_smartquotes(body))

def handle_autocards(soup):
    for link in soup.find_all('a', class_='autocard-link'):
        name = link.get_text()
        link.replace_with('[{0}]'.format(name))

def find_issue_by_code(code):
    if code is None:
        return None
    all_issues = repo.get_issues(state="all")
    for issue in all_issues:
        if issue.id in ISSUE_CODES.keys():
            if ISSUE_CODES[issue.id] == code:
                return issue
            continue
        found = code in issue.body
        icode = re.search(CODE_REGEX, issue.body, re.MULTILINE)
        if icode is None:
            icode = re.search(BBT_REGEX, issue.body, re.MULTILINE)
        if not found:
            for comment in issue.get_comments():
                if code in comment.body:
                    found = True
                if icode is None:
                    icode = re.search(CODE_REGEX, comment.body, re.MULTILINE)
                if icode is None:
                    icode = re.search(BBT_REGEX, issue.body, re.MULTILINE)

        if icode is not None:
            ISSUE_CODES[issue.id] = icode.groups()[0].strip()
        else:
            ISSUE_CODES[issue.id] = None
        if found:
            ISSUE_CODES[issue.id] = code
            return issue

def find_issue_by_name(name):
    if name is None: #What?
        return None
    all_issues = repo.get_issues(state="all")
    for issue in all_issues:
        if issue.title == name:
            return issue

def find_issue(cards):
    all_issues = repo.get_issues()
    relevant_issues = []
    for card in cards:
        for issue in all_issues:
            if issue.id in ISSUE_CODES.keys() and ISSUE_CODES[issue.id] is not None:
                continue
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
