from s3site import static

__version__ = static.VERSION
__author__ = "Justin Riley (justin.t.riley@gmail.com)"
__all__ = [
    "config",
    "static",
    "cli",
    "commands",
    "logger",
    "utils",
    "exception",
    "templates",
    "tests",
    "optcomplete",
    "progressbar",
    "spinner",
]


def test():
    try:
        from nose.core import TestProgram
        TestProgram(argv=[__file__, "s3site.tests", '-s'], exit=False)
    except ImportError:
        print 'error importing nose'

test.__test__ = False
