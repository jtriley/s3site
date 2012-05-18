from create import CmdCreate
from sync import CmdSync
from list import CmdList
from clone import CmdClone
from delete import CmdDelete
from shell import CmdShell
from help import CmdHelp

all_cmds = [
    CmdCreate(),
    CmdSync(),
    CmdList(),
    CmdClone(),
    CmdDelete(),
    CmdShell(),
    CmdHelp(),
]
