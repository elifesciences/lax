from functools import reduce
from jsonschema import validate as validator
from jsonschema import ValidationError
import os, copy, json, glob
import pytz
from dateutil import parser
from django.utils import timezone
from datetime import datetime
from functools import partial
import logging
from django.db.models.fields.related import ManyToManyField
from kids.cache import cache
from rfc3339 import rfc3339
from django.db import transaction, IntegrityError

LOG = logging.getLogger(__name__)

lmap = lambda func, *iterable: list(map(func, *iterable))

lfilter = lambda func, *iterable: list(filter(func, *iterable))

keys = lambda d: list(d.keys())

class StateError(RuntimeError):
    @property
    def message(self):
        return self.args[0]

class LaxAssertionError(AssertionError):
    @property
    def message(self):
        return self.args[0]

def atomic(fn):
    def wrapper(*args, **kwargs):
        result, rollback_key = None, 'dry run rollback'
        # NOTE: dry_run must always be passed as keyword parameter (dry_run=True)
        dry_run = kwargs.pop('dry_run', False)
        try:
            with transaction.atomic():
                result = fn(*args, **kwargs)
                if dry_run:
                    # `transaction.rollback()` doesn't work here because the `transaction.atomic()`
                    # block is expecting to do all the work and only rollback on exceptions
                    raise IntegrityError(rollback_key)
                return result
        except IntegrityError as err:
            message = err.args[0]
            if dry_run and message == rollback_key:
                return result
            # this was some other IntegrityError
            raise
    return wrapper

def freshen(obj):
    return type(obj).objects.get(pk=obj.pk)

def ensure(assertion, msg, *args):
    """intended as a convenient replacement for `assert` statements that
    get compiled away with -O flags"""
    if not assertion:
        raise LaxAssertionError(msg % args)

def resolve_path(p, ext='.json'):
    "returns a list of absolute paths given a file or a directory"
    p = os.path.abspath(p)
    if os.path.isdir(p):
        paths = glob.glob("%s/*%s" % (p.rstrip('/'), ext))
        paths.sort(reverse=True)
        return paths
    return [p]

def isint(v):
    try:
        int(v)
        return True
    except (ValueError, TypeError):
        return False

def mk_dxdoi_link(doi):
    return "https://dx.doi.org/%s" % doi

def doi2msid(doi):
    "doi to manuscript id used in EJP"
    prefix = '10.7554/eLife.'
    return doi[len(prefix):].lstrip('0')

def msid2doi(msid):
    assert isint(msid), "given msid must be an integer: %r" % msid
    return '10.7554/eLife.%05d' % int(msid)

def compfilter(fnlist):
    "returns true if given val "
    def fn(val):
        return all([fn(val) for fn in fnlist])
    return fn

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
    return first(lfilter(None, x))

def delall(ddict, lst):
    "mutator. "
    def delkey(key):
        try:
            del ddict[key]
            return True
        except KeyError:
            return False
    return list(zip(lst, lmap(delkey, lst)))

def ymd(dt):
    "returns a simple YYYY-MM-DD representation of a datetime object"
    if dt:
        return dt.strftime("%Y-%m-%d")

def todt(val):
    "turn almost any formatted datetime string into a UTC datetime object"
    if val is None:
        return None
    dt = val
    if not isinstance(dt, datetime):
        dt = parser.parse(val, fuzzy=False)
    dt.replace(microsecond=0) # not useful, never been useful, will never be useful.

    if not dt.tzinfo:
        # no timezone (naive), assume UTC and make it explicit
        LOG.debug("encountered naive timestamp %r from %r. UTC assumed.", dt, val)
        return pytz.utc.localize(dt)

    else:
        # ensure tz is UTC
        if dt.tzinfo != pytz.utc:
            LOG.debug("converting an aware dt that isn't in utc TO utc: %r", dt)
            return dt.astimezone(pytz.utc)
    return dt

def utcnow():
    "returns a UTC datetime stamp with a UTC timezone object attached"
    # there is a datetime.utcnow(), but it doesn't attach a timezone object
    return datetime.now(pytz.utc).replace(microsecond=0)

def ymdhms(dt):
    "returns an rfc3339 representation of a datetime object"
    if dt:
        dt = todt(dt) # convert to utc, etc
        return rfc3339(dt, utc=True)

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
    actual_keys = keys(data)
    return all([key in actual_keys for key in expected_keys])

def djobj_hasattr(djobj, key):
    return key in [f.name for f in djobj._meta.get_fields()]

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

def json_loads(data, *args, **kwargs):
    if isinstance(data, bytes):
        data = data.decode('utf-8')
    return json.loads(data, *args, **kwargs)

def json_dumps(obj, **kwargs):
    "drop-in for json.dumps that handles datetime objects."
    def _handler(obj):
        if hasattr(obj, 'isoformat'):
            return ymdhms(obj)
        else:
            raise TypeError('Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj)))
    return json.dumps(obj, default=_handler, **kwargs)

# http://stackoverflow.com/questions/29847098/the-best-way-to-merge-multi-nested-dictionaries-in-python-2-7
def deepmerge(d1, d2):
    d1 = copy.deepcopy(d1)
    for k in d2:
        if k in d1 and isinstance(d1[k], dict) and isinstance(d2[k], dict):
            deepmerge(d1[k], d2[k])
        else:
            d1[k] = d2[k]
    return d1

def merge_all(dict_list):
    ensure(all([isinstance(r, dict) for r in dict_list]), "not all given values are dictionaries!")
    return reduce(deepmerge, dict_list)

def boolkey(*args):
    """given N values, returns a tuple of their truthiness.
    for example: boolkey(0, 1, 2) => (False, True, True)"""
    return tuple([not not v for v in args])

#
#
#

@cache
def load_schema(schema_path):
    return json.load(open(schema_path, 'r', encoding='utf-8'))

def validate(struct, schema_path):
    try:
        # this has the effect of converting any datetime objects to rfc3339 formatted strings
        struct = json.loads(json_dumps(struct))
    except ValueError as err:
        LOG.error("struct is not serializable: %s", err.message)
        raise

    try:
        schema = load_schema(schema_path)
        validator(struct, schema)
        return struct

    except ValueError as err:
        # your json schema is broken
        #raise ValidationError("validation error: '%s' for: %s" % (err.message, struct))
        raise

    except ValidationError as err:
        # your json is incorrect
        #LOG.error("struct failed to validate against schema: %s" % err.message)
        raise

#
#
#

def create_or_update(Model, orig_data, key_list=None, create=True, update=True, commit=True, **overrides):
    inst = None
    created = updated = False
    data = {}
    data.update(orig_data)
    data.update(overrides)
    key_list = key_list or data.keys()
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
        inst.full_clean()
        inst.save()

    # it is possible to neither create nor update.
    # in this case if the model cannot be found then None is returned: (None, False, False)
    return (inst, created, updated)
