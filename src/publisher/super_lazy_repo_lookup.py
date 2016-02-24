import os, requests
import models
from django.conf import settings
import logging
from publisher import utils

logger = logging.getLogger(__name__)

"""I got carried away writing code this morning.
Completely untested, but the general shapes allows for multiple different repositories
with each repository having different targets. You could have different github
repositories for example, or several websites or ... whatever.

- Luke
"""

#
# lazily fetch article
#


def github_url(doi, data):
    # looks like:
    # https://raw.githubusercontent.com/elifesciences/elife-article-json/master/article-json/elife00003.xml.json
    return "https://raw.githubusercontent.com/%(author)s/%(repo)s/%(branch)s/%(path)s/%(filename)s" % data


# there may be multiple repositories we should investigate to find an article's EIF
REPO_LOOKUP = [
    ("github", {"author": "elifesciences",
               "repo": "elife-article-json",
               "branch": "master",
               "path": "/article-json/",
               "filename": lambda doi: "elife%s.xml.json" % doi.split('/')[1].replace('.', '')}),
]

# ties a repository to something that understands the data 
REPO_URL_RESOLVERS = {
    "github": github_url,
}

def article_eif_urls(doi):
    if not REPO_LOOKUP:
        logger.warning("no repositories have been configured. we don't know where to pull the article EIF json from!")
        return

    def _call_val(val, **kwargs):
        return val(**kwargs) if callable(val) else val
    
    for repo_name, repo_data in REPO_LOOKUP:
        if not repo_name in REPO_URL_RESOLVERS:
            logger.error("I have repository data but no way to construct a url for a %r!" % repo_name)
            continue
        # if any of the map's values are functions, call them with the doi
        repo_data = utils.dictmap(_call_val, repo_data, doi=doi)
        yield REPO_URL_RESOLVERS[repo_name](doi, repo_data)
    logger.warning("failed to find article data in any of the given repositories")
    return

def _fetch_article_eif(url):
    "downloads article eif json from a url provided by the repository"
    try:
        logger.info("fetching url %r", url)
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 404:
            logging.warning("given url %r returned a 404", url)
    except ValueError:
        logging.warning("could not decode response body from json, url: %r", url)            
    except:
        logging.exception("unhandled exception attempting to fetch url %r", url)
    
    return None

def fetch_article_eif(doi):
    "returns the first not-None result of "
    return next(_fetch_article_eif(url) for url in article_eif_urls(doi))
