import pprint
from django.core.management.base import BaseCommand
from django.db import transaction
from publisher import logic, ejp_ingestor, utils
from publisher.utils import lmap
from functools import partial
import logging

LOG = logging.getLogger(__name__)

IMPORT_TYPES = ["ejp"]
EJP = IMPORT_TYPES[0]


def ingest(fn, journal, create, update, path_list):
    "wrapper around the import function with friendlier handling of problems"

    def _(path):
        try:
            results = fn(journal, path, create=create, update=update)
            LOG.debug("results of ingest", extra={"results": results})
            return True
        except KeyboardInterrupt:
            raise
        except BaseException:
            LOG.exception("failed to import article")
            return False

    try:
        lmap(_, path_list)
    except KeyboardInterrupt:
        print("caught interrupt")
        exit(1)


class Command(BaseCommand):
    help = """
    The `import` command imports article data from different sources, default to an EIF source.

    This command supercedes the `import_article` and `import_ejp_article` commands.

    Lax requires all data sources to be JSON encoded.

    To specify the type of import to be performed, use the `--import-type` parameter.

    A single JSON file or a directory of JSON may be passed in as the `--path` paramater.
    Directories of files will have their contents expanded and only JSON files will be used.

    To only create articles and never update an article, use the `--no-update` parameter.

    To only update articles and never create articles, use the `--no-create` parameter.

    To neither create nor update (a dry run), use both `--no-create` and `--no-update` parameters."""

    def add_arguments(self, parser):
        # where am I to look?
        parser.add_argument("path", type=str)

        # create articles that don't exist?
        parser.add_argument("--no-create", action="store_false", default=True)

        # update articles that already exist?
        parser.add_argument("--no-update", action="store_false", default=True)

        # indicate the type of import we should be doing
        parser.add_argument(
            "--import-type", required=True, type=str, choices=IMPORT_TYPES
        )

        # don't prompt, don't pretty-print anything, just do it.
        parser.add_argument("--just-do-it", action="store_true", default=False)

        # do the import within a transaction - default. makes sqlite fly
        parser.add_argument("--no-atomic", action="store_false", default=True)

    def handle(self, *args, **options):
        path = options["path"]
        create_articles = options["no_create"]
        update_articles = options["no_update"]
        import_type = options["import_type"]
        atomic = options["no_atomic"]

        path_list = utils.resolve_path(path)

        if not options["just_do_it"]:
            try:
                pprint.pprint(path_list)
                print(import_type.upper(), "import of", len(path_list), "files")
                print("create?", create_articles)
                print("update?", update_articles)
                input("continue? (ctrl-c to exit)")
            except KeyboardInterrupt:
                exit(0)

        choices = {EJP: ejp_ingestor.import_article_list_from_json_path}
        fn = partial(
            ingest,
            choices[import_type],
            logic.journal(),
            create_articles,
            update_articles,
            path_list,
        )
        if atomic:
            with transaction.atomic():
                fn()
        else:
            fn()
        exit(0)
