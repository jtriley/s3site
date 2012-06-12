import os

from s3site import exception
from base import CmdBase


class CmdSync(CmdBase):
    """
    sync <site_name> <root_directory>

    Sync static S3 web-site and invalidate CloudFront paths
    """
    names = ['sync', 's']

    def execute(self, args):
        if len(args) != 2:
            self.parser.error(
                'please specify a <site_name> and <root_directory>')
        site_name, rootdir = args
        if not os.path.isdir(rootdir):
            raise exception.BaseException("'%s' is not a directory" % rootdir)
        self.sm.sync(site_name, rootdir)
