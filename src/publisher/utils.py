from django.utils import timezone

def future_date(date):
    return date > timezone.now()

def subdict(dt, ks):
    return {k:v for k, v in dt.items() if k in ks}
