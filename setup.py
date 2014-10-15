''' setup.py - Distutils setup file for PyDSP package

    David Banas
    July 9, 2011

    $Id: setup.py 33 2011-07-10 00:12:37Z dbanas $
'''

from distutils.core import setup

setup(
    name='PyDSP',
    version='0.4',
    packages=['pydsp',],
    license='BSD',
    long_description=open('README.txt').read(),
    url='https://github.com/capn-freako/PyDSP',
    author='David Banas',
    author_email='capn.freako@gmail.com',
)
