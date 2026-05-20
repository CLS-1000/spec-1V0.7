#!/usr/bin/env python3
"""Write a minimal sgmllib.py stub to site-packages.

feedparser 6.x lists sgmllib3k as a dependency, but sgmllib3k 1.0.0
(released 2013) fails to build with modern pip/setuptools. This script
writes a minimal stub that satisfies feedparser's import requirements
so the package can be installed without building sgmllib3k.
"""
import os
import site
import sys

STUB = '''\
import re
from html.parser import HTMLParser

interesting = re.compile("[&<]")
incomplete = re.compile("&([a-zA-Z][a-zA-Z0-9]*|#[0-9]*)")
entityref = re.compile("&([a-zA-Z][-.a-zA-Z0-9]*)[^a-zA-Z0-9]")
charref = re.compile("&#([0-9]+)[^0-9]")
starttagopen = re.compile("<[>a-zA-Z]")
shorttagopen = re.compile("<[a-zA-Z][a-zA-Z0-9.-]*/")
shorttag = re.compile("<([a-zA-Z][a-zA-Z0-9.-]*)/([^/]*)//")
piclose = re.compile(">")
endbracket = re.compile("[<>]")


class SGMLParser(HTMLParser):
    def __init__(self, verbose=0):
        super().__init__(convert_charrefs=False)

    def handle_entityref(self, name):
        pass

    def handle_charref(self, name):
        pass

    def handle_starttag(self, tag, attrs):
        m = getattr(self, "start_" + tag, None) or getattr(self, "do_" + tag, None)
        if m:
            m(attrs)
        else:
            self.unknown_starttag(tag, attrs)

    def handle_endtag(self, tag):
        m = getattr(self, "end_" + tag, None)
        if m:
            m()
        else:
            self.unknown_endtag(tag)

    def unknown_starttag(self, tag, attrs):
        pass

    def unknown_endtag(self, tag):
        pass
'''

if hasattr(site, "getsitepackages"):
    paths = site.getsitepackages()
else:
    paths = [site.getusersitepackages()]

dest = os.path.join(paths[0], "sgmllib.py")
os.makedirs(paths[0], exist_ok=True)
with open(dest, "w") as f:
    f.write(STUB)
print(f"sgmllib stub written to {dest}", file=sys.stderr)
