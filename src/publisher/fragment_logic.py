import copy
import hashlib
from functools import partial
from jsonschema import ValidationError
from django.db.models import Q
from django.conf import settings
from . import utils, models, aws_events, codes
from .utils import create_or_update, ensure, subdict, StateError, lmap, first
import logging
from django.db import transaction

LOG = logging.getLogger(__name__)


def _getids(x):
    # TODO: this function is poor. split into several smaller ones with well defined signatures
    if utils.isint(x):
        # id is a msid
        return {"article": models.Article.objects.get(manuscript_id=x)}
    elif isinstance(x, models.Article):
        return {"article": x}
    elif isinstance(x, models.ArticleVersion):
        return {"article": x.article, "version": x.version}
    else:
        raise TypeError("failed to add article fragment, unhandled type %r" % type(x))


def add(x, ftype, fragment, pos=1, update=False):
    "adds given fragment to database. if fragment at this article+type+version exists, it will be overwritten"
    ensure(isinstance(fragment, dict), "all fragments must be a dictionary")
    # TODO: enable, but perhaps not here
    # if ftype != models.XML2JSON:
    #    verboten_keys = ['published', 'versionDate']
    #    ensure(not subdict(fragment, verboten_keys), "fragment contains illegal keys. illegal keys: %s" % (", ".join(verboten_keys),))
    data = {"version": None, "type": ftype, "fragment": fragment, "position": pos}
    data.update(_getids(x))
    key = ["article", "type", "version"]
    frag, created, updated = create_or_update(
        models.ArticleFragment, data, key, update=update
    )
    return frag, created, updated


def rm(msid, ftype):
    fragment = models.ArticleFragment.objects.get(
        article__manuscript_id=msid, type=ftype
    )
    fragment.delete()


def get(x, ftype):
    kwargs = {"type": ftype}
    kwargs.update(_getids(x))
    return models.ArticleFragment.objects.get(**kwargs)


def merge(av):
    """returns the merged result for a particlar article version"""
    # all fragments belonging to this specific article version or
    # to this article in general
    query = Q(version=av.version) | Q(version=None)
    if not settings.MERGE_FOREIGN_FRAGMENTS:
        # ((version=av.version OR version=none) AND type=xml->json)
        query &= Q(type=models.XML2JSON)
    fragments = models.ArticleFragment.objects.filter(article=av.article).filter(query)
    if not fragments:
        raise StateError(codes.NO_RECORD, "%r has no fragments that can be merged" % av)
    return utils.merge_all([f.fragment for f in fragments])


def _validate(msid, version, data, schema_key, quiet=True):
    """returns `True` if the given `data` is valid against at least one of the schema versions, pointed to by `schema_key`.
    `quiet=True` will swallow validation errors and log the error.
    `quiet=False` will raise a `ValidationError`."""

    assert schema_key and schema_key in ["poa", "vor", "list"], (
        "unsupported schema %r" % schema_key
    )

    log_context = {"msid": msid, "version": version}

    validation_errors = []
    schema_versions_list = []
    for schema_version, schema in settings.ALL_SCHEMA_IDX[schema_key]:
        try:
            versions_list.append(schema_version)
            return utils.validate(data, schema)

        except KeyError:
            msg = f"merging {msid} returned a data structure that couldn't be used to determine validity."
            LOG.exception(msg, extra=log_context)
            # legitimate error that needs to break things
            raise

        except ValueError:
            # either the schema is bad or the struct is bad
            msg = f"validating {msid} v{version} failed to load schema file {schema}."
            LOG.exception(msg, extra=log_context)
            # this is a legitimate error and needs to break things
            raise

        except ValidationError as err:
            # not valid under this schema version
            msg = f"while validating {msid} v{version} with {schema} v{schema_version}, failed to validate with error: {err.message}"
            LOG.info(msg)
            validation_errors.append(err)
            # try the next version of the schema (if one exists)
            continue

    if validation_errors and not quiet:
        versions_list = " and ".join(map(str, versions_list))
        # "failed to validate 12345 v1 using schema 'vor' version 1 and 2"
        msg = f"failed to validate {msid} v{version} using schema '{schema_key}' version {versions_list}"
        LOG.warning(msg)
        raise first(validation_errors)


def valid(merge_result, quiet=True):
    """returns `True` if the merged result is valid article-json.
    `quiet=True` will swallow validation errors and log the error.
    `quiet=False` will raise a `ValidationError`."""
    schema_key = merge_result["status"]  # 'poa' or 'vor'
    msid = merge_result.get("id", "[no id]")
    version = merge_result.get("version", "[no version]")
    return _validate(msid, version, merge_result, schema_key, quiet)


