import csv
import json
import pathlib
import sys

import click
import sqlite_utils

from goodreads_to_sqlite import utils


@click.group()
@click.version_option()
def cli():
    "Save data from Goodreads to a SQLite database"


@cli.command()
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="auth.json",
    help="Path to save tokens to, defaults to ./auth.json.",
)
def auth(auth):
    "Save authentication credentials to a JSON file"
    auth_data = {}
    if pathlib.Path(auth).exists():
        auth_data = json.load(open(auth))
    saved_user_id = auth_data.get("goodreads_user_id")
    click.echo(
        "Create a Goodreads developer key at https://www.goodreads.com/api/keys and paste it here:"
    )
    personal_token = click.prompt("Developer key")
    click.echo()
    click.echo(
        "Please enter your Goodreads user ID (numeric) or just paste your Goodreads profile URL."
    )
    user_id = click.prompt("User-ID or URL", default=saved_user_id)
    user_id = user_id.strip("/").split("/")[-1].split("-")[0]
    if not user_id.isdigit():
        raise Exception(
            "Your user ID has to be a number! {} does not look right".format(user_id)
        )
    auth_data["goodreads_personal_token"] = personal_token
    auth_data["goodreads_user_id"] = user_id
    open(auth, "w").write(json.dumps(auth_data, indent=4) + "\n")
    auth_suffix = (" -a " + auth) if auth != "auth.json" else ""
    click.echo()
    click.echo(
        "Your authentication credentials have been saved to {}. You can now import books by running".format(
            auth
        )
    )
    click.echo()
    click.echo("    goodreads-to-sqlite books books.db" + auth_suffix + " [username]")
    click.echo()


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.option(
    "-a",
    "--auth",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    default="auth.json",
    help="Path to save tokens to, defaults to auth.json",
)
@click.argument("username", required=False)
@click.option(
    "-s",
    "--scrape",
    is_flag=True,
    help="Scrape missing data (like date_read) from the web interface. Slow.",
)
def books(db_path, auth, username, scrape):
    """Save books for a specified user, e.g. rixx"""
    db = sqlite_utils.Database(db_path)
    try:
        data = json.load(open(auth))
        token = data["goodreads_personal_token"]
        user_id = data["goodreads_user_id"]
    except (KeyError, FileNotFoundError):
        utils.error(
            "Cannot find authentication data, please run goodreads_to_sqlite auth!"
        )

    click.secho(f"Read credentials for user ID {user_id}.", fg="green")
    if username:
        user_id = username if username.isdigit() else utils.fetch_user_id(username)

    utils.fetch_user_and_shelves(user_id, token, db=db)
    utils.fetch_books(db, user_id, token, scrape=scrape)
