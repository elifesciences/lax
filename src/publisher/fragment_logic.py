from collections import OrderedDict
from functools import partial
from jsonschema import ValidationError
from django.db.models import Q
from django.conf import settings
from . import utils, models, aws_events, codes
from .utils import create_or_update, ensure, subdict, StateError, atomic, lmap, lfilter
import logging
from django.db import transaction

LOG = logging.getLogger(__name__)

def _getids(x):
    if utils.isint(x):
        # id is a msid
        return {'article': models.Article.objects.get(manuscript_id=x)}
    elif isinstance(x, models.Article):
        return {'article': x}
    elif isinstance(x, models.ArticleVersion):
        return {'article': x.article, 'version': x.version}
    else:
        raise TypeError("failed to add article fragment, unhandled type %r" % type(x))

def add(x, ftype, fragment, pos=1, update=False):
    "adds given fragment to database. if fragment at this article+type+version exists, it will be overwritten"
    ensure(isinstance(fragment, dict), "all fragments must be a dictionary")
    data = {
        'version': None,
        'type': ftype,
        'fragment': fragment,
        'position': pos
    }
    data.update(_getids(x))
    key = ['article', 'type', 'version']
    frag, created, updated = create_or_update(models.ArticleFragment, data, key, update=update)
    return frag, created, updated

def rm(msid, ftype):
    fragment = models.ArticleFragment.objects.get(article__manuscript_id=msid, type=ftype)
    fragment.delete()

def get(x, ftype):
    kwargs = {
        'type': ftype
    }
    kwargs.update(_getids(x))
    return models.ArticleFragment.objects.get(**kwargs)

def merge(av):
    """returns the merged result for a particlar article version"""
    # all fragments belonging to this specific article version or
    # to this article in general
    fragments = models.ArticleFragment.objects \
        .filter(article=av.article) \
        .filter(Q(version=av.version) | Q(version=None))
    if not fragments:
        raise StateError(codes.NO_RECORD, "%r has no fragments that can be merged" % av)
    return utils.merge_all([f.fragment for f in fragments])

def valid(merge_result, quiet=True):
    "returns True if the merged result is valid article-json"
    msid = merge_result.get('id', '[no id]')
    version = merge_result.get('version', '[no version]')
    log_context = {
        'msid': msid,
        'version': version,
    }
    try:
        schema_key = merge_result['status'] # poa or vor
        schema = settings.SCHEMA_IDX[schema_key]
        return utils.validate(merge_result, schema)

    except KeyError:
        msg = "merging %s returned a data structure that couldn't be used to determine validation"
        LOG.exception(msg, msid, extra=log_context)
        # legitimate error that needs to break things
        raise

    except ValueError as err:
        # either the schema is bad or the struct is bad
        LOG.exception("validating %s v%s failed to load schema file %s", msid, version, schema, extra=log_context)
        # this is a legitimate error and needs to break things
        raise

    except ValidationError as err:
        # definitely not valid ;)
        LOG.info("while validating %s v%s with %s, failed to validate with error: %s", msid, version, schema, err.message)
        if not quiet:
            raise

def extract_snippet(merged_result):
    if not merged_result:
        return None
    # TODO: derive these from the schema automatically somehow please
    snippet_keys = [
        # https://github.com/elifesciences/api-raml/blob/develop/src/snippets/article-vor.v1.yaml
        # https://github.com/elifesciences/api-raml/blob/develop/src/snippets/article.v1.yaml

        # pulled from given xml->json
        'copyright', 'doi', 'elocationId', 'id', 'impactStatement',
        'pdf', 'published', 'researchOrganisms', 'status', 'subjects',
        'title', 'titlePrefix', 'type', 'version', 'volume', 'authorLine',
        'abstract', 'figuresPdf', 'image',

        # added by lax
        'statusDate', 'stage', 'versionDate',
    ]
    return subdict(merged_result, snippet_keys)

def pre_process(av, result):
    "supplements the merged fragments with more article data required for validating"
    # 'published' is when the v1 article was published
    # if unpublished, this value will be None
    if av.version == 1:
        result['published'] = av.datetime_published
    else:
        result['published'] = av.article.datetime_published

    result['versionDate'] = av.datetime_published

    # 'statusDate' is when the 'status' (poa/vor) value changed to the status being
    # served up in *this* result.
    if av.version == 1 or av.status == models.POA:
        # we're a POA or a version 1, statusDate is easy :)
        result['statusDate'] = result['published']
    else:
        # we're a non-v1 VOR, statusDate is a little harder
        # we can't tell which previous version was a vor so consult our version history
        earliest_vor = av.article.earliest_vor()
        if earliest_vor:
            # article has a vor in it's version history! use it's version date
            result['statusDate'] = earliest_vor.datetime_published # may be None
        else:
            # no VORs found AT ALL
            # this means our av == earliest_vor and it *hasn't been saved yet*
            result['statusDate'] = av.datetime_published # may be/probably None

    if av.datetime_published:
        result['stage'] = 'published'
    else:
        # unpublished! tweak the results
        # https://github.com/elifesciences/api-raml/blob/develop/src/snippets/article.v1.yaml
        result['stage'] = 'preview'
        del result['versionDate']
        del result['statusDate']
        if av.version == 1:
            del result['published']

    # these keys are not part of the article-json spec and shouldn't be made public
    delete_these = [
        '-related-articles-internal',
        '-related-articles-external',
        '-meta',
        '-history',
    ]
    utils.delall(result, delete_these)

    return result

