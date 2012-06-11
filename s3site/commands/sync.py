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
        site_name, root_directory = args
        self.sm.sync(site_name, root_directory)
