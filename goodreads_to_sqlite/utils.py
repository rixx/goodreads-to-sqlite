import datetime as dt
import xml.etree.ElementTree as ET
from contextlib import suppress

import click
import dateutil.parser
import requests
from tqdm import tqdm

BASE_URL = "https://www.goodreads.com/"


def fetch_books(db, user_id, token):
    # TODO: ignore things with old last_modified, notify via click
    last_row = list(
        db["reviews"].rows_where("user_id = ? order by date_updated limit 1", [user_id])
    )
    last_timestamp = maybe_date(last_row[0]["date_updated"]) if last_row else None

    url = BASE_URL + "review/list/{}.xml".format(user_id)
    params = {
        "key": "uop3BTpOxtYgCBy5Urwjqg",
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
            rating = review.find("rating").text
            if rating:
                rating = int(rating) or None
            reviews[review_id] = {
                "id": review_id,
                "book_id": book_id,
                "user_id": user_id,
                "rating": rating,
                "text": (review.find("body").text or "").strip(),
                "shelves": [
                    {"name": shelf.attrib.get("name"), "id": shelf.attrib.get("id")}
                    for shelf in (review.find("shelves") or [])
                ],
            }
            for key in ("started_at", "read_at", "date_added", "date_updated"):
                date = maybe_date(review.find(key))
                if date:
                    reviews[review_id][key] = date
            progress_bar.update(1)

    progress_bar.close()
    save_authors(db, list(authors.values()))
    save_books(db, list(books.values()))
    save_reviews(db, list(reviews.values()))
    return review_data.attrib


def save_authors(db, authors):
    total = len(authors)
    progress_bar = tqdm(total=total, desc="Saving authors")
    db["authors"].upsert_all(authors, pk="id", column_order=("id", "name"))
    progress_bar.update(total)
    progress_bar.close()


def save_books(db, books):
    authors_table = db.table("authors", pk="id")
    for book in tqdm(books, desc="Saving books  "):
        authors = book.pop("authors", [])
        db["books"].upsert(
            book,
            pk="id",
            column_order=(
                "id",
                "isbn",
                "isbn13",
                "title",
                "series",
                "series_position",
                "pages",
                "publisher",
                "publication_date",
                "description",
                "image_url",
            ),
        ).m2m(authors_table, authors)


def save_reviews(db, reviews):
    shelves_table = db.table("shelves", pk="id")
    for review in tqdm(reviews, desc="Saving reviews"):
        shelves = review.pop("shelves", [])
        db["reviews"].upsert(
            review,
            pk="id",
            column_order=(
                "id",
                "book_id",
                "user_id",
                "rating",
                "text",
                "started_at",
                "read_at",
                "date_added",
                "date_updated",
            ),
            foreign_keys=(("book_id", "books", "id"), ("user_id", "users", "id")),
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


def fetch_user_id(username, force_online=False, db=None):
    if not force_online and db:
        user = db["users"].get(username=username)
        if user:
            return user.id
    url = BASE_URL + username
    response = requests.get(url)
    response.raise_for_status()
    if response.request.url == url:
        raise Exception("Cannot find user ID for username {}".format(username))
    last_part = response.request.url.strip("/").split("/")[-1]
    return last_part.split("-")[0]


def fetch_user(user_id, token, force_online=False, db=None):
    if not force_online and db:
        with suppress(TypeError):
            user = db["users"].get(id=user_id)
            shelves = db["shelves"].rows_where("user_id = ?", [user_id])
            if user and all(user.values()) and shelves:
                return user
    response = requests.get(
        BASE_URL + "user/show/{}.xml".format(user_id), {"key": token}
    )
    response.raise_for_status()
    to_root = ET.fromstring(response.content.decode())
    user = to_root.find("user")
    shelves = user.find("user_shelves")
    return {
        "id": user.find("id").text,
        "name": user.find("name").text,
        "username": user.find("user_name").text,
        "shelves": [
            {"id": shelf.find("id").text, "name": shelf.find("name").text}
            for shelf in shelves
        ],
    }


def save_user(db, user):
    save_data = {key: user.get(key) for key in ["id", "name", "username"]}
    pk = (
        db["users"]
        .upsert(save_data, pk="id", column_order=("id", "name", "username"), alter=True)
        .last_pk
    )
    for shelf in user.get("shelves", []):
        save_shelf(db, shelf, user["id"])
    return pk


def save_shelf(db, shelf, user_id):
    save_data = {key: shelf.get(key) for key in ["id", "name"]}
    save_data["user_id"] = user_id
    return (
        db["shelves"]
        .upsert(
            save_data,
            foreign_keys=(("user_id", "users", "id"),),
            pk="id",
            column_order=("id", "name"),
            alter=True,
        )
        .last_pk
    )


def maybe_date(value):
    if value:
        return dateutil.parser.parse(value)
    return None