def valid_snippet(merge_result, quiet=True):
    """returns `True` if the merged result is a valid article-json snippet.
    Wraps snippet in a list and validates as an article list as there is no distinct schema for an article snippet.
    `quiet=True` will swallow validation errors and log the error.
    `quiet=False` will raise a `ValidationError`."""
    if not merge_result:
        return None
    schema_key = "list"
    wrapped_data = {"total": 1, "items": [merge_result]}
    msid = merge_result.get("id", "[no id]")
    version = merge_result.get("version", "[no version]")
    wrapped_data = _validate(msid, version, wrapped_data, schema_key, quiet)
    if wrapped_data:
        return wrapped_data["items"][0]


def extract_snippet(merged_result):
    if not merged_result:
        return None
    # TODO: derive these from the schema automatically somehow please
    snippet_keys = [
        # https://github.com/elifesciences/api-raml/blob/develop/src/snippets/article-vor.v1.yaml
        # https://github.com/elifesciences/api-raml/blob/develop/src/snippets/article.v1.yaml
        # pulled from given xml->json
        "copyright",
        "doi",
        "elocationId",
        "id",
        "impactStatement",
        "pdf",
        "published",
        "researchOrganisms",
        "status",
        "subjects",
        "title",
        "titlePrefix",
        "type",
        "version",
        "volume",
        "authorLine",
        # lsh@2020-06: removed as part of introduction of structured abstracts
        # "abstract",
        "figuresPdf",
        "image",
        # added by lax
        "statusDate",
        "stage",
        "versionDate",
    ]
    return subdict(merged_result, snippet_keys)


def pre_process(av, result):
    "supplements the merged fragments with more article data required for validating"
    # don't modify what we were given
    # result = utils.deepcopy_data(result) # passes tests
    result = copy.deepcopy(result)  # safer

    # we need to inspect this value later in `hashcheck` before it gets nullified
    result["-published"] = result["published"]

    # 'published' is when the v1 article was published
    # if unpublished, this value will be None
    if av.version == 1:
        result["published"] = av.datetime_published
    else:
        result["published"] = av.article.datetime_published

    result["versionDate"] = av.datetime_published

    # 'statusDate' is when the 'status' (poa/vor) value changed to the status being
    # served up in *this* result.
    if av.version == 1 or av.status == models.POA:
        # we're a POA or a version 1, statusDate is easy :)
        result["statusDate"] = result["published"]
    else:
        # we're a non-v1 VOR, statusDate is a little harder
        # we can't tell which previous version was a vor so consult our version history
        earliest_vor = av.article.earliest_vor()
        if earliest_vor:
            # article has a vor in it's version history! use it's version date
            result["statusDate"] = earliest_vor.datetime_published  # may be None
        else:
            # no VORs found AT ALL
            # this means our av == earliest_vor and it *hasn't been saved yet*
            result["statusDate"] = av.datetime_published  # may be/probably None

    if av.datetime_published:
        result["stage"] = "published"
    else:
        # unpublished! tweak the results
        # https://github.com/elifesciences/api-raml/blob/develop/src/snippets/article.v1.yaml
        result["stage"] = "preview"
        del result["versionDate"]
        del result["statusDate"]
        if av.version == 1:
            del result["published"]

    # these keys are not part of the article-json spec and shouldn't be made public
    delete_these = [
        "-related-articles-internal",
        "-related-articles-external",
        "-meta",
        "-history",
    ]
    utils.delall(result, delete_these)

    return result


def hash_ajson(merge_result):
    string = utils.json_dumps(merge_result, indent=None)
    return hashlib.md5(string.encode("utf-8")).hexdigest()


class Identical(RuntimeError):
    def __init__(self, msg, av, hashval):
        super(Identical, self).__init__(msg)
        LOG.info(
            msg,
            extra={
                "hash": hashval,
                "msid": av.article.manuscript_id,
                "version": av.version,
            },
        )
        self.av = av
        self.hashval = hashval


