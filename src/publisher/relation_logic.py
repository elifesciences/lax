from publisher import models, codes
from publisher.utils import create_or_update, ensure, first, StateError, msid2doi
import logging
from django.conf import settings

LOG = logging.getLogger(__name__)


def remove_relationships(av):
    """destroys any relationships that may exist for given ArticleVersion `av`.
    this is necessary to accommodate silent corrections where the relations for
    a specific article version may change."""
    models.ArticleVersionRelation.objects.filter(articleversion=av).delete()
    models.ArticleVersionExtRelation.objects.filter(articleversion=av).delete()
    models.ArticleVersionReviewedPreprintRelation.objects.filter(
        articleversion=av
    ).delete()


#
# internal relationships
# an ArticleVersion can be related to an Article
#


def relate(av, a):
    "creates a relationship between an ArticleVersion `av` and an Article `a`."
    data = {"articleversion": av, "related_to": a}
    return first(
        create_or_update(models.ArticleVersionRelation, data, create=True, update=False)
    )


def relate_using_msid(av, msid, quiet=False):
    if not settings.ENABLE_RELATIONS:
        return
    try:
        art = models.Article.objects.get(manuscript_id=msid)
    except models.Article.DoesNotExist:
        # we're trying to relate this ArticleVersion to an Article that doesnt exist.
        # create a stub article and relate it to that
        stub = {
            "manuscript_id": msid,
            "journal": av.article.journal,  # saves us having to refer to logic.py and circular dependencies
            "doi": msid2doi(msid),
        }
        art, _, _ = create_or_update(
            models.Article, stub, create=settings.RELATED_ARTICLE_STUBS, update=False
        )

    if art:
        return relate(av, art)

    msg = (
        "article with msid %r not found (and not created) attempting to relate %r => %s"
        % (msid, av, msid)
    )
    if not quiet:
        raise StateError(codes.NO_RECORD, msg)
    LOG.error(msg)


def relate_using_msid_list(av, msid_list, quiet=False):
    return [relate_using_msid(av, msid, quiet) for msid in msid_list]


#
# external relationships
# an ArticleVersion can be related to an ... ?
#


def associate(av, citation):
    ensure(
        isinstance(citation, dict) and "uri" in citation,
        "expecting a valid external-link type citation, got: %r" % citation,
    )
    data = {"articleversion": av, "uri": citation["uri"], "citation": citation}
    key = ["articleversion", "uri"]
    avr, _, _ = create_or_update(
        models.ArticleVersionExtRelation, data, key, create=True, update=True
    )
    return avr


def relate_using_citation_list(av, citation_list):
    return [associate(av, citation) for citation in citation_list]


# reviewed preprints relationships


def relate_using_reviewed_preprint(av, rpp):
    ensure(
        isinstance(av, models.ArticleVersion),
        "expected an ArticleVersion object, got: %r" % type(av),
    )
    ensure(
        isinstance(rpp, models.ReviewedPreprint),
        "expected a ReviewedPreprint object, got: %r" % type(rpp),
    )
    ensure(av.id and rpp.id, "objects must exist in database")
    data = {
        "articleversion": av,
        "reviewedpreprint": rpp,
    }
    rppr, _, _ = create_or_update(
        models.ArticleVersionReviewedPreprintRelation,
        data,
        create=True,
        update=True,
    )
    return rppr


#
# querying
#


def internal_relationships_for_article_version(av):
    """returns a list of Article objects that are related backwards and forwards by the given article version.
    Ordered by manuscript_id, asc."""
    # could I solve this with clever SQL/Django ORM tricks? almost certainly
    # do I have time to and is it important enough? absolutely not

    fwd = models.ArticleVersionRelation.objects.filter(articleversion=av)

    rev = models.ArticleVersionRelation.objects.filter(related_to=av.article)

    lst = [r.related_to for r in fwd]
    lst.extend([r.articleversion.article for r in rev])

    return sorted(set(lst), key=lambda artobj: artobj.manuscript_id)


def external_relationships_for_article_version(av):
    return models.ArticleVersionExtRelation.objects.filter(articleversion=av)


#
# testing
#


def _print_relations():
    for avr in models.ArticleVersionRelation.objects.all():
        print(avr)
