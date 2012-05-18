from base import CmdBase


class CmdList(CmdBase):
    """
    list

    List all currently configured static websites on S3
    """
    names = ['list']

    def execute(self, args):
        pass
