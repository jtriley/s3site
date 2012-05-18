config_template = """\
###############################
## S3Site Configuration File ##
###############################
[global]
# enable experimental features for this release
#ENABLE_EXPERIMENTAL=True
# specify a web browser to launch when viewing spot history plots
#WEB_BROWSER=chromium
# split the config into multiple files
#INCLUDE=~/.s3site/aws, ~/.s3site/sites

#############################################
## AWS Credentials and Connection Settings ##
#############################################
[aws info]
# This is the AWS credentials section (required).
# These settings apply to all clusters
# replace these with your AWS keys
AWS_ACCESS_KEY_ID = #your_aws_access_key_id
AWS_SECRET_ACCESS_KEY = #your_secret_access_key
# replace this with your account number
AWS_USER_ID= #your userid
# Uncomment to specify a different Amazon AWS region  (OPTIONAL)
# (defaults to us-east-1 if not specified)
# NOTE: AMIs have to be migrated!
#AWS_REGION_NAME = eu-west-1
#AWS_REGION_HOST = ec2.eu-west-1.amazonaws.com
# Uncomment these settings when creating an instance-store (S3) AMI (OPTIONAL)
#EC2_CERT = /path/to/your/cert-asdf0as9df092039asdfi02089.pem
#EC2_PRIVATE_KEY = /path/to/your/pk-asdfasd890f200909.pem
# Uncomment these settings to use a proxy host when connecting to AWS
#AWS_PROXY = your.proxyhost.com
#AWS_PROXY_PORT = 8080
#AWS_PROXY_USER = yourproxyuser
#AWS_PROXY_PASS = yourproxypass
"""

DASHES = '-' * 10
copy_below = ' '.join([DASHES, 'COPY BELOW THIS LINE', DASHES])
end_copy = ' '.join([DASHES, 'END COPY', DASHES])
copy_paste_template = '\n'.join([copy_below, config_template, end_copy]) + '\n'
