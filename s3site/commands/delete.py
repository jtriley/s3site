from base import CmdBase


class CmdDelete(CmdBase):
    """
    delete

    Delete a static website on S3 and its CloudFront distribution
    """
    names = ['delete']

    def execute(self, args):
        pass
