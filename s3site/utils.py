"""
Utils module for s3site
"""
import os
import glob
import hashlib
import urlparse

from s3site.logger import log

try:
    import IPython
    if IPython.__version__ < '0.11':
        from IPython.Shell import IPShellEmbed
        ipy_shell = IPShellEmbed(argv=[])
    else:
        from IPython import embed
        ipy_shell = lambda local_ns=None: embed(user_ns=local_ns)
except ImportError, e:

    def ipy_shell(local_ns=None):
        log.error("Unable to load IPython:\n\n%s\n" % e)
        log.error("Please check that IPython is installed and working.")
        log.error("If not, you can install it via: easy_install ipython")

try:
    import pudb
    set_trace = pudb.set_trace
except ImportError:

    def set_trace():
        log.error("Unable to load PuDB")
        log.error("Please check that PuDB is installed and working.")
        log.error("If not, you can install it via: easy_install pudb")


def is_url(url):
    """
    Returns True if the provided string is a valid url
    """
    try:
        parts = urlparse.urlparse(url)
        scheme = parts[0]
        netloc = parts[1]
        if scheme and netloc:
            return True
        else:
            return False
    except:
        return False


class AttributeDict(dict):
    """
    Subclass of dict that allows read-only attribute-like access to
    dictionary key/values
    """
    def __getattr__(self, name):
        try:
            return self.__getitem__(name)
        except KeyError:
            return super(AttributeDict, self).__getattribute__(name)


def find_files(path):
    for cfile in glob.glob(os.path.join(path, '*')):
        if os.path.isdir(cfile):
            for py in find_files(cfile):
                yield py
        else:
            yield cfile


def compute_md5(path):
    md5 = hashlib.md5()
    f = open(path)
    while True:
        data = f.read(8192)
        if not data:
            break
        md5.update(data)
    return md5.hexdigest()
