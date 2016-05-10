import os, requests
import models
from django.conf import settings
import logging
from publisher import ingestor, utils
from publisher.utils import first, second
from datetime import datetime
from django.utils import timezone

LOG = logging.getLogger(__name__)

def journal(name=None):
    journal = {'name': name}
    if not name:
        journal = settings.PRIMARY_JOURNAL
    if journal.has_key('inception') and timezone.is_naive(journal['inception']):
        journal['inception'] = timezone.make_aware(journal['inception'])
    obj, new = models.Journal.objects.get_or_create(**journal)
    if new:
        LOG.info("created new Journal %s", obj)
    return obj

def article(doi, version=None, lazy=True):
    """returns the latest version of the article identified by the
    doi, or the specific version given.
    Raises DoesNotExist if article not found."""
    try:
        if version:
            return models.Article.objects.get(doi__iexact=doi, version=version)
        return models.Article.objects.filter(doi__iexact=doi).order_by('-version')[:1][0]
    
    except (IndexError, models.Article.DoesNotExist):
        # TODO: and doi-looks-like-an-elife-doi
        # TODO: fetching articles lazily only works when a version is not specified. articles in the github repo have no version currently.
        if lazy and version == None:
            try:
                ingestor.import_article_from_github_repo(journal(), doi, version)
                return article(doi, version, lazy=False)
            except ValueError:
                # bad data, bad doi, etc
                pass
        raise models.Article.DoesNotExist()

def article_versions(doi):
    "returns all versions of the given article"
    return models.Article.objects.filter(doi__iexact=doi)

def create_attribute(**kwargs):
    at = models.AttributeType(**kwargs)
    at.save()
    return at

def get_attribute(article_obj, attr):
    """looks for the attribute on the article itself first, then looks at
    the list of ad-hoc article attributes and tries to retrieve attr from there."""
    if utils.djobj_hasattr(article_obj, attr):
        return getattr(article_obj, attr)
    try:
        article_obj.articleattribute_set.get(key__name=attr)
    except models.ArticleAttribute.DoesNotExist:
        return None

def add_update_article_attribute(article, key, val, extant_only=True):
    if utils.djobj_hasattr(article, key):
        # update the article object itself
        setattr(article, key, val)
        article.save()
        return {'key': key,
                'value': getattr(article, key),
                'doi': article.doi,
                'version': article.version}
    
    # get/create the attribute type
    try:
        attrtype = models.AttributeType.objects.get(name=key)
        # found
    except models.AttributeType.DoesNotExist:
        if extant_only:
            # we've been told to *not* create new types of attributes. die.
            raise
        # not found, create.
        kwargs = {
            'name': key,
            'type': models.DEFAULT_ATTR_TYPE,
            'description': "[automatically created]"
        }
        attrtype = models.AttributeType(**kwargs)
        attrtype.save()
        LOG.info("created new AttributeType %r", attrtype)
        
    # add/update the article attribute    
    kwargs = {
        'article': article,
        'key': attrtype,
        'value': val,
    }
    try:
        attr = models.ArticleAttribute.objects.get(**utils.subdict(kwargs, ['article', 'key']))
        # article already has this attribute. update it with whatever value we were given
        attr.value = val
        attr.save()

    except models.ArticleAttribute.DoesNotExist:
        # article doesn't have this particular attribute yet
        attr = models.ArticleAttribute(**kwargs)
        attr.save()

    return {'key': attrtype.name,
            'value': val,
            'doi': article.doi,
            'version': article.version}

def add_or_update_article(**article_data):
    """given a article data it attempts to find the article and update it,
    otherwise it will create it. return the created article"""
    assert article_data.has_key('doi'), "a value for 'doi' *must* exist"
    try:
        art = models.Article.objects.get(doi=article_data['doi'], version=article_data['version'])
        for key, val in article_data.items():
            setattr(art, key, val)
        art.save()

    except models.Article.DoesNotExist:
        art = models.Article(**article_data)
        art.save()

    return art

#
#
#

def not_latest_articles():
    "returns all articles that are NOT the most recent version"
    sql = '''
    select a.*
    from publisher_article a
    where exists (
        select * 
        from publisher_article b
        where a.doi = b.doi
        and b.version > a.version)'''
    return models.Article.objects.raw(sql)


def latest_articles(where=[], limit=None):
    assert isinstance(where, list), "'where' must be a list of (clause, param) pairs"
    assert all(map(lambda p: isinstance(p, tuple), where)), "'where' must be a list of tuples"
    if limit:
        assert isinstance(limit, str) or isinstance(limit, int), "'limit' but be a string or an int. got %s" % type(limit)

    
    args, sql = [], ['''
    SELECT a.*
    FROM publisher_article a
    INNER JOIN (
      SELECT doi, MAX(version) as max_version
      FROM publisher_article
      GROUP BY doi
    ) AS b
    ON a.doi = b.doi
    AND a.version = max_version''']

    '''
    %(where)s
    %(order_by)s
    %(limit)s
    '''
    # the where list should be a list of tuples
    # [(clause, value), (clause, value)]
    if where:
        # urgh. so, this is a total hack.
        # django doesn't support the syntax 'where field in (%s)' and then
        # you give it a list of values. you need to generate all those param
        # placeholders yourself. thats what the below is doing when it detects
        # a tuple of params given for a clause.
        for idx, pair in enumerate(where):
            clause, params = pair
            if isinstance(params, tuple):
                # update the args
                args.extend(params)
                # update the clause
                clause = clause % ', '.join(['%s'] * len(params))
                where[idx] = (clause, None)
            else:
                args.append(params)

        clause_list, param_list = map(first, where), map(second, where)
        sql += ['WHERE ' + ' AND '.join(clause_list)]

    sql += ['ORDER BY datetime_published DESC']

    if limit:
        args.append(limit)
        sql += ['LIMIT %s']

    sql = ' '.join(sql)
    args = filter(None, args)
    LOG.debug("generated raw sql %s and it's args %s", sql, args)
    res = models.Article.objects.raw(sql, args)
    LOG.debug("executed raw sql %s", res.query)
    return res



#
#
#

def mk_dxdoi_link(doi):
    return "http://dx.doi.org/%s" % doi

def check_doi(doi):
    """ensures that the doi both exists with crossref and that it
    successfully redirects to an article on the website"""
    return requests.get(mk_dxdoi_link(doi))


def doi2msid(doi):
    "manuscript id representation. used in EJP"
    prefix = '10.7554/eLife.'
    return doi[len(prefix):].lstrip('0')


#
#
#

def record_correction(artobj, when=None):
    if when:
        assert timezone.is_aware(when), "refusing a naive datetime."
        assert timezone.now() > when, "refusing a correction made in the future"
        if artobj.journal.inception:
            assert when > artobj.journal.inception, "refusing a correction made before the article's journal started"
    correction = models.ArticleCorrection(**{
        'article': artobj,
        'datetime_corrected': when if when else datetime.now()})
    correction.save()
    return correction
