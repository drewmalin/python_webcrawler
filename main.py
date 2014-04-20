"""
    Web crawler!
"""
import urllib
import re
import random

CORPUS = {}
START_LINK = "http://www.drewmalin.com/"
MAX_DEPTH = 1

def generate_corpus(url, current_depth=0):
    """
        Starting point for link generation. If the incoming depth is -1, ignore any
        depth checks, otherwise halt if the current dept exceeds the max_depth.

        url - The URL to base the current search on
        current_depth - The depth in the tree of HTML pages we are currently at
    """
    if MAX_DEPTH != -1:
        if current_depth > MAX_DEPTH:
            return
        else:
            current_depth = current_depth + 1

    url = validate_url(url, '')
    if url is None:
        return

    print "[LOG]\tCrawling [" + url + "]..."
    html = urllib.urlopen(url).read()
    parse_links(html, url, current_depth)

def parse_links(html, context_link, depth):
    """
        For the incoming html, parse all links, saving them to the global corpus. All
        links found will be recursed upon (if they are valid and new to the corpus) in
        a breadth-first fashion.

        html - Context HTML page to search
        context_link - URL of the context page-- used to reconstruct relative links
        depth - Current depth from the beginning of execution
    """
    new_urls = []

    for link in get_html_links(html):
        title, url = parse_link(link)
        
        url = validate_url(url, context_link)
        if url is None:
            continue

        if persist_link(title, url):
            print "[LOG]\t\tNew link found: (" + title + ") -> [" + url + "]"
            new_urls.append(url)
        else:
            print "[DEBUG]\t\tSkipping known or invalid link: (" \
                + title + ") -> [" + url + "]"

    # Recurse on the newly found links (breadth-first)
    for url in new_urls:
        generate_corpus(url, depth)

def get_html_links(html):
    """
        Return a list of raw html strings corresponding to the <a> tags in the incoming 
        HTML. The html links will be cleaned such that newlines are removed and blocks
        of whitespace are reduced to a single space character.

        html - Raw HTML string on which to search
    """
    html_links = []
    link_locations = zip([l.start() for l in re.finditer('<a ', html)],
                         [l.end() for l in re.finditer('</a>', html)])

    for location in link_locations:
        html_link = html[location[0]:location[1]]
        html_link = re.sub('\s+', ' ', html_link)
        html_links.append(html_link)

    return html_links

def parse_link(link):
    """
        Accepts a single raw html link, returns the 'title' of that link and the url
        the link points to. If either one of these does not exist, None is returned in
        its place.
    """
    # Grab the largest amount of text enclosed in an a tag,
    # then strip the tag away.
    link_title = re.search('>.*</a>', link).group(0)[1:-4]
    # Grab the shortest amount of text enclosed in quotes after the href.
    link_url = re.search('href=["\'].*?["\']', link).group(0)[6:-1]

    return link_title, link_url

# return true if we should search the url, false if we should not
def persist_link(title, url):
    """
        Persist the title/url pair to the global corpus, if the combination has not
        yet been inspected. If the incoming url has been seen before, but under a 
        different title, a new key for that url is created. If the title has been
        found, but for a different url, the title is appended to a nonce value and
        saved.
    """
    # No link text provided? Don't save this url.
    if not title:
        return False
    # We've already seen this exact link? No need to save again.
    if title in CORPUS and CORPUS[title] == url:
        return False
    for key, value in CORPUS.iteritems():
        # We've already seen this url, but under a different key
        if value == url:
            CORPUS[title] = url
            return False
        # We haven't seen this url, but we have seen this key
        elif key == title:
            CORPUS[make_unique(title)] = url
            return True
    # We haven't seen the url or key
    CORPUS[title] = url
    return True

def make_unique(key_str):
    """
        Append a nonce value to the incoming string. Return the first string found
        that does not appear in the global corpus."
    """
    while key_str in [k for k in CORPUS.keys()]:
        key_str = key_str + str(random.random())
    return key_str

def validate_url(url, context_link):
    """
        Validate the incoming url. If the incoming url contains a '#', strip the part
        of the string that follows this character. If the url is the root ('/'), set
        the url to be the fully-qualified context string. Finally, if the incoming
        url is not a valid url, append it to the fully-qualified context string. If
        this final attempt at creating a valid string does not work, return None.
    """
    if not url or len(url) == 0:
        return None
    if url == '/':
        url = context_link
    if url[-1] == "/":
        url = url[:-1]
    if "#" in url:
        url = url[:url.find("#")]
    out_url = url
    try:
        response = urllib.urlopen(url)
    except:
        try:
            response = urllib.urlopen(context_link+url)
        except:
            out_url = None
            print "[DEBUG]\t\tInvalid URL! (" + url + ")"
        else:
            out_url = context_link+url
            print "[DEBUG]\t\tFixing URL... " + \
                  "\n\t\t\tfrom: " + url + \
                  "\n\t\t\tto: " + out_url
    return out_url

print "[INFO] START"
generate_corpus(START_LINK)
print "Found " + str(len(CORPUS)) + " unique links"
print "{"
for entry in CORPUS:
    print "\t(" + entry + ")\n\t\t-> [" + CORPUS[entry] + "]"
print "}"
print "[INFO] SUCCESS"
