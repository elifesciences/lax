from jsonschema import ValidationError
from django.db.models import Q
from django.conf import settings
from . import utils, models
from .utils import create_or_update, ensure, subdict, StateError
import logging

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
    return models.ArticleFragment.objects.get(**kwargs).fragment

def merge(av):
    """returns the merged result for a particlar article version"""
    # all fragments belonging to this specific article version or
    # to this article in general
    fragments = models.ArticleFragment.objects \
        .filter(article=av.article) \
        .filter(Q(version=av.version) | Q(version=None)) \
        .order_by('position')
    if not fragments:
        raise StateError("%r has no fragments that can be merged" % av)
    return utils.merge_all(map(lambda f: f.fragment, fragments))

def valid(merge_result, quiet=True):
    "returns True if the merged result is valid article-json"
    msid = merge_result.get('id', '[no id]')
    log_context = {
        'msid': msid,
        'version': merge_result.get('version', '[no version]'),
    }
    try:
        schema_key = merge_result['status'] # poa or vor
        schema = settings.SCHEMA_IDX[schema_key]
        utils.validate(merge_result, schema)
        return merge_result

    except KeyError:
        msg = "merging %s returned a data structure that couldn't be used to determine validation"
        LOG.exception(msg, msid, extra=log_context)
        # legitimate error that needs to break things
        raise

    except ValueError as err:
        # either the schema is bad or the struct is bad
        LOG.exception("validating %s failed to load schema file %s", msid, schema, extra=log_context)
        # this is a legitimate error and needs to break things
        raise

    except StateError as err:
        msg = "article is in a state where it can't be validated: %s" % err
        LOG.warn(msg, extra=log_context)
        if not quiet:
            raise

    except ValidationError as err:
        # definitely not valid ;)
        LOG.error("while validating %s with %s, failed to validate with error: %s", msid, schema, err.message)
        if not quiet:
            raise

def extract_snippet(merged_result):
    if not merged_result:
        return None
    # TODO: derive these from the schema automatically somehow please
    snippet_keys = [
        # pulled from given xml->json
        'copyright', 'doi', 'elocationId', 'id', 'impactStatement',
        'pdf', 'published', 'researchOrganisms', 'status', 'subjects',
        'title', 'titlePrefix', 'type', 'version', 'volume', 'authorLine',

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

    # 'statusDate' is when the av.status value changed to what it is
    result['statusDate'] = result['published'] # 'published' is the v1 pubdate, remember
    v1vor = av.article.earliest_vor()
    if v1vor and v1vor.datetime_published:
        # article has a published vor in it's version history! use it's version date
        result['statusDate'] = utils.ymdhms(v1vor.datetime_published)

    if av.datetime_published:
        result['stage'] = 'published'
    else:
        result['stage'] = 'preview'
        del result['versionDate']
        if av.version == 1:
            del result['published']
            del result['statusDate']

    return result

def merge_and_preprocess(av):
    "merges fragments AND pre-processes them for saving"
    return pre_process(av, merge(av))

def merge_if_valid(av, quiet=True):
    """merges, pre-processes and validates the fragments of the given ArticleVersion instance.
    if the result is valid, returns the merge result.
    if invalid, returns nothing.
    if invalid and quiet=False, a ValidationError will be raised"""
    result = merge_and_preprocess(av)
    if valid(result, quiet=quiet):
        return result

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

#
#
#

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