# function was split out to please complexity checker
def _identical_articles(raw_original, raw_new, final_new, oldhash, newhash):
    """compares the previous article version with the new article version.
    returns `True` if the two are identical.
    `raw_original` is the raw, merged, fragment data that hasn't been pre-processed yet.
    `raw_new` is the raw, merged, fragment data that hasn't been pre-processed yet.
    `final_new` is the new, pre-processed, fragment data.
    `oldhash` is the hash of the old data.
    `newhash` is the hash of the new data."""
    if not final_new:
        # no data, probably because it's invalid.
        return False

    identical_hash = oldhash == newhash

    # compare pubdates
    # `preprocess` will alter the publication date value if it hasn't been published yet.
    old_pubdate = raw_original.get("published")
    new_pubdate = final_new.get("-published")
    identical_pubdate = old_pubdate == new_pubdate

    # compare metadata
    # metadata are any attributes prefixed with a hyphen, for example "-related-articles-internal".
    # no metadata is present in the final rendered article-json and is used solely for other logic,
    # like related articles creating new relations in the database.
    meta_key_list = [
        "-related-articles-internal",
        "-related-articles-external",
        # "-history", # unused for now
    ]
    identical_meta = all(
        raw_original.get(meta_key) == raw_new.get(meta_key)
        for meta_key in meta_key_list
    )
    return identical_hash and identical_pubdate and identical_meta


# TODO: 'quiet' (validation-check) and 'update_fragment' are symptoms of spaghetti logic and need to be removed.
def set_article_json(av, data=None, quiet=True, hash_check=True, update_fragment=True):
    """updates the article with the result of the merge operation.
    if the result of the merge was valid, the merged result will be saved.
    if invalid, a ValidationError will be raised"""
    log_context = {"article-version": av, "hash_check": hash_check}

    try:
        # `merge` merges the *current* fragment set.
        # adding new fragment data must wait until we have what we need from the old
        raw_original = merge(av)
    except StateError:
        # NO RECORD: nothing has been ingested yet, no previous article data to compare to
        raw_original = {}

    if data:
        add(av, models.XML2JSON, data["article"], pos=0, update=update_fragment)

    raw_new = merge(av)

    # scrub the merged result, update dates, remove any meta, etc
    result = pre_process(av, raw_new)

    # validate the result.
    # if invalid, returns nothing.
    # if invalid and quiet=False, a ValidationError will be raised
    result = valid(result, quiet=quiet)

    snippet = extract_snippet(result)
    snippet = valid_snippet(snippet, quiet=quiet)

    oldhash = av.article_json_hash
    newhash = hash_ajson(result)

    if not result or not snippet:
        msg = "this article failed to merge it's fragments into a valid result and will not be saved to the database."
        LOG.critical(msg, extra=log_context)
        raise StateError(codes.INVALID, msg)

    if hash_check and _identical_articles(
        raw_original, raw_new, result, oldhash, newhash
    ):
        # if old is identical to new, then skip commit and roll the transaction back.
        # backfills (thousands of forced ingest) require skipping when identical
        # day-to-day INGEST and PUBLISH events require this too.
        # happens on multiple deliveries and silent corrections (forced ingest).
        raise Identical(
            "article data is identical to the article data already stored", av, newhash,
        )

    # postprocess
    del result["-published"]  # set in preprocess

    # save
    av.article_json_v1 = result
    av.article_json_v1_snippet = snippet
    av.article_json_hash = newhash
    av.save()

    return result


def set_all_article_json(art, **kwargs):
    "like `set_article_json`, but for every version of an article"
    return lmap(partial(set_article_json, **kwargs), art.articleversion_set.all())


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

        # hash check disabled. if fragment added that doesn't alter final article, then fragment should be preserved
        return set_all_article_json(art, quiet=False, hash_check=False)


def delete_fragment_update_article(art, key):
    "removes a fragment from an article, re-renders article, sends update event. if an error occurs, delete is rolled back and no event is sent"
    with transaction.atomic():
        # version=None ensures we don't ever remove the XML2JSON fragment
        models.ArticleFragment.objects.get(article=art, type=key, version=None).delete()

        # notify event bus that article change has occurred
        transaction.on_commit(partial(aws_events.notify, art.manuscript_id))

        # `hash_check=False`: if removing fragment doesn't alter final article, then fragment should still be removed
        return set_all_article_json(art, quiet=False, hash_check=False)


def reset_merged_fragments(art):
    """re-merges and re-sets article-json for given `art` object.
    Added 2021-01-21 to fix valid article-json that yielded invalid article-json snippets."""
    with transaction.atomic():
        # notify event bus that article change has occurred
        transaction.on_commit(partial(aws_events.notify, art.manuscript_id))

        # `hash_check=False`: reset merged fragments regardless of whether final article-json is changed
        return set_all_article_json(art, quiet=False, hash_check=False)


#
#
#


def location(av):
    "returns the location of the article xml stored in the primary fragment"
    try:
        obj = get(av, models.XML2JSON)
        return obj.fragment["-meta"]["location"]
    except models.ArticleFragment.DoesNotExist:
        return "no-article-fragment"
    except KeyError:
        return "no-location-stored"
