from datetime import datetime
from enum import Enum
from operator import attrgetter
from typing import NamedTuple

from decouple import config
import requests
import requests_cache
import typer

OMDB_API_KEY = config("OMDB_API_KEY")
RAPID_API_KEY = config("RAPID_API_KEY")

OMDB_API_BASE_URL = f"http://omdbapi.com/?apikey={OMDB_API_KEY}"
RAPID_API_BASE_URL = "streaming-availability.p.rapidapi.com"
RAPID_API_URL = f"https://{RAPID_API_BASE_URL}/get/basic"

DEFAULT_COUNTRY = "es"
ENGLISH = "en"

requests_cache.install_cache("cache.db", backend="sqlite", expire_after=10)

app = typer.Typer()


class Movie(NamedTuple):
    title: str
    year: str
    imdb_id: str


class StreamingMovie(NamedTuple):
    title: str
    service: str
    link: str
    added: datetime
    leaving: datetime


class MovieType(str, Enum):
    movie = "movie"
    series = "series"
    episode = "episode"


@app.command("search")
def search_movie_by_title(
    title: str = typer.Argument(..., help="The title of the movie"),
    year: str = typer.Option(None, help="The year of the movie"),
    kind: MovieType = typer.Option(MovieType.movie, help="The type of movie"),
):
    url = OMDB_API_BASE_URL + f"&s={title}"

    if year is not None:
        url += f"&y={year}"

    if kind is not None:
        url += f"&type={kind}"

    resp = requests.get(url)

    error = resp.json().get("Error")
    if error is not None:
        raise Exception(error)

    movies = [
        Movie(title=row["Title"], year=row["Year"], imdb_id=row["imdbID"])
        for row in resp.json()["Search"]
    ]

    for movie in sorted(movies, key=attrgetter("year")):
        print(movie)


@app.command("where")
def get_movie_data(
    imdb_id: str = typer.Argument(..., help="The IMDB id of the movie"),
    country: str = typer.Option(DEFAULT_COUNTRY, help="The country you're in"),
):
    params = {
        "imdb_id": imdb_id, "country": country, "output_language": ENGLISH
    }
    headers = {
        "X-RapidAPI-Key": RAPID_API_KEY,
        "X-RapidAPI-Host": RAPID_API_BASE_URL,
    }
    resp = requests.get(RAPID_API_URL, headers=headers, params=params)

    title = resp.json()["title"]

    for key, value in resp.json()["streamingInfo"].items():
        added = datetime.fromtimestamp(
            value[country]["added"]
        ) if value[country]["added"] > 0 else 0

        leaving = datetime.fromtimestamp(
            value[country]["leaving"]
        ) if value[country]["leaving"] > 0 else 0

        movie = StreamingMovie(
            title=title,
            service=key,
            link=value[country]["link"],
            added=added,
            leaving=leaving
        )
        print(movie)


if __name__ == "__main__":
    app()
