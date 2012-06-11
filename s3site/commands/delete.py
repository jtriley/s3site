from base import CmdBase


class CmdDelete(CmdBase):
    """
    delete <site_name>

    Delete a static website on S3 and its CloudFront distribution
    """
    names = ['delete', 'd']

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a <site_name>")
        self.sm.delete_site(args[0])
