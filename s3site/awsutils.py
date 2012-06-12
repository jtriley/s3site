"""
EC2/S3 Utility Classes
"""
import os
import posixpath
import mimetypes

import boto
import boto.s3.connection
from boto.cloudfront.origin import CustomOrigin

from s3site import utils
from s3site import exception
from s3site import progressbar
from s3site.logger import log


class EasyAWS(object):
    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 connection_authenticator, **kwargs):
        """
        Create an EasyAWS object.

        Requires aws_access_key_id/aws_secret_access_key from an Amazon Web
        Services (AWS) account and a connection_authenticator function that
        returns an authenticated AWS connection object

        Providing only the keys will default to using Amazon EC2

        kwargs are passed to the connection_authenticator's constructor
        """
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.connection_authenticator = connection_authenticator
        self._conn = None
        self._kwargs = kwargs

    def reload(self):
        self._conn = None
        return self.conn

    @property
    def conn(self):
        if self._conn is None:
            log.debug('creating self._conn w/ connection_authenticator ' +
                      'kwargs = %s' % self._kwargs)
            self._conn = self.connection_authenticator(
                self.aws_access_key_id, self.aws_secret_access_key,
                **self._kwargs)
        return self._conn


class EasyS3(EasyAWS):
    DefaultHost = 's3.amazonaws.com'
    _calling_format = boto.s3.connection.OrdinaryCallingFormat()

    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 aws_s3_path='/', aws_port=None, aws_is_secure=True,
                 aws_s3_host=DefaultHost, aws_proxy=None, aws_proxy_port=None,
                 aws_proxy_user=None, aws_proxy_pass=None, **kwargs):
        kwargs = dict(is_secure=aws_is_secure, host=aws_s3_host or
                      self.DefaultHost, port=aws_port, path=aws_s3_path,
                      proxy=aws_proxy, proxy_port=aws_proxy_port,
                      proxy_user=aws_proxy_user, proxy_pass=aws_proxy_pass)
        if aws_s3_host:
            kwargs.update(dict(calling_format=self._calling_format))
        super(EasyS3, self).__init__(aws_access_key_id, aws_secret_access_key,
                                     boto.connect_s3, **kwargs)
        self._progress_bar = None

    def __repr__(self):
        return '<EasyS3: %s>' % self.conn.server_name()

    @property
    def progress_bar(self):
        if not self._progress_bar:
            widgets = ['', progressbar.Fraction(), ' ',
                       progressbar.Bar(marker=progressbar.RotatingMarker()),
                       ' ', progressbar.Percentage(), ' ', ' ']
            pbar = progressbar.ProgressBar(widgets=widgets, force_update=True)
            self._progress_bar = pbar
        return self._progress_bar

    def create_bucket(self, bucket_name):
        """
        Create a new bucket on S3. bucket_name must be unique, the bucket
        namespace is shared by all AWS users
        """
        bucket_name = bucket_name.split('/')[0]
        try:
            log.info("Creating new bucket: %s" % bucket_name)
            return self.conn.create_bucket(bucket_name)
        except boto.exception.S3CreateError, e:
            if e.error_code == "BucketAlreadyExists":
                raise exception.BucketAlreadyExists(bucket_name)
            raise

    def delete_bucket(self, bucket):
        log.info("Deleting all files in bucket: %s" % bucket.name)
        bucket.delete_keys([f.name for f in bucket.list()])
        log.info("Deleting bucket: %s" % bucket.name)
        bucket.delete()

    def bucket_exists(self, bucket_name):
        """
        Check if bucket_name exists on S3
        """
        try:
            return self.get_bucket(bucket_name) is not None
        except exception.BucketDoesNotExist:
            return False

    def get_or_create_bucket(self, bucket_name):
        try:
            return self.get_bucket(bucket_name)
        except exception.BucketDoesNotExist:
            log.info("Creating bucket '%s'" % bucket_name)
            return self.create_bucket(bucket_name)

    def get_bucket_or_none(self, bucket_name):
        """
        Returns bucket object representing S3 bucket
        Returns None if unsuccessful
        """
        try:
            return self.get_bucket(bucket_name)
        except exception.BucketDoesNotExist:
            pass

    def get_bucket(self, bucketname):
        """
        Returns bucket object representing S3 bucket
        """
        try:
            return self.conn.get_bucket(bucketname)
        except boto.exception.S3ResponseError, e:
            if e.error_code == "NoSuchBucket":
                raise exception.BucketDoesNotExist(bucketname)
            raise

    def list_bucket(self, bucketname):
        bucket = self.get_bucket(bucketname)
        for file in bucket.list():
            if file.name:
                print file.name

    def get_buckets(self):
        try:
            buckets = self.conn.get_all_buckets()
        except TypeError:
            # hack until boto (or eucalyptus) fixes get_all_buckets
            raise exception.AWSError("AWS credentials are not valid")
        return buckets

    def list_buckets(self):
        for bucket in self.get_buckets():
            print bucket.name

    def get_bucket_files(self, bucket):
        files = [file for file in bucket.list()]
        return files

    def get_bucket_files_map(self, bucket):
        return dict([(k.name, k) for k in bucket.list()])

    def _s3_upload_progress(self, current, total):
        pb = self.progress_bar
        pb.maxval = total
        pb.update(current)

    def put_file(self, path, bucket, bucket_path):
        key = bucket.new_key(bucket_path)
        key.content_type = mimetypes.guess_type(path)
        self.progress_bar.reset()
        key.set_contents_from_filename(path, policy='public-read',
                                       cb=self._s3_upload_progress)
        self.progress_bar.reset()

    def _local_to_s3_path(self, path):
        # remove Windows driver letters (if any)
        path = utils.strip_windows_drive_letter(path)
        # split path based on OS path separator
        parts = path.split(os.path.sep)
        # join using unix path separator to match S3
        return posixpath.sep.join(parts)

    def sync_bucket(self, rootdir, bucket):
        log.info("Fetching list of files in S3 bucket: %s" % bucket.name)
        s3files = self.get_bucket_files_map(bucket)
        for f in utils.find_files(rootdir):
            s3path = self._local_to_s3_path(os.path.relpath(f, rootdir))
            if s3path in s3files:
                etag = s3files.get(s3path).etag.replace('"', '')
                md5 = utils.compute_md5(f)
                log.debug('s3 path found: %s with etag: %s' % (s3path, etag))
                if etag != md5:
                    log.info("Existing S3 path '%s' is NOT in sync" % s3path)
                    self.put_file(f, bucket, s3path)
            else:
                log.info("Local file '%s' not on S3...uploading" % f)
                self.put_file(f, bucket, s3path)

