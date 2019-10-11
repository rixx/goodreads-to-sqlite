# goodreads-to-sqlite

[![PyPI](https://img.shields.io/pypi/v/goodreads-to-sqlite.svg)](https://pypi.org/project/goodreads-to-sqlite/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/rixx/goodreads-to-sqlite/blob/master/LICENSE)

Save data from Goodreads to a SQLite database. Can save all your public shelves and reviews, and also the public reviews
and shelves of other people.

![Demo](./assets/demo.gif)

## How to install

    $ pip install goodreads-to-sqlite

## Authentication

Create a Goodreads developer token: https://www.goodreads.com/api/keys

Run this command and paste in your token and your profile URL:

    $ goodreads-to-sqlite auth

This will create a file called `auth.json` in your current directory containing the required value. To save the file at
a different path or filename, use the `--auth=myauth.json` option.

## Retrieving books for a user

The `books` command retrieves all of the books and reviews/ratings belonging to a specified user. If you leave out the
user, the books for your own account will be fetched. The user will have to be either the user ID (the numerical part of
a user's profile URL), or the name of their vanity URL.

    $ goodreads-to-sqlite books goodreads.db rixx

The `auth.json` file is used by default for authentication. You can point to a different location of `auth.json` using
`-a`:

    $ goodreads-to-sqlite books goodreads.db rixx -a /path/to/auth.json

## Limitations

- The order of books in shelves is not exposed in the API, so we cannot determine the order of the to-read list.
- The API does not expose the dates of multiple reads of a book.
- Goodreads also offers a CSV export, which is currently not supported as an input format.
- Since the Goodreads API is a bit slow, and we are restricted to one request per second, for larger libraries the
  import can take a couple of minutes.
- The script currently re-syncs the entire library instead of just looking at newly changed data, to make sure we don't
  lose information after aborted syncs.

## Thanks

This package is heavily inspired by [github-to-sqlite](https://github.com/dogsheep/github-to-sqlite/) by [Simon
Willison](https://simonwillison.net/2019/Oct/7/dogsheep/).

The terminal recording above was made with [ASCIInema](https://asciinema.org/a/WT6bfxoFP3IlgeX8PO6FHDdDx).
