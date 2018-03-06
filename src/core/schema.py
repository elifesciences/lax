import graphene

from publisher.schema import Query as PublisherQuery


class RootQuery(PublisherQuery, graphene.ObjectType):
    # This class will inherit from multiple Queries
    pass


schema = graphene.Schema(query=RootQuery, mutation=None, auto_camelcase=False)
