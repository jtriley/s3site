from base import CmdBase
from s3site.logger import log


class CmdCreate(CmdBase):
    """
    create <site_name>

    Create new static S3 web-site and CloudFront distribution
    """
    names = ['create', 'c']

    def addopts(self, parser):
        parser.add_option("-i", "--index-file", dest="index_doc",
                          action="store", default="index.html",
                          help="file to use for root index")
        parser.add_option("-e", "--error-file", dest="error_doc",
                          action="store", default="",
                          help="file to use for error page")
        parser.add_option("-c", "--cloudfront", dest="create_cf_domain",
                          action="store_true", default=False,
                          help="create a new CloudFront domain for site")
        parser.add_option("-C", "--cloudfront-cname", dest="cf_domain_cnames",
                          action="append", type="str", default=None,
                          help="CNAME to apply to CloudFront domain (this "
                          "option can be used more than once)")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a <site_name>")
        opts = self.specified_options_dict
        if 'create_cf_domain' in opts and not 'cf_domain_cnames' in opts:
            self.parser.error("The -c/--cloudfront option requires one or "
                              "more -C/--cloudfront-cname options to be "
                              "specified")
        site = self.sm.create_site(args[0], **self.specified_options_dict)
        log.info("Created new site: %s" % site.name)
