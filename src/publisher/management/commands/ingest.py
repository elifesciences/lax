"""
the `ingest` script is distinct from the `import` script.

The import script does not obey business rules and merrily update published dates and so on without concern. It is good for bulk imports, development and once-off patching of article data.

The ingest script DOES obey business rules and will not publish things twice,

"""
from collections import OrderedDict
import io, re, sys, json, argparse
from publisher import ajson_ingestor, utils, codes, aws_events
from publisher.aws_events import START, STOP
from publisher.utils import lfilter, formatted_traceback as ftb
from publisher.ajson_ingestor import StateError
import logging
from joblib import Parallel, delayed
from django.db import reset_queries
import os
from .modcommand import ModCommand
import time
LOG = logging.getLogger(__name__)

INVALID, ERROR = 'invalid', 'error'
IMPORT_TYPES = ['ingest', 'publish', 'ingest-publish']
INGEST, PUBLISH, INGEST_PUBLISH = IMPORT_TYPES
VALIDATED, INGESTED, PUBLISHED = 'validated', 'ingested', 'published'

def write(print_queue, out=None):
    if not isinstance(out, str):
        out = utils.json_dumps(out) # encodes datetime objects
    print_queue.put(out)

def clean_up(print_queue):
    print_queue.put('STOP')
    reset_queries()

def error(print_queue, errtype, code, message, force, dry_run, log_context, **moar):
    struct = OrderedDict([
        ('status', errtype), # final status of request (ingested, published, validated, invalid, error)

        ('code', code), # the error classification (bad request, unknown, parse error, etc)
        ('comment', codes.explain(code)), # a generic explanation about the error code

        ('message', message), # an explanation of the actual error

        ('trace', None), # optional tracing information. if validation error, it should be error and it's context

        ('dry-run', dry_run),
        ('force', force),

    ])
    struct.update(moar)
    log_context['status'] = errtype
    LOG.error(message, extra=log_context)
    write(print_queue, struct)
    clean_up(print_queue)
    sys.exit(1)

def error_from_err(print_queue, errtype, errobj, force, dry_run, log_context):
    return error(print_queue, errtype, errobj.code, errobj.message, force, dry_run, log_context, trace=errobj.trace)

def success(print_queue, action, av, force, dry_run, log_context):
    lu = {
        INGEST: INGESTED,
        PUBLISH: PUBLISHED,
        INGEST_PUBLISH: PUBLISHED,
    }
    status = orig_status = lu[action]
    if dry_run:
        # this is a dry run, we didn't actually ingest or publish anything
        status = VALIDATED

    attr = 'datetime_published' if orig_status == PUBLISHED else 'datetime_record_updated'
    struct = OrderedDict([
        ('status', status),
        ('id', log_context['msid']), # good idea? #'id': None if dry_run else av.article.manuscript_id,
        ('datetime', getattr(av, attr)),
        ('dry-run', dry_run),
        ('force', force),

        # backwards compatibility while bot-lax catches up
        ('message', None),
    ])
    log_context.update(struct)
    # if a 'message' key is present, we need to remove it to avoid
    #     KeyError: "Attempt to overwrite 'message' in LogRecord"
    log_context.pop('message')
    LOG.info("successfully %s article %s v%s", status, log_context['msid'], log_context['version'], extra=log_context)
    write(print_queue, struct)
    clean_up(print_queue)
    sys.exit(0)

def handle_single(print_queue, action, infile, msid, version, force, dry_run):
    data = None

    log_context = {
        'msid': msid, 'version': version
    }

    LOG.info('attempting to %s article %s v%s', action, msid, version, extra=log_context)

    # read and check the article-json given, if necessary
    try:
        if action not in [PUBLISH]:
            raw_data = infile.read()
            log_context['data'] = str(raw_data[:25]) + "... (truncated)" if raw_data else ''

            try:
                data = json.loads(raw_data)
            except ValueError as err:
                msg = "could not decode the json you gave me: %r for data: %r" % (err.msg, raw_data)
                raise StateError(codes.BAD_REQUEST, msg)

            # vagary of the CLI interface: article id and version are required
            # these may not match the data given
            data_version = data['article'].get('version')
            if not data_version == version:
                raise StateError(codes.BAD_REQUEST, "'version' in the data (%s) does not match 'version' passed to script (%s)" % (data_version, version))
            data_msid = int(data['article']['id'])
            if not data_msid == msid:
                raise StateError(codes.BAD_REQUEST, "'id' in the data (%s) does not match 'msid' passed to script (%s)" % (data_msid, msid))

    except KeyboardInterrupt as err:
        LOG.warn("ctrl-c caught during data load")
        raise

    except StateError as err:
        error_from_err(print_queue, INVALID, err, force, dry_run, log_context)

    except BaseException as err:
        LOG.exception("unhandled exception attempting to ingest article-json", extra=log_context)
        error(print_queue, ERROR, codes.UNKNOWN, str(err), force, dry_run, log_context, trace=ftb(err))

    choices = {
        # all these return a models.ArticleVersion object
        INGEST: lambda msid, ver, force, data, dry: ajson_ingestor.ingest(data, force, dry_run=dry),
        PUBLISH: lambda msid, ver, force, data, dry: ajson_ingestor.publish(msid, ver, force, dry_run=dry),
        INGEST_PUBLISH: lambda msid, ver, force, data, dry: ajson_ingestor.ingest_publish(data, force, dry_run=dry),
    }

    try:
        av = choices[action](msid, version, force, data, dry_run)
        success(print_queue, action, av, force, dry_run, log_context)

    except KeyboardInterrupt as err:
        LOG.warn("ctrl-c caught during ingest/publish")
        raise

    except SystemExit:
        # `success` and `error` use `exit` to indicate success or failure with their return code.
        # this is handled in the `job` function, so re-raise it here and handle it there
        raise

    except StateError as err:
        # handled error
        error_from_err(print_queue, INVALID, err, force, dry_run, log_context)

    except BaseException as err:
        # unhandled error
        msg = "unhandled exception attempting to %r article: %r" % (action, err)
        LOG.exception(msg, extra=log_context)
        error(print_queue, ERROR, codes.UNKNOWN, msg, force, dry_run, log_context, trace=ftb(err))


