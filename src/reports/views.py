from django.core.urlresolvers import reverse
from django.db.models import Q
from datetime import datetime, timedelta
from publisher import rss
from . import logic as reports

import csv
# https://docs.djangoproject.com/en/1.9/howto/outputting-csv/
from django.http import StreamingHttpResponse

'''
# would be nice, but not right now
def status_page(self):
    return reports.status_report()
'''

class Echo(object):
    "An object that implements just the write method of the file-like interface."

    def write(self, value):
        """Write the value by returning it, instead of storing in a buffer."""
        return value

def streaming_csv_response(filename, rows):
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)
    response = StreamingHttpResponse((writer.writerow(row) for row in rows),
                                     content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="%s.csv"' % filename
    return response

# /reports/published.csv
def article_poa_vor_pubdates(request):
    return streaming_csv_response("published", reports.article_poa_vor_pubdates())

def time_to_publication(request):
    return streaming_csv_response("time-to-publication", reports.time_to_publication())

class PAWRecentReport(rss.AbstractReportFeed):
    def get_object(self, request, days_ago=None):
        if not days_ago:
            days_ago = 28
        limit = Q(datetime_published__gte=datetime.now() - timedelta(days=int(days_ago)))
        return {
            'title': 'PAW article data',
            'url': reverse('paw-recent-report', kwargs={'days_ago': days_ago}),
            'description': 'asdf',
            'params': None,
            'results': reports.paw_recent_data(limit)
        }

class PAWAheadReport(rss.AbstractReportFeed):
    def get_object(self, request, days_ago=None):
        if not days_ago:
            days_ago = 28
        limit = Q(datetime_published__gte=datetime.now() - timedelta(days=int(days_ago)))
        return {
            'title': 'PAW article data',
            'url': reverse('paw-ahead-report', kwargs={'days_ago': days_ago}),
            'description': 'asdf',
            'params': None,
            'results': reports.paw_ahead_data(limit)
        }
