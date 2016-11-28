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
        LOG.error("while validating %s with %s, failed to validate with error: %s", msid, schema, err.message)
        if not quiet:
            raise

def extract_snippet(merged_result):
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

def merge_if_valid(av, quiet=True):
    ensure(isinstance(av, models.ArticleVersion), "I need an ArticleVersion object")

    log_context = {'article-version': av, 'quiet': quiet}

    result = merge(av)
    result = pre_process(av, result)

    if valid(result, quiet=quiet):
        av.article_json_v1 = result
        av.article_json_v1_snippet = extract_snippet(result)
        av.save()
        return True

    LOG.warn("result of merging fragments failed to validate. not updating `ArticleVersion.article_json_v1*` fields", extra=log_context)
    return False
