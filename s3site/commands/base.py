import os
import sys
import time
import signal
from s3site import optcomplete
from s3site.logger import log


class CmdBase(optcomplete.CmdComplete):
    """
    Base class for s3site commands

    Each command consists of a class, which has the following properties:

    - Must have a class member 'names' which is a list of the names for
    the command

    - Can optionally define an addopts(self, parser) method which adds options
    to the given parser. This defines the command's options.
    """
    parser = None
    opts = None
    gopts = None
    gparser = None
    subcmds_map = None
    _cfg = None
    _s3 = None
    _cf = None
    _cm = None
    _nm = None

    @property
    def comp_words(self):
        """
        Property that returns COMP_WORDS from Bash/Zsh completion
        """
        return os.environ.get('COMP_WORDS', '').split()

    @property
    def goptions_dict(self):
        """
        Returns global options dictionary
        """
        return dict(self.gopts.__dict__)

    @property
    def options_dict(self):
        """
        Returns dictionary of options for this command
        """
        return dict(self.opts.__dict__)

    @property
    def specified_options_dict(self):
        """
        Return only those options with a non-None value
        """
        specified = {}
        options = self.options_dict
        for opt in options:
            if options[opt] is not None:
                specified[opt] = options[opt]
        return specified

    @property
    def log(self):
        return log

    @property
    def cfg(self):
        """
        Get global s3siteConfig object
        """
        if not self._cfg:
            self._cfg = self.goptions_dict.get('CONFIG')
        return self._cfg

    @property
    def s3(self):
        if not self._s3:
            self._s3 = self.cfg.get_easy_s3()
        return self._s3

    @property
    def cf(self):
        if not self._cf:
            self._cf = self.cfg.get_easy_cf()
        return self._cf

    def addopts(self, parser):
        pass

    def cancel_command(self, signum, frame):
        """
        Exits program with return value of 1
        """
        print
        log.info("Exiting...")
        sys.exit(1)

    def catch_ctrl_c(self, handler=None):
        """
        Catch ctrl-c interrupt
        """
        handler = handler or self.cancel_command
        signal.signal(signal.SIGINT, handler)

    def warn_experimental(self, msg, num_secs=10):
        """
        Warn user that an experimental feature is being used
        Counts down from num_secs before continuing
        """
        sep = '*' * 60
        log.warn('\n'.join([sep, msg, sep]), extra=dict(__textwrap__=True))
        r = range(1, num_secs + 1)
        r.reverse()
        print
        log.warn("Waiting %d seconds before continuing..." % num_secs)
        log.warn("Press CTRL-C to cancel...")
        for i in r:
            sys.stdout.write('%d...' % i)
            sys.stdout.flush()
            time.sleep(1)
        print

    def _positive_int(self, option, opt_str, value, parser):
        if value <= 0:
            parser.error("option %s must be a positive integer" % opt_str)
        setattr(parser.values, option.dest, value)

    def _build_dict(self, option, opt_str, value, parser):
        tagdict = getattr(parser.values, option.dest)
        tags = value.split(',')
        for tag in tags:
            tagparts = tag.split('=')
            key = tagparts[0]
            if not key:
                continue
            value = None
            if len(tagparts) == 2:
                value = tagparts[1]
            tagstore = tagdict.get(key)
            if isinstance(tagstore, basestring) and value:
                tagstore = [tagstore, value]
            elif isinstance(tagstore, list) and value:
                tagstore.append(value)
            else:
                tagstore = value
            tagdict[key] = tagstore
        setattr(parser.values, option.dest, tagdict)
