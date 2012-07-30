#!/usr/bin/env python
import os
import sys

if sys.version_info < (2, 5):
    error = "ERROR: s3site requires Python 2.5+ ... exiting."
    print >> sys.stderr, error
    sys.exit(1)

try:
    from setuptools import setup, find_packages
    console_scripts = ['s3site = s3site.cli:main']
    extra = dict(test_suite="s3site.tests",
                 tests_require="nose",
                 install_requires=["boto>=2.5.2"],
                 include_package_data=True,
                 entry_points=dict(console_scripts=console_scripts),
                 zip_safe=False)
except ImportError:
    import string
    from distutils.core import setup  # pyflakes:ignore

    def convert_path(pathname):
        """
        Local copy of setuptools.convert_path used by find_packages (only used
        with distutils which is missing the find_packages feature)
        """
        if os.sep == '/':
            return pathname
        if not pathname:
            return pathname
        if pathname[0] == '/':
            raise ValueError("path '%s' cannot be absolute" % pathname)
        if pathname[-1] == '/':
            raise ValueError("path '%s' cannot end with '/'" % pathname)
        paths = string.split(pathname, '/')
        while '.' in paths:
            paths.remove('.')
        if not paths:
            return os.curdir
        return os.path.join(*paths)

    def find_packages(where='.', exclude=()):  # pyflakes:ignore
        """
        Local copy of setuptools.find_packages (only used with distutils which
        is missing the find_packages feature)
        """
        out = []
        stack = [(convert_path(where), '')]
        while stack:
            where, prefix = stack.pop(0)
            for name in os.listdir(where):
                fn = os.path.join(where, name)
                if ('.' not in name and os.path.isdir(fn) and
                    os.path.isfile(os.path.join(fn, '__init__.py'))):
                    out.append(prefix + name)
                    stack.append((fn, prefix + name + '.'))
        for pat in list(exclude) + ['ez_setup', 'distribute_setup']:
            from fnmatch import fnmatchcase
            out = [item for item in out if not fnmatchcase(item, pat)]
        return out

    extra = {}

VERSION = 0.9999
static = os.path.join('s3site', 'static.py')
execfile(static)  # pull VERSION from static.py

README = open('README.rst').read()

setup(
    name='s3site',
    version=VERSION,
    packages=find_packages(),
    scripts=['scripts/s3site'],
    license='LGPL3',
    author='Justin Riley',
    author_email='justin.t.riley@gmail.com',
    url="http://github.com/jtriley/s3site",
    description="A simple utility for creating, syncing, and managing static "
    "sites hosted on S3 and distributed with AWS CloudFront",
    long_description=README,
    classifiers=[
        'Environment :: Console',
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU Library or Lesser General Public '
        'License (LGPL)',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.5',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    **extra
)
