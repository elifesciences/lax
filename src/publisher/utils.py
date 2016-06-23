import copy
import pytz
from dateutil import parser
from django.utils import timezone
from functools import partial
import os, sys
import logging
from django.db.models.fields.related import ManyToManyField

LOG = logging.getLogger(__name__)

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
    if x == None:
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
    if val == None:
        return None
    dt = parser.parse(val)
    if not dt.tzinfo:
        LOG.warn("encountered naive timestamp %r. UTC assumed.", val)
        return pytz.utc.localize(dt)
    else:
        # ensure tz is UTC??
        pass
    return dt


def filldict(ddict, keys, default):
    def filldictslot(ddict, key, val):
        if not ddict.has_key(key):
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
    return {k:v for k, v in dt.items() if k in ks}

def exsubdict(dt, ks):
    "same as subdict, but exclusionary"
    return {k:v for k, v in dt.items() if k not in ks}

def dictmap(func, data, **funcargs):
    "applies the given function over the values of the given data map. optionally passes any keyword args"
    if funcargs:
        func = partial(func, **funcargs)
    return {k:func(v) for k, v in data.items()}

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
