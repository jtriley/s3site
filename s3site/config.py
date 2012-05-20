import os
import urllib
import StringIO
import ConfigParser

from s3site import utils
from s3site import static
from s3site import awsutils
from s3site import exception
from s3site.logger import log

DEBUG_CONFIG = False


def get_config(config_file=None, cache=False):
    """Factory for StarClusterConfig object"""
    return S3SiteConfig(config_file, cache).load()


def get_easy_s3(config_file=None, cache=False):
    """
    Factory for EasyS3 class that attempts to load AWS credentials from
    the StarCluster config file. Returns an EasyS3 object if
    successful.
    """
    cfg = get_config(config_file, cache)
    return cfg.get_easy_s3()

def get_easy_cf(config_file=None, cache=False):
    """
    Factory for EasyS3 class that attempts to load AWS credentials from
    the StarCluster config file. Returns an EasyS3 object if
    successful.
    """
    cfg = get_config(config_file, cache)
    return cfg.get_easy_cf()


class S3SiteConfig(object):
    """
    S3Site Config Parser

    cfg = S3SiteConfig('/path/to/my/config.cfg').load()
    """
    global_settings = static.GLOBAL_SETTINGS
    aws_settings = static.AWS_SETTINGS

    def __init__(self, config_file=None, cache=False):
        self.cfg_file = config_file or static.S3SITE_CFG_FILE
        self.cfg_file = os.path.expanduser(self.cfg_file)
        self.cfg_file = os.path.expandvars(self.cfg_file)
        self.type_validators = {
            int: self._get_int,
            float: self._get_float,
            str: self._get_string,
            bool: self._get_bool,
            list: self._get_list,
        }
        self._config = None

    def __repr__(self):
        return "<S3SiteConfig: %s>" % self.cfg_file

    def _get_urlfp(self, url):
        log.debug("Loading url: %s" % url)
        try:
            fp = urllib.urlopen(url)
            if fp.getcode() == 404:
                raise exception.ConfigError("url %s does not exist" % url)
            fp.name = url
            return fp
        except IOError, e:
            raise exception.ConfigError(
                "error loading config from url %s\n%s" % (url, e))

    def _get_fp(self, cfg_file):
        log.debug("Loading file: %s" % cfg_file)
        if os.path.exists(cfg_file):
            if not os.path.isfile(cfg_file):
                raise exception.ConfigError(
                    'config %s exists but is not a regular file' % cfg_file)
        else:
            raise exception.ConfigNotFound("config file %s does not exist\n" %
                                           cfg_file, cfg_file)
        return open(cfg_file)

    def _get_cfg_fp(self, cfg_file=None):
        cfg = cfg_file or self.cfg_file
        if utils.is_url(cfg):
            return self._get_urlfp(cfg)
        else:
            return self._get_fp(cfg)

    def _get_bool(self, config, section, option):
        try:
            opt = config.getboolean(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass
        except ValueError:
            raise exception.ConfigError(
                "Expected True/False value for setting %s in section [%s]" %
                (option, section))

    def _get_int(self, config, section, option):
        try:
            opt = config.getint(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass
        except ValueError:
            raise exception.ConfigError(
                "Expected integer value for setting %s in section [%s]" %
                (option, section))

    def _get_float(self, config, section, option):
        try:
            opt = config.getfloat(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass
        except ValueError:
            raise exception.ConfigError(
                "Expected float value for setting %s in section [%s]" %
                (option, section))

    def _get_string(self, config, section, option):
        try:
            opt = config.get(section, option)
            return opt
        except ConfigParser.NoSectionError:
            pass
        except ConfigParser.NoOptionError:
            pass

    def _get_list(self, config, section, option):
        val = self._get_string(config, section, option)
        if val:
            val = [v.strip() for v in val.split(',')]
        return val

    def __load_config(self):
        """
        Populates self._config with a new ConfigParser instance
        """
        cfg = self._get_cfg_fp()
        try:
            cp = ConfigParser.ConfigParser()
            cp.readfp(cfg)
            self._config = cp
            try:
                self.globals = self._load_section('global',
                                                  self.global_settings)
                includes = self.globals.get('include')
                if not includes:
                    return cp
                mashup = StringIO.StringIO()
                cfg = self._get_cfg_fp()
                mashup.write(cfg.read() + '\n')
                for include in includes:
                    include = os.path.expanduser(include)
                    include = os.path.expandvars(include)
                    try:
                        contents = self._get_cfg_fp(include).read()
                        mashup.write(contents + '\n')
                    except exception.ConfigNotFound:
                        raise exception.ConfigError("include %s not found" %
                                                    include)
                mashup.seek(0)
                cp = ConfigParser.ConfigParser()
                cp.readfp(mashup)
                self._config = cp
            except exception.ConfigSectionMissing:
                pass
            return cp
        except ConfigParser.MissingSectionHeaderError:
            raise exception.ConfigHasNoSections(cfg.name)
        except ConfigParser.ParsingError, e:
            raise exception.ConfigError(e)

    def reload(self):
        """
        Reloads the configuration file
        """
        self.__load_config()
        return self.load()

    @property
    def config(self):
        if self._config is None:
            self._config = self.__load_config()
        return self._config

    def _load_settings(self, section_name, settings, store,
                       filter_settings=True):
        """
        Load section settings into a dictionary
        """
        section = self.config._sections.get(section_name)
        if not section:
            raise exception.ConfigSectionMissing(
                'Missing section %s in config' % section_name)
        store.update(section)
        section_conf = store
        for setting in settings:
            requirements = settings[setting]
            func, required, default, options, callback = requirements
            func = self.type_validators.get(func)
            value = func(self.config, section_name, setting)
            if value is not None:
                if options and not value in options:
                    raise exception.ConfigError(
                        '"%s" setting in section "%s" must be one of: %s' %
                        (setting, section_name,
                         ', '.join([str(o) for o in options])))
                if callback:
                    value = callback(value)
                section_conf[setting] = value
        if filter_settings:
            for key in store.keys():
                if key not in settings and key != '__name__':
                    store.pop(key)

    def _check_required(self, section_name, settings, store):
        """
        Check that all required settings were specified in the config.
        Raises ConfigError otherwise.

        Note that if a setting specified has required=True and
        default is not None then this method will not raise an error
        because a default was given. In short, if a setting is required
        you must provide None as the 'default' value.
        """
        section_conf = store
        for setting in settings:
            requirements = settings[setting]
            required = requirements[1]
            value = section_conf.get(setting)
            if value is None and required:
                raise exception.ConfigError(
                    'missing required option %s in section "%s"' %
                    (setting, section_name))

    def _load_defaults(self, settings, store):
        """
        Sets the default for each setting in settings regardless of whether
        the setting was specified in the config or not.
        """
        section_conf = store
        for setting in settings:
            default = settings[setting][2]
            if section_conf.get(setting) is None:
                if DEBUG_CONFIG:
                    log.debug('%s setting not specified. Defaulting to %s' %
                              (setting, default))
                section_conf[setting] = default

    def _load_extends_settings(self, section_name, store):
        """
        Loads all settings from other template(s) specified by a section's
        'extends' setting.

        This method walks a dependency tree of sections from bottom up. Each
        step is a group of settings for a section in the form of a dictionary.
        A 'master' dictionary is updated with the settings at each step. This
        causes the next group of settings to override the previous, and so on.
        The 'section_name' settings are at the top of the dependency tree.
        """
        section = store[section_name]
        extends = section.get('extends')
        if extends is None:
            return
        if DEBUG_CONFIG:
            log.debug('%s extends %s' % (section_name, extends))
        extensions = [section]
        while True:
            extends = section.get('extends', None)
            if not extends:
                break
            try:
                section = store[extends]
                if section in extensions:
                    exts = ', '.join([self._get_section_name(x['__name__'])
                                      for x in extensions])
                    raise exception.ConfigError(
                        "Cyclical dependency between sections %s. "
                        "Check your EXTENDS settings." % exts)
                extensions.insert(0, section)
            except KeyError:
                raise exception.ConfigError(
                    "%s can't extend non-existent section %s" %
                    (section_name, extends))
        transform = utils.AttributeDict()
        for extension in extensions:
            transform.update(extension)
        store[section_name] = transform

    def _load_section(self, section_name, section_settings,
                      filter_settings=True):
        """
        Returns a dictionary containing all section_settings for a given
        section_name by first loading the settings in the config, loading
        the defaults for all settings not specified, and then checking
        that all required options have been specified
        """
        store = utils.AttributeDict()
        self._load_settings(section_name, section_settings, store,
                            filter_settings)
        self._load_defaults(section_settings, store)
        self._check_required(section_name, section_settings, store)
        return store

    def _get_section_name(self, section):
        """
        Returns section name minus prefix
        e.g.
        $ print self._get_section('cluster smallcluster')
        $ smallcluster
        """
        return section.split()[1]

    def _get_sections(self, section_prefix):
        """
        Returns all sections starting with section_prefix
        e.g.
        $ print self._get_sections('cluster')
        $ ['cluster smallcluster', 'cluster mediumcluster', ..]
        """
        return [s for s in self.config.sections() if
                s.startswith(section_prefix)]

    def _load_sections(self, section_prefix, section_settings,
                       filter_settings=True):
        """
        Loads all sections starting with section_prefix and returns a
        dictionary containing the name and dictionary of settings for each
        section.
        keys --> section name (as returned by self._get_section_name)
        values --> dictionary of settings for a given section

        e.g.
        $ print self._load_sections('volumes', self.plugin_settings)

        {'myvol': {'__name__': 'volume myvol',
                    'device': None,
                    'mount_path': '/home',
                    'partition': 1,
                    'volume_id': 'vol-999999'},
         'myvol2': {'__name__': 'volume myvol2',
                       'device': None,
                       'mount_path': '/myvol2',
                       'partition': 1,
                       'volume_id': 'vol-999999'},
        """
        sections = self._get_sections(section_prefix)
        sections_store = utils.AttributeDict()
        for sec in sections:
            name = self._get_section_name(sec)
            sections_store[name] = self._load_section(sec, section_settings,
                                                      filter_settings)
        return sections_store

    def _load_cluster_sections(self, cluster_sections):
        """
        Loads all cluster sections. Similar to _load_sections but also handles
        populating specified keypair, volume, plugins, permissions, etc.
        settings
        """
        clusters = cluster_sections
        cluster_store = utils.AttributeDict()
        for cl in clusters:
            name = self._get_section_name(cl)
            cluster_store[name] = utils.AttributeDict()
            self._load_settings(cl, self.cluster_settings, cluster_store[name])
        for cl in clusters:
            name = self._get_section_name(cl)
            self._load_extends_settings(name, cluster_store)
            self._load_defaults(self.cluster_settings, cluster_store[name])
            self._load_keypairs(cluster_store[name])
            self._load_volumes(cluster_store[name])
            self._load_plugins(cluster_store[name])
            self._load_permissions(cluster_store[name])
            self._load_instance_types(cluster_store[name])
            self._check_required(cl, self.cluster_settings,
                                 cluster_store[name])
        return cluster_store

    def load(self):
        """
        Populate this config object from the s3site config
        """
        log.debug('Loading config')
        try:
            self.globals = self._load_section('global', self.global_settings)
        except exception.ConfigSectionMissing:
            pass
        try:
            self.aws = self._load_section('aws info', self.aws_settings)
        except exception.ConfigSectionMissing:
            log.warn("no [aws info] section found in config")
            log.warn("attempting to load credentials from environment...")
            self.aws.update(self.get_aws_from_environ())
        #self.clusters = self._load_cluster_sections(sections)
        return self

    def get_aws_from_environ(self):
        """
        Returns AWS credentials defined in the user's shell
        environment.
        """
        awscreds = {}
        for key in static.AWS_SETTINGS:
            if key.upper() in os.environ:
                awscreds[key] = os.environ.get(key.upper())
            elif key in os.environ:
                awscreds[key] = os.environ.get(key)
        return awscreds

    def get_aws_credentials(self):
        """
        Returns AWS credentials defined in the configuration
        file. Defining any of the AWS settings in the environment
        overrides the configuration file.
        """
        # first override with environment settings if they exist
        self.aws.update(self.get_aws_from_environ())
        return self.aws

    def get_easy_s3(self):
        """
        Factory for EasyEC2 class that attempts to load AWS credentials from
        the StarCluster config file. Returns an EasyS3 object if
        successful.
        """
        aws = self.get_aws_credentials()
        try:
            s3 = awsutils.EasyS3(**aws)
            return s3
        except TypeError:
            raise exception.ConfigError("no aws credentials found")

    def get_easy_cf(self):
        """
        Factory for EasyCF class that attempts to load AWS credentials from the
        StarCluster config file. Returns an EasyCF object if successful.
        """
        aws = self.get_aws_credentials()
        try:
            cf = awsutils.EasyCF(**aws)
            return cf
        except TypeError:
            raise exception.ConfigError("no aws credentials found")


if __name__ == "__main__":
    from pprint import pprint
    cfg = S3SiteConfig().load()
    pprint(cfg.globals)
    pprint(cfg.aws)
