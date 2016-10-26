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
    # print 'status >>>>>>>>', msid, merge_result['status'], schema
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
        LOG.error("validating %s with %s, failed to valid: %s", msid, schema, err)

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

def post_process(av, result):

    result = copy.deepcopy(result)

    # version date
    result['versionDate'] = av.datetime_published

    # status date
    if result['version'] == 1:
        result['statusDate'] = av.datetime_published
    else:
        v1vor = av.article.earliest_vor()
        if v1vor:
            result['statusDate'] = v1vor.datetime_published
        else:
            result['statusDate'] = result['published']

    if not result['statusDate']:
        LOG.error("somethign gucaksdlfasdf")
        result['statusDate'] = result['published']

    utils.delall(result, ['relatedArticles', 'digest', 'references'])

    return result

def merge_if_valid(av, quiet=True):
    ensure(isinstance(av, models.ArticleVersion), "I need an ArticleVersion object")
    result = merge(av)

    result = post_process(av, result)

    if valid(result, quiet=quiet):
        av.article_json_v1 = result
        av.article_json_v1_snippet = extract_snippet(result)
        av.save()
        return True
    LOG.warn("merge result failed to validate, not updating article version")
    return False