def merge_and_preprocess(av):
    "merges fragments AND pre-processes them for saving"
    return pre_process(av, merge(av))

def merge_if_valid(av, quiet=True):
    """merges, pre-processes and validates the fragments of the given ArticleVersion instance.
    if the result is valid, returns the merge result.
    if invalid, returns nothing.
    if invalid and quiet=False, a ValidationError will be raised"""
    return valid(merge_and_preprocess(av), quiet=quiet)

def set_article_json(av, quiet):
    """updates the article with the result of the merge operation.
    if the result of the merge was valid, the merged result will be saved.
    if invalid, the ArticleVersion instance's article-json will be unset.
    if invalid and quiet=False, a ValidationError will be raised"""
    log_context = {'article-version': av, 'quiet': quiet}
    result = merge_if_valid(av, quiet)
    av.article_json_v1 = result
    av.article_json_v1_snippet = extract_snippet(result)
    av.save()
    if not result:
        msg = "this article failed to merge it's fragments into a valid result. Any article-json previously set for this version of the article has been removed. This article cannot be published in it's current state."
        LOG.warn(msg, extra=log_context)
    return result

def set_all_article_json(art, quiet):
    "like `set_article_json`, but for every version of an article"
    return lmap(partial(set_article_json, quiet=quiet), art.articleversion_set.all())

#
# higher level logic
#

def add_fragment_update_article(art, key, fragment):
    "adds a fragment to an article, re-renders article, sends update event. if an error occurs, update is rolled back and no event is sent"
    with transaction.atomic():
        # pos=1 ensures we don't ever replace the XML2JSON fragment
        frag, created, updated = add(art, key, fragment, pos=1, update=True)
        ensure(created or updated, "fragment was not created/updated")

        # notify event bus that article change has occurred
        transaction.on_commit(partial(aws_events.notify, art.manuscript_id))

        return set_all_article_json(art, quiet=False)

def delete_fragment_update_article(art, key):
    "removes a fragment from an article, re-renders article, sends update event. if an error occurs, delete is rolled back and no event is sent"
    with transaction.atomic():
        # version=None ensures we don't ever remove the XML2JSON fragment
        models.ArticleFragment.objects.get(article=art, type=key, version=None).delete()

        # notify event bus that article change has occurred
        transaction.on_commit(partial(aws_events.notify, art.manuscript_id))

        return set_all_article_json(art, quiet=False)

#
#
#

def location(av):
    "returns the location of the article xml stored in the primary fragment"
    try:
        obj = get(av, models.XML2JSON)
        return obj.fragment['-meta']['location']
    except models.ArticleFragment.DoesNotExist:
        return 'no-article-fragment'
    except KeyError as err:
        return 'no-location-stored'


#
# revalidate logic
#

# NOTE: revalidation turned out to be a bit of a dead end with
# the easiest solution being a blanket backfill. this is some
# nice code, and it's possibly useful, but I would tear it out
# if it's left unused for much longer - lsh, 2017-07-17

SET, RESET, UNSET, NOTSET = 'set', 'reset', 'unset', 'not-set'

def revalidate(av):
    try:
        had_json = not not av.article_json_v1
        result = set_article_json(av, quiet=True)
        matrix = {
            # had_json?, result?
            (True, True): RESET,
            (True, False): UNSET,

            (False, True): SET,
            (False, False): NOTSET,
        }
        return matrix[utils.boolkey(had_json, result)]
    except StateError:
        return NOTSET

def revalidate_many(avl):
    def do(av):
        return {
            'msid': av.article.manuscript_id,
            'version': av.version,
            'result': revalidate(av),
        }
    return lmap(do, avl)

#

def revalidate_report(results):
    def instate(state):
        def wrapper(row):
            return row['result'] == state
        return wrapper

    _not_set = lfilter(instate(NOTSET), results)
    _set = lfilter(instate(SET), results)
    _unset = lfilter(instate(UNSET), results)
    _reset = lfilter(instate(RESET), results)

    report = OrderedDict([
        (NOTSET, "had no article-json before, has *no* article-json *now*"),
        (SET, "had no article-json *before*, has article-json *now*"),
        (UNSET, "*had* article-json before, *no longer* has article-json"),
        (RESET, "*had* article-json before, *has* article-json now"),
        ('total-not-set', len(_not_set)),
        ('total-set', len(_set)),
        ('total-reset', len(_reset)),
        ('total-unset', len(_unset)),

        ('total-with-article-json', len(_set) + len(_reset)),
        ('total-without-article-json', len(_not_set) + len(_unset)),

        ('raw-set', _set),
        ('raw-unset', _unset),
    ])
    return report

#

@atomic
def revalidate_specific_article_version(msid, ver):
    LOG.debug('revalidating article version %s %s', msid, ver)
    avl = models.ArticleVersion.objects.filter(article__manuscript_id=msid, version=ver)
    return revalidate_many(avl)

@atomic
def revalidate_all_versions_of_article(msid):
    LOG.debug('revalidating all versions of %s', msid)
    avl = models.ArticleVersion.objects.filter(article__manuscript_id=msid)
    return revalidate_many(avl)

@atomic
def revalidate_all_article_versions():
    LOG.debug('revalidating ALL articles, this may take a while')
    return revalidate_many(models.ArticleVersion.objects.all())
