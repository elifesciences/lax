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

def valid(merge_result, schema_key, quiet=True):
    "returns True if the merged result is valid article-json"
    try:
        schema = settings.SCHEMA_IDX[schema_key]
        utils.validate(merge_result, schema)
        return merge_result
    except ValueError:
        # either the schema is bad or the struct is bad
        # either way, the error has been logged
        if not quiet:
            raise
    except ValidationError as err:
        # definitely not valid ;)
        LOG.exception(err)
        if not quiet:
            raise

def extract_snippet(merged_result):
    # TODO: derive these from the schema automatically somehow please
    snippet_keys = [
        'copyright', 'doi', 'elocationId', 'id', 'impactStatement',
        'pdf', 'published', 'research-organisms', 'status', 'subjects',
        'title', 'type', 'version', 'volume'
    ]
    return subdict(merged_result, snippet_keys)

def merge_if_valid(av, quiet=True):
    ensure(isinstance(av, models.ArticleVersion), "I need an ArticleVersion object")
    result = merge(av)
    if valid(result, schema_key=av.status, quiet=quiet):
        av.article_json_v1 = result
        av.article_json_v1_snippet = extract_snippet(result)
        av.save()
        return True
    LOG.warn("merge result failed to validate, not updating article version")
    return False
