import copy
from publisher import (
    models,
    utils,
    fragment_logic as fragments,
    logic,
    events,
    aws_events,
)
from publisher import relation_logic as relationships, codes
from publisher.models import XML2JSON
from publisher.utils import create_or_update, StateError, atomic
import logging
from django.db import transaction
from et3 import render
from et3.extract import path as p
from functools import partial
from jsonschema import ValidationError
from django.conf import settings

LOG = logging.getLogger(__name__)

# make the article-json lax compatible
# receives a list of article-json


def exclude_if_empty(val):
    if not val:
        return render.EXCLUDE_ME
    return val


ARTICLE = {
    "manuscript_id": [p("id"), int],
    "volume": [p("volume")],
    "type": [p("type")],
    "doi": [p("id"), utils.msid2doi],  # remove when apiv1 is turned off
    "date_received": [p("-history.received", None), utils.todt, exclude_if_empty],
    "date_accepted": [p("-history.accepted", None), utils.todt, exclude_if_empty],
    # 'ejp_type': [p('type'), models.EJP_TYPE_REV_SLUG_IDX.get]
}

ARTICLE_VERSION = {
    "title": [p("title")],
    "version": [p("version")],
    "status": [p("status")],
    # only v1 article-json has a published date. v2 article-json does not
    "datetime_published": [p("published", None), utils.todt],
}

#
#
#


def _ingest_objects(data, create, update, force, log_context):
    "ingest helper. returns the journal, article, an article version and a list of article events"

    # WARN: log_context is a mutable dict

    # et3 won't mutate data but there may be a function in the pipeline that does. this is safest.
    data = copy.deepcopy(data)

    # this *could* be scraped from the provided data, but we have no time to
    # normalize journal names so we sometimes get duplicate journals in the db.
    # safer to disable until needed.
    journal = logic.journal()

    try:
        article_struct = render.render_item(ARTICLE, data["article"])
        article, created, updated = create_or_update(
            models.Article,
            article_struct,
            ["manuscript_id", "journal"],
            create,
            update,
            journal=journal,
        )

        log_context["article"] = article

        previous_article_versions = []
        if updated:
            previous_article_versions = list(
                article.articleversion_set.all().order_by("version")
            )  # earliest -> latest

        av_struct = render.render_item(ARTICLE_VERSION, data["article"])
        # this is an INGEST event and *not* a PUBLISH event. we don't touch the date published.
        # 2018-11-22: not strictly true anymore, forced INGEST events are expected to change pubdates
        # we'll handle that further down in _ingest though
        del av_struct["datetime_published"]

        av, created, updated = create_or_update(
            models.ArticleVersion,
            av_struct,
            ["article", "version"],
            create,
            update,
            commit=False,
            article=article,
        )

        log_context["article-version"] = av

        events.ajson_ingest_events(article, data["article"], force)

        return av, created, updated, previous_article_versions

    except KeyError as err:
        raise StateError(
            codes.PARSE_ERROR,
            "failed to scrape article data, key not present: %s" % err,
        )


#
#
#


def _ingest(data, force=False) -> models.ArticleVersion:
    """ingests article-json. returns a triple of (journal obj, article obj, article version obj)
    unpublished article-version data can be ingested multiple times UNLESS that article version has been published.
    published article-version data can be ingested only if force=True"""

    create = update = True
    log_context = {}

    try:
        av, created, updated, previous_article_versions = _ingest_objects(
            data, create, update, force, log_context
        )

        # enforce business rules
        if created:
            if previous_article_versions:
                last_version = previous_article_versions[-1]
                log_context["previous-version"] = last_version

                if not last_version.published():
                    # uhoh. we're attempting to create an article version before previous version of that article has been published.
                    msg = "refusing to ingest new article version when previous article version is still unpublished."
                    LOG.error(msg, extra=log_context)
                    raise StateError(codes.PREVIOUS_VERSION_UNPUBLISHED, msg)

                if not last_version.version + 1 == av.version:
                    # uhoh. we're attempting to create an article version out of sequence
                    msg = "refusing to ingest new article version out of sequence."
                    log_context.update(
                        {
                            "given-version": av.version,
                            "expected-version": last_version.version + 1,
                        }
                    )
                    LOG.error(msg, extra=log_context)
                    raise StateError(codes.PREVIOUS_VERSION_DNE, msg)

            # no other versions of article exist
            else:
                if not av.version == 1:
                    # uhoh. we're attempting to create our first article version and it isn't a version 1
                    msg = "refusing to ingest new article version out of sequence. no other article versions exist so I expect a v1"
                    log_context.update(
                        {"given-version": av.version, "expected-version": 1}
                    )
                    LOG.error(msg, extra=log_context)
                    raise StateError(codes.PREVIOUS_VERSION_DNE, msg)

        elif updated:
            # this version of the article already exists
            # this is only a problem if the article version has already been published
            if av.published():
                # uhoh. we've received an INGEST event for a previously published article version
                if not force:
                    # unless our arm is being twisted, die.
                    msg = "refusing to ingest new article data on an already published article version."
                    LOG.error(msg, extra=log_context)
                    raise StateError(codes.ALREADY_PUBLISHED, msg)
                else:
                    # this is a forced INGEST event on a published article
                    # aka a 'silent correction'
                    if av.version == 1:
                        # the expectation is that v1 publication dates will be updated here rather than
                        # sending a forced PUBLISH or INGEST+PUBLISH event
                        # note: v2 pub dates cannot be altered yet because they don't exist in the xml
                        datetime_published = utils.todt(data["article"]["published"])
                        av.datetime_published = datetime_published

        # 2017-12-20: shifted this block below the business rules checks.
        # this is so business rules (attempting to ingest out of order) are checked before
        # identity (this data already exists) and validity (this data is malformed)

        # validation and hash check of article-json occurs here
        quiet = False if settings.VALIDATE_FAILS_FORCE else force
        # only update the fragment if this article version has *not* been published *or* if force=True
        update_fragment = not av.published() or force
        fragments.set_article_json(
            av, data, quiet=quiet, hash_check=True, update_fragment=update_fragment
        )

        # update the relationships
        relationships.remove_relationships(av)
        relationships.relate_using_msid_list(
            av, data["article"].get("-related-articles-internal", []), quiet=force
        )
        relationships.relate_using_citation_list(
            av, data["article"].get("-related-articles-external", [])
        )

        # 2017-12-20: end section

        # passed all checks, save
        av.save()

        # notify event bus that article change has occurred
        transaction.on_commit(partial(aws_events.notify_all, av))

        return av

    except KeyError as err:
        # *probably* an error while scraping ...
        raise StateError(
            codes.PARSE_ERROR, "failed to scrape given article data: %r" % err
        )

    except fragments.Identical:
        # hashes match, transaction would result in identical article and unnecessary event being emitted. rollback
        raise

    except StateError:
        raise

    except ValidationError as err:
        raise StateError(codes.INVALID, err.message, err)

    except Exception:
        LOG.exception(
            "unhandled exception attempting to ingest article-json", extra=log_context
        )
        raise


