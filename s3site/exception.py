import os

from s3site.templates import config
from s3site.logger import log


class BaseException(Exception):
    def __init__(self, *args):
        self.args = args
        self.msg = args[0]

    def __str__(self):
        return self.msg

    def explain(self):
        return "%s: %s" % (self.__class__.__name__, self.msg)


class ConfigError(BaseException):
    """Base class for all config related errors"""


class ConfigNotFound(ConfigError):
    def __init__(self, *args):
        self.msg = args[0]
        self.cfg = args[1]
        self.template = config.copy_paste_template

    def create_config(self):
        cfg_parent_dir = os.path.dirname(self.cfg)
        if not os.path.exists(cfg_parent_dir):
            os.makedirs(cfg_parent_dir)
        cfg_file = open(self.cfg, 'w')
        cfg_file.write(config.config_template)
        cfg_file.close()
        log.info("Config template written to %s" % self.cfg)
        log.info("Please customize the config template")

    def display_options(self):
        print 'Options:'
        print '--------'
        print '[1] Show the s3site config template'
        print '[2] Write config template to %s' % self.cfg
        print '[q] Quit'
        resp = raw_input('\nPlease enter your selection: ')
        if resp == '1':
            print self.template
        elif resp == '2':
            print
            self.create_config()


class ConfigSectionMissing(ConfigError):
    pass


class ConfigHasNoSections(ConfigError):
    def __init__(self, cfg_file):
        self.msg = "No valid sections defined in config file %s" % cfg_file


class S3SiteError(BaseException):
    """Base exception for all s3site related errors"""
    pass


class SiteDoesNotExist(S3SiteError):
    def __init__(self, site_name):
        self.msg = "Site '%s' does not exist" % site_name


class AWSError(BaseException):
    """Base exception for all AWS related errors"""


class BucketAlreadyExists(AWSError):
    def __init__(self, bucket_name):
        self.msg = "bucket with name '%s' already exists on S3\n" % bucket_name
        self.msg += "(NOTE: S3's bucket namespace is shared by all AWS users)"


class BucketDoesNotExist(AWSError):
    def __init__(self, bucket_name):
        self.msg = "bucket '%s' does not exist" % bucket_name


class DistributionDoesNotExist(AWSError):
    def __init__(self, id):
        self.msg = "CloudFront distribution '%s' does not exists" % id