def job(print_queue, action, path, force, dry_run):
    try:
        msid, version = utils.version_from_path(path)
        handle_single(print_queue, action, io.open(path, 'r', encoding='utf8'), msid, version, force, dry_run)
        return 0

    except KeyboardInterrupt:
        LOG.warn("ctrl-c caught. use ctrl-c again to quit to sending notifications")
        try:
            time.sleep(3)
        except KeyboardInterrupt:
            raise

    except SystemExit as err:
        LOG.debug("system exit caught", extra={'msid': msid, 'version': version})
        return err.code

def json_files(print_queue, path):
    json_files = utils.resolve_path(path)
    cregex = re.compile(r'^.*/elife-\d{5,}-v\d\.xml\.json$')
    ajson_file_list = lfilter(cregex.match, json_files)
    if not ajson_file_list:
        LOG.info("found no article json at %r" % os.path.abspath(path))
        clean_up(print_queue)
        sys.exit(0) # successfully did nothing
    return ajson_file_list

def handle_many_concurrently(print_queue, action, path, force, dry_run):
    try:
        ajson_file_list = json_files(print_queue, path)
        aws_events.notify(STOP) # defer sending notifications
        # order cannot be guaranteed
        Parallel(n_jobs=-1)(delayed(job)(print_queue, action, path, force, dry_run) for path in ajson_file_list) # pylint: disable=unexpected-keyword-arg
        clean_up(print_queue)
        sys.exit(0) # TODO: return with num failed
    finally:
        aws_events.notify(START) # resume sending notifications, process outstanding

def handle_many_serially(print_queue, action, path, force, dry_run):
    try:
        ajson_file_list = sorted(json_files(print_queue, path)) # ASC
        aws_events.notify(STOP) # defer sending notifications
        num_failed = sum([job(print_queue, action, path, force, dry_run) for path in ajson_file_list])
        clean_up(print_queue)
        sys.exit(num_failed)
    finally:
        aws_events.notify(START) # resume sending notifications, process outstanding


class Command(ModCommand):
    help = ''

    def add_arguments(self, parser):
        parser.add_argument('--id', dest='msid', type=int)
        parser.add_argument('--version', dest='version', type=int)
        parser.add_argument('--dir', dest='dir')
        parser.add_argument('--force', action='store_true', default=False)
        parser.add_argument('--dry-run', action='store_true', default=False)

        parser.add_argument('--serial', action='store_true', default=False)

        # might remove this and hide the implementation details in bot-lax ...
        parser.add_argument('--ingest', dest='action', action='store_const', const=INGEST)
        parser.add_argument('--publish', dest='action', action='store_const', const=PUBLISH)
        parser.add_argument('--ingest+publish', dest='action', action='store_const', const=INGEST_PUBLISH)

        parser.add_argument('infile', nargs='?', type=argparse.FileType('r'), default=sys.stdin)

        self.parser = parser

    def invalid_args(self, message):
        self.parser.error(message)
        sys.exit(1)

    def handle(self, *args, **options):
        action = options['action']
        force = options['force']
        dry_run = options['dry_run']

        # single options:
        msid = options['msid']
        version = options['version']

        # many options:
        path = options['dir']
        serial = options['serial']

        self.log_context = {
            'action': action, 'force?': force, 'dry_run?': dry_run
        }

        if not action:
            self.invalid_args("no action specified. I need either a 'ingest', 'publish' or 'ingest+publish' action")

        if serial:
            import queue
            print_queue = queue.Queue()

        else:
            import multiprocessing
            manager = multiprocessing.Manager()
            print_queue = manager.Queue()

        try:
            if path:
                if options['msid'] or options['version']:
                    self.invalid_args("the 'id' and 'version' options are not required when a 'dir' option is passed")

                if not os.path.isdir(path):
                    self.invalid_args("the 'dir' option must point to a directory. got %r" % path)

                fn = handle_many_serially if serial else handle_many_concurrently
                fn(print_queue, action, path, force, dry_run)

            else:
                if not (options['msid'] and options['version']):
                    self.invalid_args("the 'id' and 'version' options are both required when a 'dir' option is not passed")

                handle_single(print_queue, action, options['infile'], msid, version, force, dry_run)

        except KeyboardInterrupt:
            LOG.info("ctrl-c caught somewhere, printing buffer")

        except Exception as err:
            LOG.exception("unhandled exception!")
            error(print_queue, ERROR, codes.UNKNOWN, str(err), force, dry_run, self.log_context, trace=ftb(err))

        finally:
            self.stdout.write('+' * 20)
            for msg in iter(print_queue.get, 'STOP'):
                self.stdout.write(msg)
            self.stdout.write('+' * 20)
            self.stdout.flush()
