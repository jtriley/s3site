from base import CmdBase


class CmdClone(CmdBase):
    """
    clone <site_name>

    Download a static S3 web-site to a local directory
    """
    names = ['clone', 'cl']

    def addopts(self, parser):
        parser.add_option("-o", "--output-dir", dest="output_dir",
                          action="store", default=None,
                          help="use an output directory other than the "
                          "current working directory")

    def execute(self, args):
        if len(args) != 1:
            self.parser.error("please specify a <site_name>")
        site_name = args[0]
        self.sm.clone_site(site_name, **self.specified_options_dict)
