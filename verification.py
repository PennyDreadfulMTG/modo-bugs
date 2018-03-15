import requests
from github import Github
from lxml import etree

import configuration

manifest = requests.get('http://mtgoclientdepot.onlinegaming.wizards.com/MTGO.application')
tree = etree.fromstring(manifest.content)
identity = tree.find('{urn:schemas-microsoft-com:asm.v1}assemblyIdentity')
version = identity.attrib['version']

print("Current MTGO Version is {0}".format(version))

github = Github(configuration.get("github_user"), configuration.get("github_password"))
repo = github.get_repo("PennyDreadfulMTG/modo-bugs")
