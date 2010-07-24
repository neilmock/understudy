#!/usr/bin/env python

"""
@file setup.py
@author Neil Mock
@date 07/02/2010
@brief setuptools config for understudy
"""

version = '0.1.0'

sdict = {
    'name' : 'understudy',
    'version' : version,
    'description' : 'Distributed computing framework for Python.',
    'long_description' : 'Distributed computing framework for Python.',
    'url': 'http://github.com/neilmock/understudy',
    'download_url' : 'http://cloud.github.com/downloads/neilmock/understudy/understudy-%s.tar.gz' % version,
    'author' : 'Neil Mock',
    'author_email' : 'neilmock@gmail.com',
    'maintainer' : 'Neil Mock',
    'maintainer_email' : 'neilmock@gmail.com',
    'keywords' : ['understudy', 'distributed', 'cloud'],
    'license' : 'MIT',
    'packages' : ['understudy'],
    'classifiers' : [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python'],
}

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(**sdict)
