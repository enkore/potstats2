
from setuptools import setup, find_packages

description = open('README.rst', 'r').read()

setup(
    name='potstats2',

    use_scm_version=True,
    setup_requires=['setuptools_scm', 'pytest-runner'],
    install_requires=[
        'click',
        'requests',
        'sqlalchemy',
        'Flask',
        'psycopg2',
    ],
    tests_require=[
        'potstats2[test]',
    ],
    extras_require={
        'test': [
            'pytest',
        ],
        'cache': [
            'redis',
            'blinker'
        ],
    },

    description='potstats2',
    long_description=description,

    url='https://github.com/enkore/potstats2',
    author='Marian Beermann',

    license='EUPL',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
    ],

    packages=find_packages('src'),
    package_dir={'': 'src'},

    entry_points = {
        'console_scripts': [
            'potstats2-worldeater = potstats2.worldeater.main:main',
            'potstats2-db = potstats2.db:main',
            'potstats2-backend-dev = potstats2.backend:main',
            'potstats2-cache = potstats2.backend.cache:main',
            'potstats2-analytics = potstats2.analytics:main',
        ],
    },
)
