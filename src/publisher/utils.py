from collections import OrderedDict
from functools import reduce
import jsonschema
from jsonschema.exceptions import relevance, ValidationError
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
from django.conf import settings
import traceback

LOG = logging.getLogger(__name__)

lmap = lambda func, *iterable: list(map(func, *iterable))

lfilter = lambda func, *iterable: list(filter(func, *iterable))

keys = lambda d: list(d.keys())

lzip = lambda *iterable: list(zip(*iterable))

def formatted_traceback(errobj):
    return ''.join(traceback.format_tb(errobj.__traceback__))

class StateError(RuntimeError):

    idx_code = 0
    idx_message = 1
    idx_trace = 2

    @property
    def code(self):
        return self.args[self.idx_code]

    @property
    def message(self):
        return self.args[self.idx_message]

    @property
    def trace(self):
        # we have no explicit error object to work with
        # just return a standard stacktrace
        if len(self.args) < 3:
            return formatted_traceback(self)

        traceobj = self.args[self.idx_trace]

        # if exception object has a 'trace' attribute, use that,
        # else just stringify the thing
        return getattr(traceobj, 'trace', None) or str(traceobj)

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

def ensure(assertion, msg):
    """intended as a convenient replacement for `assert` statements that
    get compiled away with -O flags"""
    if not assertion:
        raise LaxAssertionError(msg)

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

def toint(v):
    if v is None:
        return
    try:
        return int(v)
    except (ValueError, TypeError) as err:
        raise ValueError(str(err))

def mk_dxdoi_link(doi):
    return "https://dx.doi.org/%s" % doi

def pad_msid(msid):
    return "%05d" % int(msid)

def doi2msid(doi):
    "doi to manuscript id used in EJP"
    prefix = '10.7554/eLife.'
    return doi[len(prefix):].lstrip('0')

def msid2doi(msid):
    assert isint(msid), "given msid must be an integer: %r" % msid
    return '10.7554/eLife.%s' % pad_msid(msid)

def version_from_path(path):
    _, msid, ver = os.path.split(path)[-1].split('-') # ll: ['elife', '09560', 'v1.xml']
    ver = ver[1] # "v1.xml" -> "1"
    return int(msid), int(ver)

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
        dt = parser.parse(val, fuzzy=False) # raises ValueError
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

def renkey(ddict, oldkey, newkey):
    "renames a key in ddict from oldkey to newkey"
    if oldkey in ddict:
        ddict[newkey] = ddict[oldkey]
        del ddict[oldkey]
    return ddict

def renkeys(ddict, pair_list):
    for oldkey, newkey in pair_list:
        renkey(ddict, oldkey, newkey)

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


def json_loads(data, *args, **kwargs):
    if isinstance(data, bytes):
        data = data.decode('utf-8')
    return json.loads(data, *args, **kwargs)

def ordered_json_loads(data):
    "same as json_loads, just ensures order is preserved when loading maps"
    return json_loads(data, object_pairs_hook=OrderedDict)

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

# https://www.peterbe.com/plog/fastest-way-to-uniquify-a-list-in-python-3.6
# def f12(seq):
def unique(seq):
    # Raymond Hettinger
    # https://twitter.com/raymondh/status/944125570534621185
    return list(dict.fromkeys(seq))

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
        jsonschema.validate(struct, schema)
        return struct

    except ValueError:
        # json schema is broken
        #raise ValidationError("validation error: '%s' for: %s" % (err.message, struct))
        raise

    except ValidationError as err:
        # json is incorrect
        v = jsonschema.Draft4Validator(schema)
        err.error_list = list(v.iter_errors(struct))
        err.count = len(err.error_list)
        err.message, err.trace = format_validation_error_list(err.error_list, schema_path)
        raise err

def flatten_validation_errors(error):
    """an error can have sub-errors and each sub-error can have it's own errors (a tree).
    two nodes at different depths may be equally important in determining failure.
    this visits each node depth-first, returning a single list of errors that can be sorted."""
    rt = []
    for suberror in error.context:
        res = flatten_validation_errors(suberror)
        rt.extend(res)

    # finally, add parent to bottom of list
    rt.append(error)
    return rt

