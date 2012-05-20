import sys

import s3site
from s3site import utils
from s3site.logger import log

from base import CmdBase


class CmdShell(CmdBase):
    """
    shell

    Load an interactive IPython shell configured for s3site
    """

    names = ['shell', 'sh']

    def addopts(self, parser):
        pass

    def execute(self, args):
        local_ns = dict(cfg=self.cfg, s3site=s3site, s3=self.s3, cf=self.cf,
                        log=log)
        modules = [(s3site.__name__ + '.' + module, module)
                   for module in s3site.__all__]
        modules += [('boto', 'boto')]
        for fullname, modname in modules:
            log.info('Importing module %s' % modname)
            try:
                __import__(fullname)
                local_ns[modname] = sys.modules[fullname]
            except ImportError, e:
                log.error("Error loading module %s: %s" % (modname, e))
        utils.ipy_shell(local_ns=local_ns)
