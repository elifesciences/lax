"these constants help to classify errors that are raised during normal operation of Lax"

UNKNOWN = 'unknown'

ALREADY_PUBLISHED = 'already-published'
INVALID = 'invalid-article-json'
BAD_REQUEST = 'bad-request'

# generic error we throw when we try to access something that isn't there
# or something that is there isn't correct, etc
PARSE_ERROR = 'error-parsing-article-json'

# attempt to ingest a version 2 when a version 1 not yet published
PREVIOUS_VERSION_UNPUBLISHED = 'previous-version-unpublished'

# attempt to ingest a version 2 when a version 1 does not exist
PREVIOUS_VERSION_DNE = 'previous-version-does-not-exist'

# thrown when we can't find something in the database that we expect to exist
NO_RECORD = 'record-not-found'
