import re, sys
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup, Comment
from bs4.element import Tag
from github import Github
from github.Issue import Issue

import configuration
from helpers import BBT_REGEX, CODE_REGEX, remove_smartquotes, strip_squarebrackets

ISSUE_CODES = {}

github = Github(configuration.get("github_user"), configuration.get("github_password"))
repo = github.get_repo("PennyDreadfulMTG/modo-bugs")

def scrape() -> None:
    print('Fetching http://magic.wizards.com/en/articles/archive/184956')
    soup = BeautifulSoup(requests.get('http://magic.wizards.com/en/articles/archive/184956').text, 'html.parser')
    articles = [parse_article_item_extended(a) for a in soup.find_all('div', class_='article-item-extended')]
    bug_blogs = [a for a in articles if str(a[0].string).startswith('Magic Online Bug Blog')]
    print('scraping {0} ({1})'.format(bug_blogs[0][0], bug_blogs[0][1]))
    update_redirect(bug_blogs[0][0].text, bug_blogs[0][1])
    scrape_bb(bug_blogs[0][1])

def update_redirect(title: str, redirect: str) -> None:
    text = "---\ntitle: {title}\nredirect_to:\n - {url}\n---\n".format(title=title, url=redirect)
    bb_jekyl = open('bug_blog.md', mode='r')
    orig = bb_jekyl.read()
    bb_jekyl.close()
    if orig != text:
        print('New bug blog update!')
        sys.argv.append('check-missing') # This might be a bad idea
        bb_jekyl = open('bug_blog.md', mode='w')
        bb_jekyl.write(text)
        bb_jekyl.close()

def parse_article_item_extended(a: Tag) -> Tuple[Tag, str]:
    title = a.find_all('h3')[0]
    link = 'http://magic.wizards.com' + a.find_all('a')[0]['href']
    return (title, link)

def scrape_bb(url: str) -> None:
    soup = BeautifulSoup(requests.get(url).text, 'html.parser')
    for b in soup.find_all('div', class_='collapsibleBlock'):
        parse_block(b)

def parse_block(collapsibleBlock: Tag) -> None:
    title = collapsibleBlock.find_all('h2')[0].get_text()
    print(title)
    handle_autocards(collapsibleBlock)
    if title == "Change Log":
        parse_changelog(collapsibleBlock)
    elif title == "Known Issues List":
        parse_knownbugs(collapsibleBlock)
    else:
        print("Unknown block: {0}".format(title))

def parse_changelog(collapsibleBlock: Tag) -> None:
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
                        create_comment(issue, 'Added to Bug Blog.\nBug Blog Text: {0}\nCode: {1}'.format(item.get_text(), code))
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
                text = "From Bug Blog.\nAffects: \n<!-- Images -->\nBug Blog Text: {0}".format(remove_smartquotes(item.get_text()))
                if code is not None:
                    text += "\nCode: {0}".format(code)
                repo.create_issue(remove_smartquotes(item.get_text()), body=remove_smartquotes(text), labels=["From Bug Blog"])

def get_cards_from_string(item: str) -> List[str]:
    cards = re.findall(r'\[?\[([^\]]*)\]\]?', item)
    cards = [c for c in cards]
    return cards

