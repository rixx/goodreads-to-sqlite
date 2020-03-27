import datetime as dt
import sys
import xml.etree.ElementTree as ET
from contextlib import suppress

import bs4
import click
import dateutil.parser
import requests
from tqdm import tqdm

BASE_URL = "https://www.goodreads.com/"


def error(message):
    click.secho(message, bold=True, fg="red")
    sys.exit(-1)


def fetch_books(db, user_id, token, scrape=False):
    """Fetches a user's books and reviews from the public Goodreads API.

    Technically we are rate-limited to one request per second, but since we are not
    running in parallel, and the Goodreads API responds way slower than that, we are
    reliably in the clear."""
    url = BASE_URL + "review/list/{}.xml".format(user_id)
    params = {
        "key": token,
        "v": "2",
        "per_page": "200",
        "sort": "date_updated",
        "page": 0,
    }
    end = -1
    total = 0
    books = dict()
    authors = dict()
    reviews = dict()
    progress_bar = None

    while end < total:
        params["page"] += 1
        response = requests.get(url, data=params)
        response.raise_for_status()
        root = ET.fromstring(response.content.decode())
        review_data = root.find("reviews")
        end = int(review_data.attrib["end"])
        total = int(review_data.attrib["total"])

        if progress_bar is None:
            progress_bar = tqdm(
                desc="Fetching books", total=int(review_data.attrib.get("total"))
            )
        for review in review_data:
            book_data = review.find("book")
            book_authors = []

            for author in book_data.find("authors"):
                author_id = author.find("id").text
                author = _get_author_from_data(author)
                authors[author_id] = author
                book_authors.append(author)

            book_id = book_data.find("id").text
            books[book_id] = _get_book_from_data(book_data, book_authors)

            review_id = review.find("id").text
            reviews[review_id] = _get_review_from_data(review, user_id)
            progress_bar.update(1)
    progress_bar.close()

    if scrape is True:
        scrape_data(user_id, reviews)

    save_authors(db, list(authors.values()))
    save_books(db, list(books.values()))
    save_reviews(db, list(reviews.values()))


def scrape_data(user_id, reviews):
    relevant_ids = {
        review_id
        for review_id, review in reviews.items()
        if "read_at" not in review
        and any(shelf["name"] == "read" for shelf in review["shelves"])
    }
    url = BASE_URL + "review/list/{}".format(user_id)
    params = {
        "utf8": "✓",
        "shelf": "read",
        "per_page": "100",  # Maximum allowed page size
        "sort": "date_updated",
        "page": 0,
    }
    date_counter = 0
    progress_bar = None
    while True:
        params["page"] += 1
        response = requests.get(url, data=params)
        response.raise_for_status()
        soup = bs4.BeautifulSoup(response.content.decode(), "html.parser")
        if progress_bar is None:
            read_shelf = soup.select("a.selectedShelf")[0].text
            total = int(read_shelf[read_shelf.find("(") :].strip("()"))
            progress_bar = tqdm(desc="Scraping books", total=total)
        rows = soup.select("table#books tbody tr")
        for row in rows:
            review_id = row.attrs["id"][len("review_") :]
            if review_id in relevant_ids:
                date = row.select(".date_read_value")
                if date:
                    reviews[review_id]["read_at"] = dateutil.parser.parse(
                        date[0].text, default=dt.date(2019, 1, 1)
                    )
                    date_counter += 1
            progress_bar.update(1)
        if not soup.select("a[rel=next]") or progress_bar.n >= progress_bar.total:
            break
    progress_bar.close()
    click.echo("Found {} previously missing read dates.".format(date_counter))


def save_authors(db, authors):
    total = len(authors)
    progress_bar = tqdm(total=total, desc="Saving authors")
    db["authors"].insert_all(authors, pk="id", replace=True)
    progress_bar.update(total)
    progress_bar.close()


def save_books(db, books):
    authors_table = db.table("authors", pk="id")
    for book in tqdm(books, desc="Saving books  "):
        authors = book.pop("authors", [])
        db["books"].insert(book, pk="id", replace=True).m2m(authors_table, authors)


def save_reviews(db, reviews):
    shelves_table = db.table("shelves", pk="id")
    for review in tqdm(reviews, desc="Saving reviews"):
        shelves = review.pop("shelves", [])
        db["reviews"].insert(
            review,
            pk="id",
            foreign_keys=(("book_id", "books", "id"), ("user_id", "users", "id")),
            alter=True,
            replace=True,
        ).m2m(shelves_table, shelves)


def _get_author_from_data(author):
    return {"id": author.find("id").text, "name": author.find("name").text}


