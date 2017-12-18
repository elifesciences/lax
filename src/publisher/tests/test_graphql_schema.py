import os

from .base import BaseCase
from graphene.test import Client

from core.schema import schema as lax_schema
from publisher import ajson_ingestor
from publisher.models import Publisher


class TestGraphQLSchema(BaseCase):
    all_articles_query = '''{
	  all_articles {
	    edges {
	      node {
	        id
	      }
	    }
	  }
	}'''

    article_by_manuscript_id_query = '''{
	  all_articles(manuscript_id: 16695 ) {
	    edges {
	      node {
            date_received
            date_accepted
	        doi
	        id
	        manuscript_id
            volume
	        type
	      }
	    }
	  }
	}'''

    article_version_by_title_query = '''{
	  all_article_versions(title: "A Cryptochrome 2 Mutation Yields Advanced Sleep Phase in Human") {
	    edges {
	      node {
	        id
	        status
	        title
	        version
	      }
	    }
	  }
	}'''

    article_fragments_by_manuscript_id_query = '''{
	  all_article_fragments(article__manuscript_id: 16695) {
	    edges {
	      node {
	        id
	        fragment
	      }
	    }
	  }
	}'''

    publisher_by_name_query = '''{
	  all_publishers(name: "Some Publisher") {
	    edges {
	      node {
	        id
	        name
	      }
	    }
	  }
	}'''

    journal_by_name_query = '''{
	  all_journals(name: "eLife") {
	    edges {
	      node {
	        id
	        name
	      }
	    }
	  }
	}'''

    all_article_events = '''{
	  all_article_events {
	    edges {
	      node {
	        id
	        article {
	          manuscript_id
	        }
	        event
	        datetime_event
	        value
	      }
	    }
	  }
	}'''

    all_articles_for_journal_query = '''{
	  all_articles(journal__name: "eLife") {
	    edges {
	      node {
	        id
	        manuscript_id
	      }
	    }
	  }
	}'''

    all_events_for_article = '''{
	  all_article_events(article__manuscript_id: 16695) {
	    edges {
	      node {
	        id
	        event
	        datetime_event
	      }
	    }
	  }
	}'''

    def setUp(self):
        self.gql_client = Client(lax_schema)

        # ingest article fixtures
        for man_id in ['16695', '20105', '20125']:
            fp = os.path.join(self.fixture_dir, 'ajson', 'elife-{}-v1.xml.json'.format(man_id))
            ajson_ingestor.ingest(self.load_ajson(fp))

    def tearDown(self):
        pass

    def test_has_correct_number_of_articles(self):
        executed = self.gql_client.execute(self.all_articles_query)
        self.assertEqual(len(executed['data']['all_articles']['edges']), 3)

    def test_can_find_an_article_by_manuscript_id(self):
        executed = self.gql_client.execute(self.article_by_manuscript_id_query)
        article_result = executed['data']['all_articles']['edges'][0]['node']
        self.assertEqual(article_result['manuscript_id'], 16695)
        self.assertEqual(article_result['date_received'], '2016-04-06')
        self.assertEqual(article_result['date_accepted'], '2016-08-14')
        self.assertEqual(article_result['doi'], '10.7554/eLife.16695')
        self.assertEqual(article_result['volume'], 5)
        self.assertEqual(article_result['type'], 'research-article')

    def test_can_find_an_article_fragments_by_manuscript_id(self):
        executed = self.gql_client.execute(self.article_fragments_by_manuscript_id_query)
        article_fragments_result = executed['data']['all_article_fragments']['edges'][0]['node']
        self.assertTrue(article_fragments_result['fragment'])

    def test_can_find_an_article_version_by_title(self):
        executed = self.gql_client.execute(self.article_version_by_title_query)
        article_version_result = executed['data']['all_article_versions']['edges'][0]['node']
        self.assertEqual(article_version_result['status'], 'POA')
        self.assertEqual(article_version_result['title'], 'A Cryptochrome 2 Mutation Yields Advanced Sleep Phase in Human')
        self.assertEqual(article_version_result['version'], 1)

    def test_can_find_publisher_by_name(self):
        publisher_name = 'Some Publisher'
        Publisher.objects.create(name=publisher_name)

        executed = self.gql_client.execute(self.publisher_by_name_query)
        publisher_result = executed['data']['all_publishers']['edges'][0]['node']
        self.assertEqual(publisher_result['name'], publisher_name)

    def test_can_find_journal_by_name(self):
        executed = self.gql_client.execute(self.journal_by_name_query)
        journal_result = executed['data']['all_journals']['edges'][0]['node']
        self.assertEqual(journal_result['name'], 'eLife')

    def test_can_find_articles_by_journal(self):
        executed = self.gql_client.execute(self.all_articles_for_journal_query)
        articles = executed['data']['all_articles']['edges']
        self.assertEqual(len(articles), 3)

    def test_can_get_all_article_events(self):
        executed = self.gql_client.execute(self.all_article_events)
        self.assertEqual(len(executed['data']['all_article_events']['edges']), 9)

    def test_can_get_all_article_events_for_manuscript_id(self):
        executed = self.gql_client.execute(self.all_events_for_article)
        self.assertEqual(len(executed['data']['all_article_events']['edges']), 3)
