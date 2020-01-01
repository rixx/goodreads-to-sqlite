# goodreads-to-sqlite

[![PyPI](https://img.shields.io/pypi/v/goodreads-to-sqlite.svg)](https://pypi.org/project/goodreads-to-sqlite/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/rixx/goodreads-to-sqlite/blob/master/LICENSE)

Save data from Goodreads to a SQLite database. Can save all your public shelves and reviews, and also the public reviews
and shelves of other people.

![Demo](./assets/demo.gif)

## How to install

    $ pip install goodreads-to-sqlite

Add the `-U` flag to update. Change notes can be found in the ``CHANGELOG`` file, next to this README.

## Authentication

Create a Goodreads developer token: https://www.goodreads.com/api/keys

Run this command and paste in your token and your profile URL:

    $ goodreads-to-sqlite auth

This will create a file called `auth.json` in your current directory containing the required value. To save the file at
a different path or filename, use the `--auth=myauth.json` option.

## Retrieving books

The `books` command retrieves all of the books and reviews/ratings belonging to you:

    $ goodreads-to-sqlite books goodreads.db rixx

You can specify the user to target, to fetch books on public shelves of other users. Please provide either the user ID
(the numerical part of a user's profile URL), or the name of their vanity URL.

    $ goodreads-to-sqlite books goodreads.db rixx

Sometime in 2018 or 2017, Goodreads started leaving out some "read_at" timestamps in their API. If you want to include
these datapoints regardless, you can add the `--scrape` parameter, and the dates will be scraped from the website.
This will take a bit longer, by maybe a minute depending on the size of your library.

    $ goodreads-to-sqlite books goodreads.db --scrape

The `auth.json` file is used by default for authentication. You can point to a different location of `auth.json` using
`-a`:

    $ goodreads-to-sqlite books goodreads.db rixx -a /path/to/auth.json

## Limitations

- The order of books in shelves is not exposed in the API, so we cannot determine the order of the to-read list.
- Goodreads also offers a CSV export, which is currently not supported as an input format.
- Since the Goodreads API is a bit slow, and we are restricted to one request per second, for larger libraries the
  import can take a couple of minutes.
- The script currently re-syncs the entire library instead of just looking at newly changed data, to make sure we don't
  lose information after aborted syncs.

## Thanks

This package is heavily inspired by [github-to-sqlite](https://github.com/dogsheep/github-to-sqlite/) by [Simon
Willison](https://simonwillison.net/2019/Oct/7/dogsheep/).

The terminal recording above was made with [ASCIInema](https://asciinema.org/a/WT6bfxoFP3IlgeX8PO6FHDdDx).