def _get_book_from_data(book, authors):
    series = None
    series_position = None
    title = book.find("title").text
    title_series = book.find("title_without_series").text
    if title != title_series:
        series_with_position = title[len(title_series) :].strip(" ()")
        if "#" in series_with_position:
            series, series_position = series_with_position.split("#", maxsplit=1)
        elif "Book" in series_with_position:
            series, series_position = series_with_position.split("Book", maxsplit=1)
        else:
            series = series_with_position
            series_position = ""
        series = series.strip(", ")
        series_position = series_position.strip(", #")
        title = title_series
    publication_year = book.find("publication_year").text
    publication_date = None
    if publication_year:
        publication_date = dt.date(
            int(book.find("publication_year").text),
            int(book.find("publication_month").text or 1),
            int(book.find("publication_day").text or 1),
        )
    return {
        "id": book.find("id").text,
        "isbn": book.find("isbn").text,
        "isbn13": book.find("isbn13").text,
        "title": title,
        "series": series,
        "series_position": series_position,
        "pages": book.find("num_pages").text,
        "publisher": book.find("publisher").text,
        "publication_date": publication_date,
        "description": book.find("description").text,
        "image_url": book.find("image_url").text,
        "authors": authors,
    }


def _get_review_from_data(review, user_id):
    rating = review.find("rating").text
    rating = int(rating) or None if rating else None
    result = {
        "id": review.find("id").text,
        "book_id": review.find("book").find("id").text,
        "user_id": user_id,
        "rating": rating,
        "text": (review.find("body").text or "").strip(),
        "shelves": [
            {
                "name": shelf.attrib.get("name"),
                "id": shelf.attrib.get("id"),
                "user_id": user_id,
            }
            for shelf in (review.find("shelves") or [])
        ],
    }
    for key in ("started_at", "read_at", "date_added", "date_updated"):
        date = maybe_date(review.find(key).text)
        if date:
            result[key] = date
    return result


def fetch_user_id(username, force_online=False, db=None) -> str:
    """We can look up a user ID given a (public vanity) username.

    We go to that profile page, and observe the redirect target. If we have the
    user in question in our database, we just return the known value, since
    user IDs are assumed to be stable. The vanity URL redirects to a URL ending
    in <user_id>-<username>."""
    if not force_online and db:
        user = db["users"].get(username=username)
        if user:
            return user.id
    click.echo("Fetching user details.")
    url = username if username.startswith("http") else BASE_URL + username
    response = requests.get(url)
    response.raise_for_status()
    if "/author/" in username:
        soup = bs4.BeautifulSoup(response.content.decode(), "html.parser")
        url = soup.select("link[rel=alternate][title=Bookshelves]")[0].attrs["href"]
    else:
        url = response.request.url
    result = url.strip("/").split("/")[-1].split("-")[0]
    if not result.isdigit():
        error("Cannot find user ID for {}".format(response.request.url))
    return result


def fetch_user_and_shelves(user_id, token, db) -> dict:
    with suppress(TypeError):
        user = db["users"].get(id=user_id)
        shelves = db["shelves"].rows_where("user_id = ?", [user_id])
        if user and all(user.values()) and shelves:
            user["shelves"] = shelves
            return user
    click.secho("Fetching shelves.")
    response = requests.get(
        BASE_URL + "user/show/{}.xml".format(user_id), {"key": token}
    )
    response.raise_for_status()
    to_root = ET.fromstring(response.content.decode())
    user = to_root.find("user")
    shelves = user.find("user_shelves")
    if not shelves:
        error("This user's shelves and reviews are private, and cannot be fetched.")
    user = {
        "id": user.find("id").text,
        "name": user.find("name").text,
        "username": user.find("user_name").text,
        "shelves": [
            {"id": shelf.find("id").text, "name": shelf.find("name").text}
            for shelf in shelves
        ],
    }
    save_user(db, user)


def save_user(db, user):
    save_data = {key: user.get(key) for key in ["id", "name", "username"]}
    pk = db["users"].insert(save_data, pk="id", alter=True, replace=True).last_pk
    for shelf in user.get("shelves", []):
        save_shelf(db, shelf, user["id"])
    return pk


def save_shelf(db, shelf, user_id):
    save_data = {key: shelf.get(key) for key in ["id", "name"]}
    save_data["user_id"] = user_id
    return (
        db["shelves"]
        .insert(
            save_data, foreign_keys=(("user_id", "users", "id"),), pk="id", alter=True, replace=True
        )
        .last_pk
    )


def maybe_date(value):
    if value:
        return dateutil.parser.parse(value)
    return None
