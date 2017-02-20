from functools import partial
from publisher import models
from publisher.utils import create_or_update, lmap

def remove_relationships(av):
    # destroy any relationships that may already exist
    models.ArticleVersionRelation.objects.filter(articleversion=av).delete()

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

def relate_using_msid_list(av, msid_list, replace=False):
    if replace:
        remove_relationships(av)
    return lmap(partial(relate_using_msid, av), msid_list)
