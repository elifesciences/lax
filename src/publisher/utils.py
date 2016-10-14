from jsonschema import validate as validator
from jsonschema import ValidationError
import copy, json
import pytz
from dateutil import parser
from django.utils import timezone
from datetime import datetime
from functools import partial
import logging
from django.db.models.fields.related import ManyToManyField

LOG = logging.getLogger(__name__)

def ensure(assertion, msg, *args):
    """intended as a convenient replacement for `assert` statements that
    get compiled away with -O flags"""
    if not assertion:
        raise AssertionError(msg % args)

def isint(v):
    try:
        int(v)
        return True
    except (ValueError, TypeError):
        return False

def doi2msid(doi):
    "doi to manuscript id used in EJP"
    prefix = '10.7554/eLife.'
    return doi[len(prefix):].lstrip('0')

def msid2doi(msid):
    assert len(str(msid)) <= 5, "given msid is too long: %r" % msid
    assert isint(msid), "given msid must be an integer: %r" % msid
    return '10.7554/eLife.%05d' % int(msid)

def nth(idx, x):
    # 'nth' implies a sequential collection
    if isinstance(x, dict):
        raise TypeError
    if x is None:
        return x
    try:
        return x[idx]
    except IndexError:
        return None
    except TypeError:
        raise

def first(x):
    return nth(0, x)

def second(x):
    return nth(1, x)

def firstnn(x):
    "given sequential `x`, returns the first non-nil value"
    return first(filter(None, x))

def delall(ddict, lst):
    "mutator. "
    def delkey(key):
        try:
            del ddict[key]
            return True
        except KeyError:
            return False
    return zip(lst, map(delkey, lst))

def ymd(dt):
    if dt:
        return dt.strftime("%Y-%m-%d")

def todt(val):
    "turn almost any formatted datetime string into a UTC datetime object"
    if val is None:
        return None

    if not isinstance(val, datetime):
        dt = parser.parse(val, fuzzy=False)
    else:
        dt = val # don't attempt to parse, work with what we have

    if not dt.tzinfo:
        # no timezone (naive), assume UTC and make it explicit
        LOG.warn("encountered naive timestamp %r from %r. UTC assumed.", dt, val)
        return pytz.utc.localize(dt)

    else:
        # ensure tz is UTC
        if dt.tzinfo != pytz.utc:
            LOG.debug("got an aware dt that isn't in utc: %r", dt)
            return dt.astimezone(pytz.utc)
    return dt

def utcnow():
    return datetime.now(pytz.utc)

def filldict(ddict, keys, default):
    def filldictslot(ddict, key, val):
        if key not in ddict:
            ddict[key] = val
    data = copy.deepcopy(ddict)
    for key in keys:
        if isinstance(key, tuple):
            key, val = key
        else:
            val = default
        filldictslot(data, key, val)
    return data


# stolen from:
# http://stackoverflow.com/questions/10823877/what-is-the-fastest-way-to-flatten-arbitrarily-nested-lists-in-python
def flatten(container):
    for i in container:
        if isinstance(i, list) or isinstance(i, tuple):
            for j in flatten(i):
                yield j
        else:
            yield i

def future_date(date):
    "predicate. returns True if given timezone-aware date is in the future"
    return date > timezone.now()

def subdict(dt, ks):
    "returns a copy of the given dictionary `dt` with only the keys `ks` included"
    return {k: v for k, v in dt.items() if k in ks}

def exsubdict(dt, ks):
    "same as subdict, but exclusionary"
    return {k: v for k, v in dt.items() if k not in ks}

def dictmap(func, data, **funcargs):
    "applies the given function over the values of the given data map. optionally passes any keyword args"
    if funcargs:
        func = partial(func, **funcargs)
    return {k: func(v) for k, v in data.items()}

def has_all_keys(data, expected_keys):
    actual_keys = data.keys()
    return all(map(lambda key: key in actual_keys, expected_keys))

def djobj_hasattr(djobj, key):
    return key in map(lambda f: f.name, djobj._meta.get_fields())

def to_dict(instance):
    opts = instance._meta
    data = {}
    for f in opts.concrete_fields + opts.many_to_many:
        if isinstance(f, ManyToManyField):
            if instance.pk is None:
                data[f.name] = []
            else:
                data[f.name] = list(f.value_from_object(instance).values_list('pk', flat=True))
        else:
            data[f.name] = f.value_from_object(instance)
    return data

def updatedict(ddict, **kwargs):
    newdata = copy.deepcopy(ddict)
    for key, val in kwargs.items():
        newdata[key] = val
    return newdata

def json_dumps(obj):
    "drop-in for json.dumps that handles datetime objects."
    def _handler(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            raise TypeError('Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj)))
    return json.dumps(obj, default=_handler)

# http://stackoverflow.com/questions/7204805/dictionaries-of-dictionaries-merge
def deepmerge(a, b, path=None):
    "merges b into a"
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                deepmerge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass # same leaf value
            else:
                # can't merge, replace
                a[key] = b
        else:
            a[key] = b[key]
    return a

#
#
#

def validate(struct, schema_path):
    # if given a string, assume it's json and try to load it
    # if given a data, assume it's serializable, dump it and load it
    try:
        struct = json.loads(json_dumps(struct))
    except ValueError as err:
        LOG.error("struct is not serializable: %s", err.message)
        raise

    try:
        schema = json.load(open(schema_path, 'r'))
        validator(struct, schema)
        return struct

    except ValueError as err:
        # your json schema is broken
        raise ValidationError("validation error: '%s' for: %s" % (err.message, struct))

    except ValidationError as err:
        # your json is incorrect
        LOG.error("struct failed to validate against schema: %s" % err.message)
        raise

#
#
#

def create_or_update(Model, orig_data, key_list, create=True, update=True, commit=True, **overrides):
    inst = None
    created = updated = False
    data = {}
    data.update(orig_data)
    data.update(overrides)
    try:
        # try and find an entry of Model using the key fields in the given data
        inst = Model.objects.get(**subdict(data, key_list))
        # object exists, otherwise DoesNotExist would have been raised
        if update:
            [setattr(inst, key, val) for key, val in data.items()]
            updated = True
    except Model.DoesNotExist:
        if create:
            inst = Model(**data)
            created = True

    if (updated or created) and commit:
        inst.save()

    # it is possible to neither create nor update.
    # in this case if the model cannot be found then None is returned: (None, False, False)
    return (inst, created, updated)
