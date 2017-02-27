from functools import partial
from publisher import models
from publisher.utils import create_or_update, lmap, ensure, first
#from django.db.models import Q

def remove_relationships(av):
    "destroys any relationships that may exist for given ArticleVersion"
    models.ArticleVersionRelation.objects.filter(articleversion=av).delete()
    models.ArticleVersionExtRelation.objects.filter(articleversion=av).delete()

#
# internal relationships
# an ArticleVersion can be related to an Article
#

def relate(av, a):
    "creates a relationship between an ArticleVersion and an Article"
    data = {
        'articleversion': av,
        'related_to': a
    }
    return first(create_or_update(models.ArticleVersionRelation, data, create=True, update=False))

def relate_using_msid(av, msid):
    return relate(av, models.Article.objects.get(manuscript_id=msid))

def relate_using_msid_list(av, msid_list):
    return lmap(partial(relate_using_msid, av), msid_list)

#
# external relationships
# an ArticleVersion can be related to an ... ?
#

def associate(av, citation):
    ensure(isinstance(citation, dict) and 'uri' in citation,
           "expecting a valid external-link type citation, got: %r" % citation)
    data = {
        'articleversion': av,
        'uri': citation['uri'],
        'citation': citation,
    }
    key = ['articleversion', 'uri']
    avr, _, _ = create_or_update(models.ArticleVersionExtRelation, data, key, create=True, update=True)
    return avr

def relate_using_citation_list(av, citation_list):
    return lmap(partial(associate, av), citation_list)

#
# querying
#

def internal_relationships_for_article_version(av):
    "returns a list of Article objects that are related, backward and forwards, by the given article version"
    # could I solve this with clever SQL/Django ORM tricks? almost certainly
    # do I have time to and is it important enough? absolutely not

    fwd = models.ArticleVersionRelation.objects \
        .filter(articleversion=av)

    rev = models.ArticleVersionRelation.objects \
        .filter(related_to=av.article)

    lst = [r.related_to for r in fwd]
    lst.extend([r.articleversion.article for r in rev])

    return lst

def external_relationships_for_article_version(av):
    return models.ArticleVersionExtRelation.objects \
        .filter(articleversion=av)
