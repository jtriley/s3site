import os
import glob
import time
import hashlib
import mimetypes

from boto.exception import S3ResponseError

from s3site import spinner
from s3site import exception
from s3site import progressbar
from s3site.logger import log


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

    def create_site(self, name, index_doc="index.html", error_doc="",
                    headers=None, create_cf_domain=False,
                    enable_cf_domain=True, cf_domain_cnames=None,
                    cf_domain_comment=None, cf_trusted_signers=None):
        site_bucket = self.s3.get_bucket_or_none(name)
        if site_bucket:
            raise exception.SiteAlreadyExists(name)
        site_bucket = self.s3.create_bucket(name)
        site_bucket.configure_website(suffix=index_doc, error_key=error_doc,
                                      headers=None)
        if create_cf_domain:
            self.cf.create_distribution(
                origin=site_bucket.get_website_endpoint(),
                enabled=enable_cf_domain,
                cnames=cf_domain_cnames, comment=cf_domain_comment,
                trusted_signers=cf_trusted_signers)
        return site_bucket

    def delete_site(self, name):
        site = self.get_site(name)
        dists = self.cf.get_all_dists_for_bucket(site.bucket)
        for d in dists:
            log.info("Deleting CloudFront distribution: %s" % d.id,
                     extra=dict(__nonl__=True))
            s = spinner.Spinner()
            s.start()
            dist = d.get_distribution()
            dist.disable()
            while dist.status == 'InProgress':
                time.sleep(30)
                dist = d.get_distribution()
            s.stop()
            dist.delete()
        self.s3.delete_bucket(site.bucket)

    def get_all_sites(self):
        buckets = self.s3.get_buckets()
        sites = []
        for bucket in buckets:
            try:
                webconfig = bucket.get_website_configuration()
                site = Site(bucket, self.s3, self.cf, webconfig=webconfig)
                sites.append(site)
            except S3ResponseError:
                continue
        return sites

    def list_all_sites(self):
        dists = self.cf.get_all_distributions()
        sites = self.get_all_sites()
        header = '*' * 60
        if not sites:
            log.info("No sites found.")
        for site in sites:
            s3_web_url = site.bucket.get_website_endpoint()
            sdists = [d for d in dists if d.origin.dns_name == s3_web_url]
            print header
            print site.name
            print header
            print 'S3 Website URL: %s' % s3_web_url
            webcfg = site.webconfig.get("WebsiteConfiguration")
            index_file = webcfg.get("IndexDocument", {}).get("Suffix", 'N/A')
            error_file = webcfg.get("ErrorDocument", {}).get("Key", 'N/A')
            print 'Index file: %s' % index_file
            print 'Error file: %s' % error_file
            if sdists:
                print 'CloudFront Distributions:'
            for sdist in sdists:
                print '   - %s (%s)' % (sdist.id, sdist.domain_name)
            print

    def sync(self, site_name, root_dir):
        site = self.get_site(site_name)
        return site.sync(root_dir)


class Site(object):
    def __init__(self, bucket, s3, cf, webconfig=None):
        self.bucket = bucket
        self.webconfig = webconfig or bucket.get_website_configuration()
        self.s3 = s3
        self.cf = cf
        self._progress_bar = None

    @property
    def name(self):
        return self.bucket.name

    @property
    def progress_bar(self):
        if not self._progress_bar:
            widgets = ['', progressbar.Fraction(), ' ',
                       progressbar.Bar(marker=progressbar.RotatingMarker()),
                       ' ', progressbar.Percentage(), ' ', ' ']
            pbar = progressbar.ProgressBar(widgets=widgets, force_update=True)
            self._progress_bar = pbar
        return self._progress_bar

    def _find_files(self, path):
        for cfile in glob.glob(os.path.join(path, '*')):
            if os.path.isdir(cfile):
                for py in self._find_files(cfile):
                    yield py
            else:
                yield cfile

    def _compute_md5(self, path):
        md5 = hashlib.md5()
        f = open(path)
        while True:
            data = f.read(8192)
            if not data:
                break
            md5.update(data)
        return md5.hexdigest()

    def get_bucket_files(self):
        return dict([(k.name, k) for k in self.bucket.list()])

    def _s3_upload_progress(self, current, total):
        pb = self.progress_bar
        pb.maxval = total
        pb.update(current)

    def _upload_file_to_site(self, path, s3path):
        key = self.bucket.new_key(s3path)
        key.content_type = mimetypes.guess_type(path)
        self.progress_bar.reset()
        key.set_contents_from_filename(path, policy='public-read',
                                       cb=self._s3_upload_progress)
        self.progress_bar.reset()

    def sync(self, rootdir):
        log.info("Syncing '%s' with '%s'" % (self.name, rootdir))
        log.info("Fetching list of files in S3 bucket: %s" % self.name)
        s3files = self.get_bucket_files()
        for i in self._find_files(rootdir):
            s3path = os.path.relpath(i, rootdir)
            if s3path in s3files:
                etag = s3files.get(s3path).etag.replace('"', '')
                md5 = self._compute_md5(i)
                log.debug('s3 path found: %s with etag: %s' % (s3path, etag))
                if etag != md5:
                    log.info("Existing S3 path '%s' is NOT in sync" % s3path)
                    self._upload_file_to_site(i, s3path)
            else:
                log.info("Local file '%s' not on S3...uploading" % i)
                self._upload_file_to_site(i, s3path)
        log.info("Successfully synced site: %s" % self.name)