@atomic
def ingest(*args, **kwargs) -> models.ArticleVersion:
    return _ingest(*args, **kwargs)


#
# PUBLISH requests
#


def _publish(msid, version, force=False) -> models.ArticleVersion:
    """attach a `datetime_published` value to an article version. if none provided, use RIGHT NOW.
    you cannot publish an already published article version unless force==True"""
    try:
        av = models.ArticleVersion.objects.get(
            article__manuscript_id=msid, version=version
        )
        if av.published():
            if not force:
                raise StateError(
                    codes.ALREADY_PUBLISHED,
                    "refusing to publish an already published article version",
                )

        # RULE: we won't use any other article fragments for determining the publication date
        # except the xml->json fragment.
        raw_data = fragments.get(av, XML2JSON).fragment

        # the json *will always* have a published date if v1 ...
        if version == 1:
            # pull that published date from the stored (but unpublished) article-json
            # and set the pub-date on the ArticleVersion object
            datetime_published = utils.todt(raw_data.get("published"))
            # todo: can this check be removed in favour of ajson validation?
            if not datetime_published:
                raise StateError(
                    codes.PARSE_ERROR,
                    "found 'published' value in article-json, but it's either null or unparsable as a date+time",
                )

        else:
            # but *not* if it's > v1. in this case, we generate one.
            if av.published() and force:
                # this article version is already published and a force publish request has been sent
                if False and "versionDate" in raw_data:  # fail this case for now.
                    # FUTURE CASE: when a 'versionDate' value is present in the article-json, use that.
                    # as of 2016-10-21 version history IS NOT captured in the xml,
                    # it won't be parsed by the bot-lax-adaptor and it
                    # won't find it's way here. this is a future-case only.
                    datetime_published = utils.todt(raw_data["versionDate"])
                    if not datetime_published:
                        raise StateError(
                            codes.PARSE_ERROR,
                            "found 'versionDate' value in article-json, but it's either null or unparseable as a datetime",
                        )
                else:
                    # CURRENT CASE
                    # this is a non-v1 forced PUBLISH event
                    # ignore anything given in the ajson and preserve the existing pubdate set by lax.
                    # if the pubdate for an article is to change, it must come from the xml (see above case)
                    datetime_published = av.datetime_published
            else:
                # CURRENT CASE
                # this article version hasn't been published yet. use a value of RIGHT NOW as the published date.
                datetime_published = utils.utcnow()

        av.datetime_published = datetime_published
        av.save()

        events.ajson_publish_events(av, force)

        # merge the fragments we have available and make them available for serving.
        # allow errors when the publish operation is being forced.
        # NOTE: hash checks will always fail on publish events as we modify the `versionDate`.
        quiet = False if settings.VALIDATE_FAILS_FORCE else force
        fragments.set_article_json(av, data=None, quiet=quiet, hash_check=False)

        # notify event bus that article change has occurred
        transaction.on_commit(partial(aws_events.notify_all, av))

        return av

    except ValidationError as err:
        # the problem isn't that the ajson is invalid, it's that we've allowed invalid ajson into the system
        raise StateError(
            codes.INVALID,
            "refusing to publish an article '%sv%s' with invalid article-json"
            % (msid, version),
            err,
        )

    except models.ArticleFragment.DoesNotExist:
        raise StateError(
            codes.NO_RECORD,
            "no 'xml->json' fragment found. being strict and failing this publish. please INGEST!",
        )

    except models.ArticleVersion.DoesNotExist:
        # attempted to publish an article that doesn't exist ...
        raise StateError(
            codes.NO_RECORD,
            "refusing to publish an article '%sv%s' that doesn't exist"
            % (msid, version),
        )


@atomic
def publish(*args, **kwargs) -> models.ArticleVersion:
    return _publish(*args, **kwargs)


#
# INGEST+PUBLISH requests
#


@atomic
def ingest_publish(data, force=False, dry_run=False) -> models.ArticleVersion:
    "convenience. publish an article if it were successfully ingested"
    av = _ingest(data, force=force)
    return _publish(av.article.manuscript_id, av.version, force=force)
