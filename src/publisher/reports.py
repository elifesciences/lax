# not really reports, but I copied the logic from a module that used to exist called 'reports'.
# it is just adhoc data dumps that print data to stdout
# use `./src/manage.py output --report <funcname>`

import sys, csv
from . import models, utils, fragment_logic

import logging

LOG = logging.getLogger(__name__)

# used by backfill.sh to get a list of
def article_version_list_as_csv():
    q = (
        models.ArticleVersion.objects.select_related("article")
        .defer("article_json_v1", "article_json_v1_snippet")
        .order_by("article__manuscript_id", "version")
        .all()
    )

    def mkrow(av):
        msid = utils.pad_msid(av.article.manuscript_id)
        version = av.version
        # this is very expensive to do.
        # the difference is between instant and minutes.
        loc = fragment_logic.location(av)
        if "," in loc:
            # bad data that may screw up consumers
            LOG.warn(
                "bad data! location for %s, version %s contains a comma: %s",
                msid,
                version,
                loc,
            )
        return [msid, version, loc]

    try:
        writer = csv.writer(sys.stdout, lineterminator="\n")
        sys.stdout.write(str(q.count()))
        [writer.writerow(mkrow(row)) for row in q]
        return True
    except KeyboardInterrupt:
        return False
