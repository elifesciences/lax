from publisher import models, utils
from publisher.utils import create_or_update

def add(art, event, value=None, datetime_event=None):
    # I suspect I'll need this wrapper soon enough
    # ajson_ingestor is getting very large and there is
    # ambiguity about how silent corrections to historical dates should be treated ...
    datetime_event = datetime_event or utils.utcnow()
    struct = {
        'event': event,
        'value': str(value),
        'datetime_event': datetime_event
    }
    #print('ae %s' % struct)
    create = update = True
    ae, created, updated = \
        create_or_update(models.ArticleEvent, struct, ['article', 'event', 'datetime_event'], create, update, article=art)
    return ae
