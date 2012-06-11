from base import CmdBase


class CmdList(CmdBase):
    """
    list

    List all currently configured static websites on S3
    """
    names = ['list', 'ls']

    def execute(self, args):
        self.sm.list_all_sites()
