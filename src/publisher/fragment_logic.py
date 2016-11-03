#from datetime import datetime
import copy
from jsonschema import ValidationError
from django.db.models import Q
from django.conf import settings
from . import utils, models
from .utils import create_or_update, ensure, subdict
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
    return utils.merge_all(map(lambda f: f.fragment, fragments))

def valid(merge_result, quiet=True):
    "returns True if the merged result is valid article-json"
    msid = merge_result.get('id', '[no id]')
    schema_key = merge_result['status']
    schema = settings.SCHEMA_IDX[schema_key]
    try:
        utils.validate(merge_result, schema)
        return merge_result
    except ValueError as err:
        # either the schema is bad or the struct is bad
        LOG.error("validating %s with %s, failed to load json file: %s", msid, schema, err.message)
        if not quiet:
            raise
    except ValidationError as err:
        # definitely not valid ;)
        LOG.error("while validating %s with %s, failed to valid with error: %s", msid, schema, err)
        if not quiet:
            raise

def extract_snippet(merged_result):
    # TODO: derive these from the schema automatically somehow please
    snippet_keys = [
        'copyright', 'doi', 'elocationId', 'id', 'impactStatement',
        'pdf', 'published', 'researchOrganisms', 'status', 'statusDate', 'subjects',
        'title', 'titlePrefix', 'type', 'version', 'volume', 'authorLine'
    ]
    return subdict(merged_result, snippet_keys)

def pre_process(av, result):
    """this is the 'pre_process' step in: 
    merge -> pre_process -> valid? -> post_process -> store

    pre_process is called after `merge()` to add/remove/tweak the merged result
    prior to validation. especially useful during development, this should be 
    minimal once dev is complete"""
    
    result = copy.deepcopy(result)

    # at time of writing these, fixtures with these were failing to validate
    # TODO: these need to be removed 
    utils.delall(result, ['relatedArticles', 'digest', 'references'])

    return result

def post_process(av, result):
    """this is the 'post_process' step in: 
    merge -> pre_process -> valid? -> post_process -> store

    post_process is called after valid? to tweak the valid result.
    why oh why would one do this? well, during dev, we have instances
    where there are changes to the schema that are pending ..."""

    # replace the version date with what we have stored.
    # it will have a timezone component and be properly formatted
    # if unpublished, this value will be None
    # NOTE: null published values are currently verboten. once allowed, shift back into pre_process
    result['published'] = av.datetime_published
    
    # set the version date
    # if unpublished, this value will be None
    result['versionDate'] = av.datetime_published

    # calculate the status date
    # it's when the av.status changed to what it is
    result['statusDate'] = result['published'] # 'published' is the v1 pubdate remember
    v1vor = av.article.earliest_vor()
    if v1vor:
        # article has a vor in it's version history! use it's version date
        result['statusDate'] = v1vor.datetime_published.isoformat()

    return result

def merge_if_valid(av, allow_invalid=False, quiet=True):
    ensure(isinstance(av, models.ArticleVersion), "I need an ArticleVersion object")

    log_context = {'article-version': av, 'allow_invalid': allow_invalid, 'quiet': quiet}

    result = merge(av)

    result = pre_process(av, result)
    is_valid = valid(result, quiet=quiet)
    result = post_process(av, result)
    
    if is_valid or allow_invalid:
        if not is_valid:
            absolutely_required_keys = ['published']
            ensure(all(map(result.has_key, absolutely_required_keys)), \
                       "an invalid merge is being forced but I absolutely require the following keys that are not present: %s" % \
                       ', '.join(absolutely_required_keys))
            LOG.warn("article-json failed to validate but the 'allow_invalid' flag is set. storing invalid article-json.",
                     extra=log_context)
        av.article_json_v1 = result
        av.article_json_v1_snippet = extract_snippet(result)
        av.save()
        return True
    LOG.warn("merge result failed to validate, not updating article version", extra=log_context)
    return False
