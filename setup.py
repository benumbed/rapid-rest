#!/usr/bin/env python3
from setuptools import setup, find_packages

def import_requires():
    """
    Imports the required packages from requirements.txt
    """
    with open("requirements.txt", "r") as req:
        return [req_line.strip() for req_line in req.readlines() if not req_line.startswith("-") and req_line.strip()]

setup(
    name="rapid-rest",
    version="0.1.1",
    url='https://gitlab.bunker/global/rapid-rest',
    description="Rapid development REST API server built on Flask and friends",
    license='MIT',
    author='Benumbed',
    author_email='benumbed@projectneutron.com',
    package_dir={'': 'src'},
    packages=[
      "rapidrest",
      "rapidrest.security",
      "rapidrest_dummyapi",
      "rapidrest_tests",
    ],
    install_requires = import_requires(),
    extras_require = {
        "Vault": ["hvac>=0.7.2"],
        "tests": ["nose2", "WebTest"]
    },
    classifiers=[
        'Topic :: Internet :: WWW/HTTP :: WSGI :: Application',
        'Development Status :: 2 - Alpha',
        'Environment :: Web Environment',
        'Framework :: Flask',
        'License :: OSI Approved :: MIT',
        'Intended Audience :: Information Technology',
        'Natural Language :: English'
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ]
)