def validation_error_detail(err, schema_file):
    "returns a rendered template using the given error and origin schema file"
    error = '''This:

{instance}

is not valid because: {message}

It fails the schema:

{schema}

found at: {schema_path}

in the schema file: {schema_file}'''
    instance = json.dumps(err.instance, indent=4)
    if '\n' not in instance:
        instance = '    %s' % instance # give the simple value an indent
    return error.format(**{
        'instance': instance,
        'message': err.message,
        'schema': json.dumps(err.schema, indent=4),
        'schema_path': ' > '.join(map(str, list(err.relative_schema_path))),
        'schema_file': os.path.basename(schema_file)})

def validation_error_summary(sorted_error_list):
    "returns a rendered template for the given error list"
    error = '''Data fails to validate against multiple schemas.
Possible reasons (smallest, most relevant, errors first):

{enumerated_error_list}

The full errors including their schema are attached to this error as a 'trace', indexed by their number above.'''
    sub_error_list = ['{idx}. {message}'.format(idx=i + 1, message=err.message) for i, err in enumerate(sorted_error_list)]
    sub_error_list = unique(sub_error_list)[:10] # cap the number to something sensible, remove dupes.
    sub_error_str = '\n\n'.join(sub_error_list)
    return error.format(enumerated_error_list=sub_error_str)

def format_validation_error(error, schema_file):
    """formats the given error. if error is one of many failures, a summary formatted error is returned.
    return value is a pair of (error-msg, sub-error-msg-list)."""

    # https://python-jsonschema.readthedocs.io/en/latest/errors/?#jsonschema.exceptions.ValidationError

    if not error.context:
        # error is not composed of sub-errors, return early
        return validation_error_detail(error, schema_file), []

    # each of these failed, only author knows which one they were trying to validate against
    suberror_list = flatten_validation_errors(error)

    def sorter(ve):
        """smaller error messages are easier and faster to read together
        however, I'm still err'ing on the side of heuristic"""
        neg_path_len, weak_ve, strong_ve = relevance(ve)
        big_message = len(ve.message) > 75
        new_relevance = (big_message, neg_path_len, weak_ve, strong_ve)
        return new_relevance
    suberror_list = sorted(suberror_list, key=sorter)

    return validation_error_summary(suberror_list), [validation_error_detail(err, schema_file) for err in suberror_list]

def format_validation_error_list(error_list, schema_file):
    """same as `format_validation_error` but applied to a list of them.
    returns a pair of (top-level-errors, complete-error-list-including-subs)"""

    msg_list = []
    trace_list = []
    sep = "\n%s\n" % ("-" * 40,)

    total_errors = len(error_list) # realises lazy list
    many_errors = total_errors > settings.NUM_SCHEMA_ERRORS
    for i, error in enumerate(error_list[:settings.NUM_SCHEMA_ERRORS]):
        _msg, sub_msg_list = format_validation_error(error, schema_file)

        # (error 1 of 2) ...
        msg = "(error %s of %s)\n\n%s\n" % (i + 1, total_errors, _msg)
        if many_errors:
            # (error 1 of 10, 190 total)
            msg = "(error %s of %s, %s total)\n\n%s\n" % (i + 1, settings.NUM_SCHEMA_ERRORS, total_errors, _msg)

        # note: sub_msg will be an empty string if no sub-errors exist
        _subs = []
        for j, sub_msg in enumerate(sub_msg_list[:settings.NUM_SCHEMA_ERROR_SUBS]):
            # (error 1, possibility 2) ... This: foo ... is not valid because: ...
            _subs.append("(error %s, possibility %s)\n\n%s\n" % (i + 1, j + 1, sub_msg))
        sub_msg = sep.join(_subs)

        msg_list.append(msg)
        trace_list.append(msg + sub_msg)

    msg = sep.join(msg_list)
    trace = sep.join(trace_list)

    return msg, trace

#
#
#

# modified from:
# http://stackoverflow.com/questions/9323749/python-check-if-one-dictionary-is-a-subset-of-another-larger-dictionary
def partial_match(patn, real):
    """does real dict match pattern?"""
    for pkey, pvalue in patn.items():
        if isinstance(pvalue, dict):
            partial_match(pvalue, real[pkey]) # recurse
        else:
            ensure(real[pkey] == pvalue, "%s != %s" % (real[pkey], pvalue))
    return True

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
    # if create=True and update=False and object already exists, you'll get: (obj, False, False)
    # if the model cannot be found then None is returned: (None, False, False)
    return (inst, created, updated)
