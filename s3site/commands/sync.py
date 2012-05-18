from base import CmdBase


class CmdSync(CmdBase):
    """
    sync

    Sync static S3 web-site with a local directory and invalidate CloudFront
    """
    names = ['sync']

    def execute(self, args):
        pass
