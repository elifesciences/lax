from functools import partial
from publisher import models
from publisher.utils import create_or_update, lmap, ensure

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
    # create new relation
    avr, _, _ = create_or_update(models.ArticleVersionRelation, data, create=True, update=False)
    return avr

def relate_using_msid(av, msid):
    return relate(av, models.Article.objects.get(manuscript_id=int(msid)))

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
