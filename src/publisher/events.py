"handles the creation of article events, converting bot-lax article-json into event objects."

from et3 import render
from et3.extract import path as p, lookup
from publisher import models, utils
from publisher.utils import create_or_update, todt


def elide(x):
    return x if x else render.EXCLUDE_ME


def add(art, event, value=None, datetime_event=None, uri=None):
    "creates/updates an ArticleEvent and attaches it to the given `art`"
    utils.ensure(art, "need art")
    datetime_event = datetime_event or utils.utcnow()
    if value:
        value = str(value)[:255]
    struct = {
        "event": event,
        "value": value,
        "datetime_event": datetime_event,
        "uri": uri,
    }
    create = update = True

    unique_key_list = ["article", "event", "datetime_event"]

    ae, created, updated = create_or_update(
        models.ArticleEvent,
        struct,
        unique_key_list,
        create,
        update,
        article=art,
    )
    return ae


def add_many(article, ae_list, force=False, skip_missing_datestamped=False):
    if skip_missing_datestamped:
        # ignores any events missing a 'datetime' key.
        # why?? not all articles generate all events, but a dict with keys will still be generated.
        # we detect these 'empty' events by looking at it's timestamp. if it's empty, discard it.
        # but, because we make life complicated for ourselves, some events don't have datestamps
        # and we need to capture them anyway.
        # WARN: if 'datetime' field is present but is empty, it *will be given a datetime of now()*.
        # use `elide` to remove field entirely.
        ae_list = [ae for ae in ae_list if "datetime_event" in ae]

    # lsh@2021-09-21: certain events should be unique, like preprint events.
    # if any events to be created are in the singleton list, remove them before creating new ones.
    # this behaviour will prevent re-ingesting POAs (with no events) from deleting events created during a VOR ingest.
    singletons = [models.DATE_PREPRINT_PUBLISHED]
    for ae in ae_list:
        if ae["event"] in singletons:
            models.ArticleEvent.objects.filter(
                article=article, event=ae["event"]
            ).delete()

    return [add(article, **struct) for struct in ae_list]


#
# event descriptions
# note: if the `datetime_event` field is missing it will exclude an event entirely.
#

INGEST_EVENTS = [
    {
        "event": [models.DATE_PREPRINT_PUBLISHED],
        "datetime_event": [p("-history.preprint.date", render.EXCLUDE_ME)],
        "value": [p("-history.preprint.description", None)],
        "uri": [p("-history.preprint.uri", None)],
    },
    {
        "event": [models.DATE_SENT_FOR_PEER_REVIEW],
        "datetime_event": [p("-history.date-sent-for-peer-review", render.EXCLUDE_ME)],
    },
    {
        "event": [models.DATE_XML_RECEIVED],
        "datetime_event": [p("-history.received", render.EXCLUDE_ME)],
    },
    {
        "event": [models.DATE_XML_ACCEPTED],
        "datetime_event": [p("-history.accepted", render.EXCLUDE_ME)],
    },
    {
        "event": [models.DATETIME_ACTION_INGEST],
        "datetime_event": [None],
        # "forced=true"
        "value": [p("forced?"), lambda v: "forced=%s" % v],
    },
]
INGEST_EVENTS__REVIEWED_PREPRINT = {
    "event": [models.DATE_REVIEWED_PREPRINT],
    "datetime_event": [p("date", render.EXCLUDE_ME)],
    "value": [p("description", None)],
    "uri": [p("uri", None)],
}

PUBLISH_EVENTS = [
    {
        "event": [models.DATETIME_ACTION_PUBLISH],
        "value": [p("forced?"), lambda v: "forced=%s" % v],
    }
]

EJP_EVENTS = [
    {
        "event": [models.DATE_EJP_QC],
        "datetime_event": [p("date_initial_qc"), todt, elide],
        "value": ["initial"],
    },
    {
        "event": [models.DATE_EJP_DECISION],
        "datetime_event": [p("date_initial_decision"), todt, elide],
        "value": [p("initial_decision")],
    },
    {
        "event": [models.DATE_EJP_QC],
        "datetime_event": [p("date_full_qc"), todt, elide],
        "value": ["full"],
    },
    {
        "event": [models.DATE_EJP_DECISION],
        "datetime_event": [p("date_full_decision"), todt, elide],
        "value": [p("decision")],
    },
    {
        "event": [models.DATE_EJP_QC],
        "datetime_event": [p("date_rev1_qc"), todt, elide],
        "value": ["rev1"],
    },
    {
        "event": [models.DATE_EJP_DECISION],
        "datetime_event": [p("date_rev1_decision"), todt, elide],
        "value": [p("rev1_decision")],
    },
    {
        "event": [models.DATE_EJP_QC],
        "datetime_event": [p("date_rev2_qc"), todt, elide],
        "value": ["rev2"],
    },
    {
        "event": [models.DATE_EJP_DECISION],
        "datetime_event": [p("date_rev2_decision"), todt, elide],
        "value": [p("rev2_decision")],
    },
    {
        "event": [models.DATE_EJP_QC],
        "datetime_event": [p("date_rev3_qc"), todt, elide],
        "value": ["rev3"],
    },
    {
        "event": [models.DATE_EJP_DECISION],
        "datetime_event": [p("date_rev3_decision"), todt, elide],
        "value": [p("rev3_decision")],
    },
    {
        "event": [models.DATE_EJP_QC],
        "datetime_event": [p("date_rev4_qc"), todt, elide],
        "value": ["rev4"],
    },
    {
        "event": [models.DATE_EJP_DECISION],
        "datetime_event": [p("date_rev4_decision"), todt, elide],
        "value": [p("rev4_decision")],
    },
]

#
#
#


def ajson_ingest_events(article, data, force=False):
    "scrapes and inserts events from article-json data"
    data["forced?"] = force
    ae_structs = [render.render_item(desc, data) for desc in INGEST_EVENTS]
    rpp_structs = [
        render.render_item(INGEST_EVENTS__REVIEWED_PREPRINT, event)
        for event in lookup(data, "-history.reviewed-preprint-list", [])
    ]
    return add_many(
        article, ae_structs + rpp_structs, force, skip_missing_datestamped=True
    )


def ajson_publish_events(av, force=False):
    ae_structs = [
        render.render_item(desc, {"article": av.article, "forced?": force})
        for desc in PUBLISH_EVENTS
    ]
    return add_many(av.article, ae_structs, force)


def ejp_ingest_events(article, data, force=False):
    "scrapes and inserts events from ejp data"
    data["forced?"] = force
    ae_structs = [render.render_item(desc, data) for desc in EJP_EVENTS]
    return add_many(article, ae_structs, force, skip_missing_datestamped=True)
