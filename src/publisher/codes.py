"these constants help to classify errors that are raised during normal operation of Lax"

idx = {}

UNKNOWN = "unknown"
idx[UNKNOWN] = (
    "an error occured that we haven't seen before to know how to best handle it"
)

INVALID = "invalid-article-json"
idx[INVALID] = (
    "the article json failed validation against the spec. this happens at several points during INGEST and PUBLISH requests"
)

BAD_REQUEST = "bad-request"
idx[BAD_REQUEST] = (
    "the request to lax couldn't be parsed or contained errors after being parsed"
)

PARSE_ERROR = "error-parsing-article-json"
idx[PARSE_ERROR] = (
    """generic error we throw when we try to access something that isn't there or something that is there isn't correct, etc"""
)

ALREADY_PUBLISHED = "already-published"
idx[ALREADY_PUBLISHED] = (
    "a PUBLISH or INGEST request was received for a specific version of an article already published. an INGEST request can happen many times before publication but can only happen after publication if the 'force' flag is present"
)

PREVIOUS_VERSION_UNPUBLISHED = "previous-version-unpublished"
idx[PREVIOUS_VERSION_UNPUBLISHED] = (
    "attempt to ingest a version 2 when a version 1 not yet published"
)

PREVIOUS_VERSION_DNE = "previous-version-does-not-exist"
idx[PREVIOUS_VERSION_DNE] = (
    "attempt to ingest a version 2 when a version 1 does not exist"
)

NO_RECORD = "record-not-found"
idx[NO_RECORD] = (
    "thrown when we can't find something in the database that we expect to exist"
)

# ---


def explain(code):
    return idx.get(code)
