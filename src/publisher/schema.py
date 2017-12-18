import graphene
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType
from graphene.relay import Node

from .models import (
    Article,
    ArticleEvent,
    ArticleFragment,
    ArticleVersion,
    ArticleVersionRelation,
    ArticleVersionExtRelation,
    Journal,
    Publisher,
)

CHAR_FILTER_VALUES = ['exact', 'icontains', 'istartswith', 'iendswith']


class ArticleNode(DjangoObjectType):
    class Meta:
        model = Article
        interfaces = (Node,)
        filter_fields = {
            'id': ['exact'],
            'ejp_type': CHAR_FILTER_VALUES,
            'journal__name': CHAR_FILTER_VALUES,
            'manuscript_id': ['exact'],
            'type': CHAR_FILTER_VALUES,
        }


class ArticleEventNode(DjangoObjectType):
    class Meta:
        model = ArticleEvent
        interfaces = (Node,)
        filter_fields = {
            'id': ['exact'],
            'article__manuscript_id': ['exact'],
            'event': CHAR_FILTER_VALUES,
            'value': CHAR_FILTER_VALUES,
        }


class ArticleFragmentNode(DjangoObjectType):
    class Meta:
        model = ArticleFragment
        interfaces = (Node,)
        filter_fields = {
            'id': ['exact'],
            'type': CHAR_FILTER_VALUES,
            'article__manuscript_id': ['exact'],
        }


class ArticleVersionNode(DjangoObjectType):
    class Meta:
        model = ArticleVersion
        interfaces = (Node,)
        filter_fields = {
            'id': ['exact'],
            'title': CHAR_FILTER_VALUES,
            'status': CHAR_FILTER_VALUES,
        }


class ArticleVersionRelationNode(DjangoObjectType):
    class Meta:
        model = ArticleVersionRelation
        interfaces = (Node,)
        filter_fields = {
            'id': ['exact'],
        }


class ArticleVersionExtRelationNode(DjangoObjectType):
    class Meta:
        model = ArticleVersionExtRelation
        interfaces = (Node,)
        filter_fields = {
            'id': ['exact'],
            'uri': CHAR_FILTER_VALUES,
        }


class JournalNode(DjangoObjectType):
    class Meta:
        model = Journal
        interfaces = (Node,)
        filter_fields = {
            'id': ['exact'],
            'name': CHAR_FILTER_VALUES,
        }


class PublisherNode(DjangoObjectType):
    class Meta:
        model = Publisher
        interfaces = (Node,)
        filter_fields = {
            'id': ['exact'],
            'name': CHAR_FILTER_VALUES,
        }


class Query(graphene.AbstractType):
    article = Node.Field(ArticleNode)
    article_event = Node.Field(ArticleEventNode)
    article_fragment = Node.Field(ArticleFragmentNode)
    article_version = Node.Field(ArticleVersionNode)
    article_version_relation = Node.Field(ArticleVersionRelationNode)
    article_version_ext_relation = Node.Field(ArticleVersionExtRelationNode)
    journal = Node.Field(JournalNode)
    publisher = Node.Field(PublisherNode)

    all_articles = DjangoFilterConnectionField(ArticleNode)
    all_article_events = DjangoFilterConnectionField(ArticleEventNode)
    all_article_fragments = DjangoFilterConnectionField(ArticleFragmentNode)
    all_article_versions = DjangoFilterConnectionField(ArticleVersionNode)
    all_article_version_relations = DjangoFilterConnectionField(ArticleVersionRelationNode)
    all_article_version_ext_relations = DjangoFilterConnectionField(ArticleVersionExtRelationNode)
    all_journals = DjangoFilterConnectionField(JournalNode)
    all_publishers = DjangoFilterConnectionField(PublisherNode)
