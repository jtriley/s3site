from base import CmdBase


class CmdSync(CmdBase):
    """
    sync

    Sync static S3 web-site and invalidate CloudFront paths
    """
    names = ['sync', 's']

    def execute(self, args):
        pass
