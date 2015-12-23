from django.utils import timezone
from functools import partial

def future_date(date):
    return date > timezone.now()

def subdict(dt, ks):
    return {k:v for k, v in dt.items() if k in ks}

def dictmap(func, data, **funcargs):
    if funcargs:
        func = partial(func, **funcargs)
    return {k:func(v) for k, v in data.items()}

def djobj_hasattr(djobj, key):
    return key in map(lambda f: f.name, djobj._meta.get_fields())
