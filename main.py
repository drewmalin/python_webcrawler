"""
    Web crawler!
"""
import urllib, re, random, argparse, sys, time, json

CORPUS = {}
START_URL = ""
MAX_DEPTH = 0
VERBOSE = False
CURRENT_PROGRESS = 0

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

    print "\n[LOG]\tCrawling [" + url + "]..."
    update_progress(0)
    html = urllib.urlopen(url).read()
    update_progress(.1)
    parse_links(html, url, current_depth)
    update_progress(1)

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
    links = get_html_links(html)
    for link in links:
        title, url = parse_link(link)
        url = validate_url(url, context_link)
        
        # This portion of the algorithm is considered to be 90% of the 
        # processing. This 90% is broken into two chunks, each of which updates
        # the progress bar by a fraction equal to 1/(the number of links to 
        # process). At this point, half half of that portion of the 90% chunk 
        # is complete.
        update_progress(CURRENT_PROGRESS + .9 * float(.5)/len(links))

        if url is None:
            continue

        if persist_link(title, url):
            if VERBOSE:
                print "[DEBUG]\t\tNew link found: (" + \
                    title + ") -> [" + url + "]"
            new_urls.append(url)
        else:
            if VERBOSE:
                print "[DEBUG]\t\tSkipping known or invalid link: (" \
                    + title + ") -> [" + url + "]"

        # The second half of the 90% chunk is now complete.
        update_progress(CURRENT_PROGRESS + .9 * float(.5)/len(links))

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
        html_link = re.sub('\s+', ' ', html_link).strip()
        if html_link:
            html_links.append(html_link)

    return html_links

def parse_link(link):
    """
        Accepts a single raw html link, returns the 'title' of that link and the url
        the link points to. If either one of these does not exist, None is returned in
        its place.
    """
    if VERBOSE:
        print "[DEBUG]\t\tParsing tag HTML: " + link
    
    # Grab the largest amount of text enclosed in an a tag, then strip the tag
    # away. If no title is found, return None.
    link_title_re = re.search('>.*</a>', link)
    link_title = link_title_re.group(0)[1:-4] if link_title_re else None
    # Grab the shortest amount of text after 'href='. Anchor tags *usually*
    # have quote-wrapped links, but this is not required. The following are
    # valid:
    # <a href="url"></a>
    # <a href='url'></a>
    # <a href=url></a>
    link_url_re = re.search('href=["\']?.*?["\'> ]', link)
    link_url = link_url_re.group(0)[5:-1] if link_url_re else None
    
    if link_url and link_url[0] in ("\'", "\""):
        link_url = link_url[1:]
    if link_url and link_url[-1] in (" ", ">", "\'", "\""):
        link_url = link_url[:-1]

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
    if url == START_URL or (title in CORPUS and CORPUS[title] == url):
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
        _ = urllib.urlopen(url)
    except:
        try:
            _ = urllib.urlopen(context_link+url)
        except:
            out_url = None
            if VERBOSE:
                print "[DEBUG]\t\tInvalid URL! (" + url + ")"
        else:
            out_url = context_link+url
            if VERBOSE:
                print "[DEBUG]\t\tFixing URL... " + \
                    "\n\t\t\tfrom: " + url + \
                    "\n\t\t\tto: " + out_url
    return out_url

def update_progress(new_progress):
    """
        Update the progress bar status to the specified position. If the specified
        position is greater than 1 (i.e., resulting in a progress greater than 100%)
        then the bar is set to 100%. The progress bar will not be printed if verbose
        mode is on (as the command line clutter looks very messy).
    """
    if VERBOSE:
        return
    global CURRENT_PROGRESS
    CURRENT_PROGRESS = new_progress if new_progress <= 1 else 1
    length = 20
    progress = '#' * int(CURRENT_PROGRESS * length)
    whitespace = ' ' * (length - len(progress))
    sys.stdout.write("\r[{0}] {1}%".format(progress + whitespace, \
                     int(CURRENT_PROGRESS * 100)))
    sys.stdout.flush()


def main():
    """ 
        Entry point into the crawler.
    """
    global VERBOSE
    global MAX_DEPTH
    global START_URL

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("-v", "--verbose", 
                            help="Enable verbose logging", action="store_true")
    arg_parser.add_argument("-d", "--depth",
                            help="Specify maximum search depth", type=int)
    arg_parser.add_argument("url",
                            help="URL on which to begin crawl", type=str)
    arg_parser.add_argument("-o", "--output",
                            help="File for final output", type=str)
    args = arg_parser.parse_args()

    VERBOSE = args.verbose
    MAX_DEPTH = args.depth
    START_URL = args.url
    
    print "[LOG] START"
    start_time = time.time()
    generate_corpus(START_URL)
    print "\nFound " + str(len(CORPUS)) + " unique links in " + \
        str(time.time() - start_time) + " seconds"
    if args.output:
        out_file = open(args.output, 'w')
        json.dump(CORPUS, out_file, sort_keys=True, indent=4, 
                  ensure_ascii=False)
        out_file.close()
        print "[LOG] Results written to " + args.output
    print "[LOG] SUCCESS"

if __name__ == "__main__":
    main()
