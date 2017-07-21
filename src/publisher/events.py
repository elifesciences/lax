from et3 import render
from et3.extract import path as p
from publisher import models, utils
from publisher.utils import create_or_update

def add(art, event, value=None, datetime_event=None):
    datetime_event = datetime_event or utils.utcnow()
    struct = {
        'event': event,
        'value': str(value),
        'datetime_event': datetime_event
    }
    create = update = True
    ae, created, updated = \
        create_or_update(models.ArticleEvent, struct, ['article', 'event', 'datetime_event'], create, update, article=art)
    return ae

def add_many(article, ae_list, force=False, skip_missing_datestamped=False):
    if skip_missing_datestamped:
        # ignores any events that don't have an explicit datetime
        ae_list = utils.lfilter(lambda struct: 'datetime_event' in struct, ae_list)
    return [add(article, **struct) for struct in ae_list]

#
#
#

INGEST_EVENTS = [
    # why the list with a single value here? et3.render expects a pipeline of transformations
    {'event': [models.DATE_XML_RECEIVED], 'datetime_event': [p('-history.received', render.EXCLUDE_ME)]},
    {'event': [models.DATE_XML_ACCEPTED], 'datetime_event': [p('-history.accepted', render.EXCLUDE_ME)]},
    {'event': [models.DATETIME_ACTION_INGEST], 'datetime_event': [None], 'value': [p('forced?'), lambda v: "forced=%s" % v]},
]

PUBLISH_EVENTS = [
    {'event': [models.DATETIME_ACTION_PUBLISH], 'value': [p('forced?'), lambda v: "forced=%s" % v]},
]

EJP_EVENTS = [
    '''
    {'event': [models.DATE_EJP_QC], 'datetime_event': [p('date_initial_qc')], 'value': ['initial']},
    {
        'event': [models.DATE_EJP_DECISION],
        'datetime_event': [p('date_initial_decision')],
        'value': [p('initial_decision')],
    },
    {'event': [models.DATE_EJP_QC], 'datetime_event': [p('date_full_qc')], 'value': ['full']},
    '''
]

'''
        "ejp_type": "TR",
        "date_initial_qc": "2015-09-03T00:00:00",
        "date_initial_decision": "2015-09-06T00:00:00",
        "initial_decision": "EF",

        "date_full_qc": "2015-09-09T00:00:00",
        "date_full_decision": "2015-10-02T00:00:00",
        "decision": "RVF",

        "date_rev1_qc": "2015-11-20T00:00:00",
        "date_rev1_decision": "2015-11-24T00:00:00",
        "rev1_decision": "RVF",

        "date_rev2_qc": "2015-12-14T00:00:00",
        "date_rev2_decision": "2015-12-16T00:00:00",
        "rev2_decision": "AF",

        "date_rev3_qc": null,
        "date_rev3_decision": null,
        "rev3_decision": null,

        "date_rev4_qc": null,
        "date_rev4_decision": null,
        "rev4_decision": null
'''

#
#
#
    
def ajson_ingest_events(article, data, force=False):
    "scrapes and inserts events from article-json data"
    data['forced?'] = force
    ae_structs = [render.render_item(desc, data) for desc in INGEST_EVENTS]
    return add_many(article, ae_structs, force, skip_missing_datestamped=True)

def ajson_publish_events(av, force=False):
    ae_structs = [render.render_item(desc, {'article': av.article, 'forced?': force}) for desc in PUBLISH_EVENTS]
    return add_many(av.article, ae_structs, force)

def ejp_ingest_events(article, data, force=False):
    "scrapes and inserts events from ejp data"
    data['forced?'] = force
    ae_structs = [render.render_item(desc, data) for desc in EJP_EVENTS]
    return add_many(article, ae_structs, force)
