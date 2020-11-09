from __future__ import annotations

from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / 'README.md').read_text(encoding='utf-8')


setup(
    name='pattern-matching-pep634',

    # version= # Handled in setup.cfg

    description='Pattern matching, backport of PEP-634', 

    long_description=long_description,
    
    long_description_content_type='text/markdown',

    url='https://github.com/MegaIng/pattern-matching',

    author='MegaIng',
    author_email='trampchamp@hotmail.de',

    # Classifiers help users find your project by categorizing it.
    #
    # For a list of valid classifiers, see https://pypi.org/classifiers/
    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Software Development',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
    ],

    keywords='pattern-matching, PEP-634, backport',

    packages=['pattern_matching'],

    python_requires='>=3.7',
    install_requires=['lark'],
    project_urls={  # Optional
        'Bug Reports': 'https://github.com/MegaIng/pattern-matching/issues',
        'Source': 'https://github.com/MegaIng/pattern-matching/',
    },
)
