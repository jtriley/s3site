"""
Module for storing static data structures
"""
import os
import sys


VERSION = 0.9999
PID = os.getpid()

S3SITE_CFG_DIR = os.path.join(os.path.expanduser('~'), '.s3site')
S3SITE_CFG_FILE = os.path.join(S3SITE_CFG_DIR, 'config')
S3SITE_LOG_DIR = os.path.join(S3SITE_CFG_DIR, 'logs')
S3SITE_META_FILE = '__s3site.cfg'
DEBUG_FILE = os.path.join(S3SITE_LOG_DIR, 'debug.log')
AWS_DEBUG_FILE = os.path.join(S3SITE_LOG_DIR, 'aws-debug.log')
CRASH_FILE = os.path.join(S3SITE_LOG_DIR, 'crash-report-%d.txt' % PID)

GLOBAL_SETTINGS = {
    # setting, type, required?, default, options, callback
    'enable_experimental': (bool, False, False, None, None),
    'web_browser': (str, False, None, None, None),
    'include': (list, False, [], None, None),
}

AWS_SETTINGS = {
    'aws_access_key_id': (str, True, None, None, None),
    'aws_secret_access_key': (str, True, None, None, None),
    'aws_user_id': (str, False, None, None, None),
    'aws_port': (int, False, None, None, None),
    'aws_ec2_path': (str, False, '/', None, None),
    'aws_s3_path': (str, False, '/', None, None),
    'aws_is_secure': (bool, False, True, None, None),
    'aws_region_name': (str, False, None, None, None),
    'aws_region_host': (str, False, None, None, None),
    'aws_s3_host': (str, False, None, None, None),
    'aws_proxy': (str, False, None, None, None),
    'aws_proxy_port': (int, False, None, None, None),
    'aws_proxy_user': (str, False, None, None, None),
    'aws_proxy_pass': (str, False, None, None, None),
}


def __expand_all(path):
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    return path


def __makedirs(path, exit_on_failure=False):
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except OSError:
            if exit_on_failure:
                sys.stderr.write("!!! ERROR - %s *must* be a directory\n" %
                                 path)
    elif not os.path.isdir(path) and exit_on_failure:
        sys.stderr.write("!!! ERROR - %s *must* be a directory\n" % path)
        sys.exit(1)


def create_config_dirs():
    __makedirs(S3SITE_CFG_DIR, exit_on_failure=True)
    __makedirs(S3SITE_LOG_DIR)