class EasyCF(EasyAWS):
    def __init__(self, aws_access_key_id, aws_secret_access_key, aws_port=None,
                 aws_proxy=None, aws_proxy_port=None,
                 host='cloudfront.amazonaws.com', **kwargs):
        kwargs = dict(port=aws_port, proxy=aws_proxy,
                      proxy_port=aws_proxy_port)
        super(EasyCF, self).__init__(aws_access_key_id, aws_secret_access_key,
                                     boto.connect_cloudfront, **kwargs)

    def __repr__(self):
        return '<EasyCF: %s>' % self.conn.server_name()

    def get_distribution_by_id(self, id):
        dists = self.get_all_distributions()
        for dist in dists:
            if dist.id == id:
                return dist
        raise exception.DistributionDoesNotExist(id)

    def get_all_distributions(self):
        return self.conn.get_all_distributions()

    def get_all_dists_for_bucket(self, bucket):
        web_endpoint = bucket.get_website_endpoint()
        return [d for d in self.get_all_distributions()
                if d.origin.dns_name == web_endpoint]

    def create_distribution(self, origin, enabled, caller_reference='',
                            cnames=None, comment='', trusted_signers=None):
        origin = CustomOrigin(dns_name=origin,
                              origin_protocol_policy="http-only")
        dist = self.conn.create_distribution(origin, enabled,
                                             caller_reference=caller_reference,
                                             cnames=cnames, comment=comment,
                                             trusted_signers=trusted_signers)
        log.info("New CloudFront distribution created: %s" % dist.id)
        return dist


if __name__ == "__main__":
    from starcluster.config import get_easy_ec2
    ec2 = get_easy_ec2()
    ec2.list_all_instances()
    ec2.list_registered_images()
