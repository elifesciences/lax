import sys
from publisher import reports
from django.core.management.base import BaseCommand


def build_report_choices():
    candidates = reports.__dict__.keys()
    candidates = [c for c in candidates if callable(getattr(reports, c))]
    return candidates


class Command(BaseCommand):
    help = "for exporting views of data from lax"

    def add_arguments(self, parser):
        parser.add_argument("--report", choices=build_report_choices())

    def handle(self, *args, **options):
        report = options["report"]
        result = getattr(reports, report)()
        sys.exit(0 if result else 1)
