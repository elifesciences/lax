"""
the `ingest` script is distinct from the `import` script. 

The import script does not obey business rules and merrily update published dates and so on without concern. It is good for bulk imports, development and once-off patching of article data.

The ingest script DOES obey business rules and will not publish things twice, 

"""

import sys, json, argparse
from django.core.management.base import BaseCommand
from publisher import ajson_ingestor, utils
from publisher.ajson_ingestor import StateError
import logging

LOG = logging.getLogger(__name__)

INVALID = 'invalid'
IMPORT_TYPES = ['ingest', 'publish', 'ingest-publish']
INGEST, PUBLISH, BOTH = IMPORT_TYPES
INGESTED, PUBLISHED = 'ingested', 'published'

import os
from django.core.management.base import CommandParser

class ModCommand(BaseCommand):
    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``ArgumentParser`` which will be used to
        parse the arguments to this command.
        """
        parser = CommandParser(
            self, prog="%s %s" % (os.path.basename(prog_name), subcommand),
            description=self.help or None,
        )
        #parser.add_argument('--version', action='version', version=self.get_version())
        parser.add_argument(
            '-v', '--verbosity', action='store', dest='verbosity', default=1,
            type=int, choices=[0, 1, 2, 3],
            help='Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output',
        )
        parser.add_argument(
            '--settings',
            help=(
                'The Python path to a settings module, e.g. '
                '"myproject.settings.main". If this isn\'t provided, the '
                'DJANGO_SETTINGS_MODULE environment variable will be used.'
            ),
        )
        parser.add_argument(
            '--pythonpath',
            help='A directory to add to the Python path, e.g. "/home/djangoprojects/myproject".',
        )
        parser.add_argument('--traceback', action='store_true', help='Raise on CommandError exceptions')
        parser.add_argument(
            '--no-color', action='store_true', dest='no_color', default=False,
            help="Don't colorize the command output.",
        )
        self.add_arguments(parser)
        return parser

class Command(ModCommand):
    help = ''

    def add_arguments(self, parser):
        # update articles that already exist?
        parser.add_argument('--id', dest='msid', type=int, required=True)
        parser.add_argument('--version',  dest='version', type=int, required=True)
        parser.add_argument('--force', action='store_true', default=False)
        parser.add_argument('--dry-run', action='store_true', default=False)

        parser.add_argument('--ingest', dest='action', action='store_const', const=INGEST)
        parser.add_argument('--publish', dest='action', action='store_const', const=PUBLISH)
        parser.add_argument('--ingest+publish', dest='action', action='store_const', const=BOTH)

        parser.add_argument('infile', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

    def write(self, out=None):
        if not isinstance(out, basestring):
            out = utils.json_dumps(out) # encodes datetime objects
        self.stdout.write(out)
        self.stdout.flush()

    def error(self, errtype, message):
        struct = {
            'status': errtype,
            'message': message
        }
        self.log_context['status'] = errtype
        LOG.error(message, extra=self.log_context)
        self.write(struct)

    def success(self, action, av, dry_run=False):
        status = INGESTED if action == INGEST else PUBLISHED
        attr = 'datetime_published' if status == PUBLISHED else 'datetime_record_updated'
        struct = {
            'status': status,
            'id': None if dry_run else av.article.manuscript_id,
            'datetime': getattr(av, attr),
            'message': "(dry-run)" if dry_run else None,
        }
        self.log_context.update(struct)
        self.log_context.pop('message')
        LOG.info("successfully %s article", status, extra=self.log_context)
        self.write(struct)

    def handle(self, *args, **options):
        action = options['action']
        msid = options['msid']
        version = options['version']
        force = options['force']
        dry_run = options['dry_run']

        data = None

        self.log_context = {
            'action': action, 'msid': msid, 'version': version, 'force?': force, 'dry_run?': dry_run
        }

        if not action:
            self.error(INVALID, "no action specified. I need either a 'ingest', 'publish' or 'ingest+publish' action")
            sys.exit(1)

        # read and check the article-json given, if necessary
        try:
            if action in [INGEST, BOTH]:
                raw_data = options['infile'].read()
                self.log_context['data'] = str(raw_data[:25]) + "... (truncated)" if raw_data else ''
                data = json.loads(raw_data)
                # vagary of the CLI interface: article id and version are required
                # these may not match the data given
                data_version = data['article']['version']
                if not data_version == version:
                    raise StateError("version in the data (%s) does not match version passed to script (%s)" % (data_version, version))
                data_msid = int(data['article']['id'].lstrip('0'))
                if not data_msid == msid:
                    raise StateError("manuscript-id in the data (%s) does not match id passed to script (%s)" % (data_msid, msid))
        except ValueError as err:
            self.error(INVALID, "could not decode the json you gave me: %r for data: %r" % (err.message, raw_data))
            sys.exit(1)

        choices = {
            # all these return a models.ArticleVersion object
            INGEST: lambda msid, ver, force, data, dry: ajson_ingestor.ingest(data, force, dry_run=dry)[-1],
            PUBLISH: lambda msid, ver, force, data, dry: ajson_ingestor.publish(msid, ver, force, dry_run=dry),
            BOTH: lambda msid, ver, force, data, dry: ajson_ingestor.ingest_publish(data, force, dry_run=dry)[-1],
        }

        try:
            av = choices[action](msid, version, force, data, dry_run)
            self.success(action, av, dry_run)

        except StateError as err:
            self.error(INVALID, "failed to call action %r: %s" % (action, err.message))
            sys.exit(1)

        except:
            LOG.exception("unhandled exception attempting to %r article", action, extra=self.log_context)
            raise

        sys.exit(0)
