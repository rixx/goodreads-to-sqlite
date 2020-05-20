import os

from setuptools import setup

VERSION = "0.5"


def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="goodreads-to-sqlite",
    description="Save data from Goodreads to a SQLite database",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Tobias Kunze",
    author_email="r@rixx.de",
    url="https://github.com/rixx/goodreads-to-sqlite",
    project_urls={
        "Source": "https://github.com/rixx/goodreads-to-sqlite",
        "Issues": "https://github.com/rixx/goodreads-to-sqlite/issues",
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "License :: OSI Approved",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Database",
    ],
    keywords="goodreads books sqlite export dogsheep",
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["goodreads_to_sqlite"],
    entry_points="""
        [console_scripts]
        goodreads-to-sqlite=goodreads_to_sqlite.cli:cli
    """,
    install_requires=[
        "beautifulsoup4~=4.8",
        "click",
        "python-dateutil",
        "requests",
        "sqlite-utils~=2.4.4",
        "tqdm~=4.36",
    ],
    extras_require={"test": ["pytest"]},
    tests_require=["goodreads-to-sqlite[test]"],
)
