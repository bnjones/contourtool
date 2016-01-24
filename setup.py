#!/usr/bin/env python

from __future__ import print_function

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
    print("warning: setuptools not available, can't install_require PyUSB")
    print("warning: If it isn't already installed, try 'pip install pyusb'")

setup(
    name='contourtool',
    version='0.1',
    description='A tool to fetch data from Contour Next USB blood glucose'
    ' meters.',
    author='Ben Jones',
    author_email='benj2579@gmail.com',
    install_requires=['pyusb'],
    packages=['contourtool'],
    entry_points={
        'console_scripts': [
            'contourtool = contourtool:main',
        ],
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console'
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
    ]
)