def parse_knownbugs(b: Tag) -> None:
    # attempt to find all the fixed bugs
    all_codes = b.find_all(string=lambda text: isinstance(text, Comment))
    all_codes = [str(code).replace('\t', ' ') for code in all_codes]
    for issue in repo.get_issues():
        # code = re.search(CODE_REGEX, issue.body, re.MULTILINE)
        bbt = re.search(BBT_REGEX, issue.body, re.MULTILINE)
        if bbt is None:
            cards = get_cards_from_string(issue.title)
            if "From Bug Blog" in [i.name for i in issue.labels]:
                find_bbt_in_body_or_comments(issue)
                find_bbt_in_issue_title(issue, b)
                bbt = re.search(BBT_REGEX, issue.body, re.MULTILINE)
                if bbt is None:
                    print("Issue #{id} {cards} has no Bug Blog text!".format(id=issue.number, cards=cards))
                    issue.add_to_labels("Invalid Bug Blog")
                continue

            if not cards:
                continue
            lines = b.find_all(string=re.compile(r'\[' + cards[0] + r'\]'))
            if not lines:
                continue
            for line in lines:
                parent = line.parent
                try:
                    bb_code = str(parent.find_all(string=lambda text: isinstance(text, Comment))[0]).replace('\t', ' ')
                except IndexError:
                    bb_code = None
                bb_text = parent.get_text().strip()
                print(bb_code)
                if find_issue_by_code(bb_code) is not None:
                    print("Already assigned.")
                    continue
                if find_issue_by_code(bb_text) is not None:
                    print("Already assigned.")
                    continue
                text = ''.join(parent.strings)
                print(text)
                if bb_code is not None:
                    create_comment(issue, 'Found in bug blog.\n{0}\nCode: {1}'.format(text, bb_code))
                else:
                    create_comment(issue, 'Found in bug blog.\nBug Blog Text: {0}'.format(text))
                if not ("From Bug Blog" in [i.name for i in issue.labels]):
                    issue.add_to_labels("From Bug Blog")
            continue
        else:
            if "Invalid Bug Blog" in [i.name for i in issue.labels]:
                issue.remove_from_labels('Invalid Bug Blog')

        if "From Bug Blog" in [i.name for i in issue.labels]:
            # Don't check for Bug Blog Text if it's not marked as a BB issue (Maybe because it was reopened)
            if bbt is not None:
                text = remove_smartquotes(bbt.group(1).strip())
                for row in b.find_all('tr'):
                    data = row.find_all("td")
                    rowtext = remove_smartquotes(data[1].text.strip())
                    if rowtext == text:
                        break
                    elif strip_squarebrackets(rowtext) == strip_squarebrackets(text):
                        # Fix this
                        print("Issue #{id}'s bug blog text has differing autocard notation.".format(id=issue.number))
                        body = re.sub(BBT_REGEX, 'Bug Blog Text: {0}'.format(rowtext), issue.body, flags=re.MULTILINE)
                        if issue.body != body:
                            issue.edit(body=body)
                            print('Updated to `{0}`'.format(rowtext))
                        break
                else:
                    print('{id} is fixed!'.format(id=issue.number))
                    create_comment(issue, 'This bug has been removed from the bug blog!')
                    issue.edit(state='closed')

    if 'check-missing' in sys.argv:
        # This is very expensive.
        for row in b.find_all('tr'):
            data = row.find_all("td")
            row_text = data[1].text.strip()
            if row_text == "Description":
                # BS4 is bad.
                continue
            if find_issue_by_code(row_text):
                continue
            print("Could not find issue for `{row}`".format(row=row_text))
            text = "From Bug Blog.\nBug Blog Text: {0}".format(row_text)
            repo.create_issue(remove_smartquotes(row_text), body=remove_smartquotes(text), labels=["From Bug Blog"])


def find_bbt_in_issue_title(issue, known_issues):
    title = strip_squarebrackets(issue.title).replace(' ', '')
    for row in known_issues.find_all('tr'):
        data = row.find_all("td")
        row_text = strip_squarebrackets(data[1].text.strip()).replace(' ', '')
        if row_text == title:
            body = issue.body
            body += "\nBug Blog Text: {0}".format(data[1].text.strip())
            if body != issue.body:
                issue.edit(body=body)
            return

def create_comment(issue, body):
    ISSUE_CODES[issue.number] = None
    return issue.create_comment(remove_smartquotes(body))

def handle_autocards(soup: Tag) -> None:
    for link in soup.find_all('a', class_='autocard-link'):
        name = link.get_text()
        link.replace_with('[{0}]'.format(name))

def find_issue_by_code(code: str) -> Issue:
    if code is None:
        return None
    def scan(issue_list):
        for issue in issue_list:
            if not "From Bug Blog" in [i.name for i in issue.labels]:
                # Only bug blog issues have bug blog data
                ISSUE_CODES[issue.number] = None
                continue
            icode = ISSUE_CODES.get(issue.number, None)
            if icode == code:
                return issue
            elif icode is not None:
                continue
            found = code in issue.body
            if not found:
                icode = find_bbt_in_body_or_comments(issue)
                found = code in issue.body
            if icode is not None:
                ISSUE_CODES[issue.number] = icode.groups()[0].strip()
            else:
                ISSUE_CODES[issue.number] = None
            if found:
                ISSUE_CODES[issue.number] = code
                return issue
        return None
    res = scan(repo.get_issues(state="open"))
    if res:
        return res
    return scan(repo.get_issues(state="closed"))

def find_bbt_in_body_or_comments(issue):
    body = issue.body
    icode = re.search(BBT_REGEX, issue.body, re.MULTILINE)
    if not icode:
        for comment in issue.get_comments():
            if icode is None:
                icode = re.search(BBT_REGEX, comment.body, re.MULTILINE)
                if icode is not None:
                    body += '\nBug Blog Text: {0}'.format(icode.groups()[0].strip())
    if body != issue.body:
        issue.edit(body=body)
    return icode

def find_issue_by_name(name: str) -> Issue:
    if name is None: #What?
        return None
    all_issues = repo.get_issues(state="all")
    for issue in all_issues:
        if issue.title == name:
            return issue

def find_issue(cards: List[str]) -> Optional[Issue]:
    all_issues = repo.get_issues()
    relevant_issues: List[Issue] = []
    for card in cards:
        for issue in all_issues:
            if ISSUE_CODES.get(issue.number, None) is not None:
                continue
            if '[{0}]'.format(card) in issue.title and not issue in relevant_issues:
                relevant_issues.append(issue)

    print(relevant_issues)
    if len(relevant_issues) > 1:
        # Do something smart.
        print("Error: Too many issues")
        return None
    elif len(relevant_issues) == 1:
        return relevant_issues[0]
    else:
        print("No issue for this card.")
        return None

if __name__ == "__main__":
    scrape()
