from boto.exception import S3ResponseError

from s3site import exception


class SiteManager(object):
    def __init__(self, s3=None, cf=None, cfg=None):
        self.s3 = s3
        self.cf = cf
        self.cfg = cfg

    def get_site(self, name):
        site_bucket = self.s3.get_bucket(name)
        webconfig = site_bucket.get_website_configuration()
        return Site(site_bucket, self.s3, self.cf, webconfig=webconfig)

    def get_site_or_none(self, name):
        try:
            return self.get_site(name)
        except (exception.BucketDoesNotExist, S3ResponseError):
            pass

    def list_all_sites(self):
        buckets = self.s3.get_buckets()
        for bucket in buckets:
            try:
                bucket.get_website_configuration()
            except S3ResponseError:
                continue
            print bucket.name
        print self.cf.conn.get_all_distributions()


class Site(object):
    def __init__(self, bucket, s3, cf, webconfig=None):
        self.bucket = bucket
        self.webconfig = webconfig or bucket.get_website_configuration()
        self.s3 = s3
        self.cf = cf
