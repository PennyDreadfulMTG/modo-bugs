from typing import Dict
from github.Issue import Issue
from github.IssueComment import IssueComment

from helpers import remove_smartquotes

ISSUE_CODES: Dict[int, str] = {}

def create_comment(issue: Issue, body: str) -> IssueComment:
    ISSUE_CODES[issue.number] = None
    return issue.create_comment(remove_smartquotes(body))
