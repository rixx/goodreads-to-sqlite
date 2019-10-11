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
    click.echo()
    personal_token = click.prompt("Developer key")
    click.echo(
        "Please enter your Goodreads user ID (numeric) or just paste your Goodreads profile URL."
    )
    click.echo()
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
    "--load",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=True, exists=True),
    help="Load books from the CSV file available at https://www.goodreads.com/review/import/ instead of the API",
)
def books(db_path, auth, load, username):
    "Save books for a specified user, e.g. rixx"
    db = sqlite_utils.Database(db_path)
    user_id = username if username and username.isdigit() else None
    username = None if user_id else username
    if load:
        if not username:
            click.secho(
                "Please give your username for a file import to make sure the books are saved for the correct user!",
                bold=True,
                fg="red",
            )
            sys.exit(-1)
        books = csv.DictReader(open(load))  # TODO save books from CSV
    else:
        if username:
            user_id = utils.fetch_user_id(username)
        try:
            data = json.load(open(auth))
            token = data["goodreads_personal_token"]
            user_id = user_id or data["goodreads_user_id"]
        except (KeyError, FileNotFoundError):
            click.secho(
                "Cannot find authentication data, please run goodreads_to_sqlite auth!",
                bold=True,
                fg="red",
            )
            sys.exit(-1)
        utils.save_user(db, utils.fetch_user(user_id, token, db=db))
        # TODO: tqdm
        utils.fetch_books(db, user_id, token, commit=True)
