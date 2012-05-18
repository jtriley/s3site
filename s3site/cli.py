"""
(square brackets mean optional)

  s3site [global-opts] command [command-opts] command-args
"""
import os
import sys
import shlex
import socket
import optparse
import platform
import traceback

from boto.exception import BotoServerError, EC2ResponseError, S3ResponseError

from s3site import config
from s3site import static
from s3site import logger
from s3site import commands
from s3site import exception
from s3site import optcomplete
from s3site.logger import log, console, session
from s3site import __version__

__description__ = """
s3site - (http://github.com/jtriley/s3site) (v. %s)
""" % __version__


class S3SiteCLI(object):
    """
    s3site Command Line Interface
    """
    def __init__(self):
        self._gparser = None
        self.subcmds_map = {}

    @property
    def gparser(self):
        if not self._gparser:
            self._gparser = self.create_global_parser()
        return self._gparser

    def print_header(self):
        print __description__.replace('\n', '', 1)

    def parse_subcommands(self, gparser=None):
        """
        Parse global arguments, find subcommand from list of subcommand
        objects, parse local subcommand arguments and return a tuple of
        global options, selected command object, command options, and
        command arguments.

        Call execute() on the command object to run. The command object has
        members 'gopts' and 'opts' set for global and command options
        respectively, you don't need to call execute with those but you could
        if you wanted to.
        """
        gparser = gparser or self.gparser
        # parse global options.
        gopts, args = gparser.parse_args()
        if not args:
            gparser.print_help()
            raise SystemExit("\n!!! Error: you must specify a command.")
        # set debug level if specified
        if gopts.DEBUG:
            console.setLevel(logger.DEBUG)
        # load s3site config object into global options
        try:
            cfg = config.S3SiteConfig(gopts.CONFIG)
            cfg.load()
        except exception.ConfigNotFound, e:
            log.error(e.msg)
            e.display_options()
            sys.exit(1)
        except exception.ConfigError, e:
            log.error(e.msg)
            sys.exit(1)
        gopts.CONFIG = cfg
        # Parse command arguments and invoke command.
        subcmdname, subargs = args[0], args[1:]
        try:
            sc = self.subcmds_map[subcmdname]
            lparser = optparse.OptionParser(sc.__doc__.strip())
            sc.gopts = gopts
            sc.parser = lparser
            sc.gparser = gparser
            sc.subcmds_map = self.subcmds_map
            sc.addopts(lparser)
            sc.opts, subsubargs = lparser.parse_args(subargs)
        except KeyError:
            raise SystemExit("Error: invalid command '%s'" % subcmdname)
        return gopts, sc, sc.opts, subsubargs

    def create_global_parser(self, subcmds=None, no_usage=False,
                             add_help=True):
        if no_usage:
            gparser = optparse.OptionParser(usage=optparse.SUPPRESS_USAGE,
                                            add_help_option=add_help)
        else:
            gparser = optparse.OptionParser(__doc__.strip(),
                                            version=__version__,
                                            add_help_option=add_help)
            subcmd_descriptions = ''
            subcmds = subcmds or commands.all_cmds
            # Build map of name -> command and docstring.
            for sc in subcmds:
                helptxt = sc.__doc__.splitlines()[3].strip()
                description = '- %s: %s\n' % (', '.join(sc.names), helptxt)
                subcmd_descriptions += description
                for n in sc.names:
                    assert n not in self.subcmds_map
                    self.subcmds_map[n] = sc
            max_len = len(max(subcmd_descriptions.splitlines()))
            cmds_header = 'Commands: (pass --help to any command for '
            cmds_header += 'detailed usage)'
            gparser.usage += '\n\n%s\n' % cmds_header
            gparser.usage += '%s\n' % ('-' * max_len)
            gparser.usage += subcmd_descriptions
            gparser.usage += '%s\n' % ('-' * max_len)
            gparser.usage = gparser.usage.strip()
        gparser.add_option("-d", "--debug", dest="DEBUG",
                           action="store_true", default=False,
                           help="print debug messages (useful for "
                           "diagnosing problems)")
        gparser.add_option("-c", "--config", dest="CONFIG", action="store",
                           metavar="FILE",
                           help="use alternate config file (default: %s)" %
                           static.S3SITE_CFG_FILE)
        gparser.disable_interspersed_args()
        return gparser

    def __write_module_version(self, modname, fp):
        """
        Write module version information to a file
        """
        try:
            mod = __import__(modname)
            fp.write("%s: %s\n" % (mod.__name__, mod.__version__))
        except Exception, e:
            print "error getting version for '%s' module: %s" % (modname, e)

    def bug_found(self):
        """
        Builds a crash-report when s3site encounters an unhandled
        exception. Report includes system info, python version, dependency
        versions, and a full debug log and stack-trace of the crash.
        """
        dashes = '-' * 10
        header = dashes + ' %s ' + dashes + '\n'
        crashfile = open(static.CRASH_FILE, 'w')
        crashfile.write(header % "CRASH DETAILS")
        argv = sys.argv[:]
        argv[0] = os.path.basename(argv[0])
        argv = ' '.join(argv)
        crashfile.write('COMMAND: %s\n' % argv)
        crashfile.write(session.stream.getvalue())
        crashfile.write(header % "SYSTEM INFO")
        crashfile.write("s3site: %s\n" % __version__)
        crashfile.write("Python: %s\n" % sys.version.replace('\n', ' '))
        crashfile.write("Platform: %s\n" % platform.platform())
        dependencies = ['boto']
        for dep in dependencies:
            self.__write_module_version(dep, crashfile)
        crashfile.close()
        log.error("Oops! Looks like you've found a bug in s3site")
        log.error("Crash report written to: %s" % static.CRASH_FILE)
        sys.exit(1)

    def get_global_opts(self):
        """
        Parse and return global options. This method will silently return None
        if any errors are encountered during parsing.
        """
        gparser = self.create_global_parser(no_usage=True, add_help=False)
        try:
            sys.stdout = open(os.devnull, 'w')
            sys.stderr = open(os.devnull, 'w')
            gopts, _ = gparser.parse_args()
            return gopts
        except SystemExit:
            pass
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

    def is_completion_active(self):
        return 'OPTPARSE_AUTO_COMPLETE' in os.environ

    def _init_completion(self):
        """
        Restore original sys.argv from COMP_LINE in the case that s3site
        is being called by Bash/ZSH for completion options. Bash/ZSH will
        simply call 's3site' with COMP_LINE environment variable set to
        the current (partial) argv for completion.

        s3site's Bash/ZSH completion code needs to read the global config
        option in case an alternate config is specified at the command line
        when completing options. s3site's completion code uses the config
        to generate completion options. Setting sys.argv to $COMP_LINE in this
        case allows the global option parser to be used to extract the global
        -c option (if specified) and load the proper config in the completion
        code.
        """
        if 'COMP_LINE' in os.environ:
            newargv = shlex.split(os.environ.get('COMP_LINE'))
            for i, arg in enumerate(newargv):
                arg = os.path.expanduser(arg)
                newargv[i] = os.path.expandvars(arg)
            sys.argv = newargv

    def handle_completion(self):
        if self.is_completion_active():
            gparser = self.create_global_parser(no_usage=True, add_help=False)
            # set sys.path to COMP_LINE if it exists
            self._init_completion()
            # fetch the global options
            gopts = self.get_global_opts()
            # try to load s3siteConfig into global options
            if gopts:
                try:
                    cfg = config.S3SiteConfig(gopts.CONFIG)
                    cfg.load()
                except exception.ConfigError:
                    cfg = None
                gopts.CONFIG = cfg
            scmap = {}
            for sc in commands.all_cmds:
                sc.gopts = gopts
                for n in sc.names:
                    scmap[n] = sc
            listcter = optcomplete.ListCompleter(scmap.keys())
            subcter = optcomplete.NoneCompleter()
            optcomplete.autocomplete(gparser, listcter, None, subcter,
                                     subcommands=scmap)
            sys.exit(1)

    def main(self):
        """
        s3site main
        """
        # Handle Bash/ZSH completion if necessary
        self.handle_completion()
        # Show s3site header
        self.print_header()
        # Parse subcommand options and args
        gopts, sc, opts, args = self.parse_subcommands()
        if args and args[0] == 'help':
            # make 'help' subcommand act like --help option
            sc.parser.print_help()
            sys.exit(0)
        # run the subcommand and handle exceptions
        try:
            sc.execute(args)
        except (EC2ResponseError, S3ResponseError, BotoServerError), e:
            log.error("%s: %s" % (e.error_code, e.error_message))
            sys.exit(1)
        except socket.error, e:
            log.error("Unable to connect: %s" % e)
            log.error("Check your internet connection?")
            sys.exit(1)
        except exception.BaseException, e:
            log.error(e.msg, extra={'__textwrap__': True})
            sys.exit(1)
        except SystemExit:
            # re-raise SystemExit to avoid the bug-catcher below
            raise
        except Exception:
            if not gopts.DEBUG:
                traceback.print_exc()
            log.debug(traceback.format_exc())
            print
            self.bug_found()


def main():
    static.create_config_dirs()
    logger.configure_s3site_logging()
    S3SiteCLI().main()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print "Interrupted, exiting."
