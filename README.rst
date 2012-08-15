######
s3site
######

NOTE: This project is functional but currently a work in progress.

A simple utility for creating, syncing, and managing static sites hosted on S3
and optionally distributed with AWS CloudFront

Create a new S3-hosted static site::

    $ s3site create s3sitedemo
    site: s3sitedemo
    s3_site_url: s3sitedemo.amazonaws.com
    index_file: index.html
    error_file: error.html

Same thing but additionally configured with CloudFront::

    $ s3site create -c -C your.cname.com s3sitedemo
    site: s3sitedemo
    s3_site_url: s3sitedemo.amazonaws.com
    cf_domain_url: blahblah.cloudfront.net
    index_file: index.html
    error_file: error.html

NOTE: The above command can also be used on existing CloudFront-enabled sites
to update the CNAMEs associated with your CF domain::

    $ s3site create -c -C myother.cname.com -C your.cname.com s3sitedemo

Now use your favorite static web site generator to create the website in a
single directory (NOTE: Jekyll is just an example - you can use anything as
long as it outputs static files (e.g. html, js, css, png, etc))::

    $ jekyll /site/source /path/to/static/site/root

Now use s3site to sync it to your new site::

    $ s3site sync s3sitedemo /path/to/static/site/root

The above will synchronize the folder with your site's S3 bucket by
transferring missing and changed files. If additionally you configured your
site with CloudFront then any files transfered will also be invalidated in your
site's CloudFront cache which ensures that all distribution servers have the
latest version of your site. Anytime a root (or index) document for a site
needs to be invalidated the parent '/' is also invalidated.

You should now be able to view your site via its S3 or CloudFront URL. If you
forget these urls you can always use the 'list' command to look them up::

    $ s3site list

You can clone the latest copy of your website from S3 using the clone command::

    $ s3site clone s3sitedemo -o ~/s3sitedemo

Finally, you can also delete a site from S3 and it's associated CloudFront
distribution (if any)::

    $ s3site delete s3sitedemo
