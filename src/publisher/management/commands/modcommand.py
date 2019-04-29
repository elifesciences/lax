import os
from django.core.management.base import CommandParser
from django.core.management.base import BaseCommand
import logging

LOG = logging.getLogger(__name__)


class ModCommand(BaseCommand):
    def create_parser(self, prog_name, subcommand):
        """
        Create and return the ``ArgumentParser`` which will be used to
        parse the arguments to this command.
        """
        parser = CommandParser(
            self,
            prog="%s %s" % (os.path.basename(prog_name), subcommand),
            description=self.help or None,
        )
        # parser.add_argument('--version', action='version', version=self.get_version())
        parser.add_argument(
            "-v",
            "--verbosity",
            action="store",
            dest="verbosity",
            default=1,
            type=int,
            choices=[0, 1, 2, 3],
            help="Verbosity level; 0=minimal output, 1=normal output, 2=verbose output, 3=very verbose output",
        )
        parser.add_argument(
            "--settings",
            help=(
                "The Python path to a settings module, e.g. "
                '"myproject.settings.main". If this isn\'t provided, the '
                "DJANGO_SETTINGS_MODULE environment variable will be used."
            ),
        )
        parser.add_argument(
            "--pythonpath",
            help='A directory to add to the Python path, e.g. "/home/djangoprojects/myproject".',
        )
        parser.add_argument(
            "--traceback", action="store_true", help="Raise on CommandError exceptions"
        )
        parser.add_argument(
            "--no-color",
            action="store_true",
            dest="no_color",
            default=False,
            help="Don't colorize the command output.",
        )
        self.add_arguments(parser)
        return parser
