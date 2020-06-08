import os
from setuptools import setup, find_packages
from data_interrogator import __version__

with open(os.path.join(os.path.dirname(__file__), '/docs/README.rst')) as readme:
    README = readme.read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name='django-data-interrogator',
    version=__version__,
    packages=find_packages(),
    include_package_data=True,
    package_data={
        'data_interrogator': ['*.html', '*.js', '*.css'],
    },
    license='MIT License',
    description='A suite of interactive table builder utilities that create reports using efficient SQL queries.',
    long_description=README,
    url='https://github.com/LegoStormtroopr/django-data-interrogator/',
    author='Samuel Spencer',
    author_email='sam@sqbl.org',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        # Replace these appropriately if you are stuck on Python 2.
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Programming Language :: Python :: 3.3',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
    keywords='django data analytics',
    install_requires=[
        'django',  # I mean obviously you'll have django installed if you want to use this.
        'django-model-utils',
    ],
    develop_requires=[
        'pandas'
    ]

)
