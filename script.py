from datetime import datetime
from operator import attrgetter
from typing import NamedTuple

from decouple import config
import requests
import requests_cache

OMDB_API_KEY = config("OMDB_API_KEY")
OMDB_API_BASE_URL = f"http://omdbapi.com/?apikey={OMDB_API_KEY}"
RAPID_API_KEY = config("RAPID_API_KEY")
RAPID_API_BASE_URL = "streaming-availability.p.rapidapi.com"
RAPID_API_URL = f"https://{RAPID_API_BASE_URL}/get/basic"
HEADERS = {
    "X-RapidAPI-Key": RAPID_API_KEY,
    "X-RapidAPI-Host": RAPID_API_BASE_URL,
}
DEFAULT_COUNTRY = "es"
DEFAULT_LANGUAGE = "en"

requests_cache.install_cache("cache.db", backend="sqlite", expire_after=10)


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


def search_movie_by_title(title, year=None, type_=None):
    url = OMDB_API_BASE_URL + f"&s={title}"
    if year is not None:
        url += f"&y={year}"
    if type_ is not None:
        url += f"&type={type_}"
    resp = requests.get(url)
    error = resp.json().get("Error")
    if error is not None:
        raise Exception(error)
    movies = [
        Movie(title=row["Title"], year=row["Year"], imdb_id=row["imdbID"])
        for row in resp.json()["Search"]
    ]
    return sorted(movies, key=attrgetter("year"))


def get_movie_data(imdb_id, country=DEFAULT_COUNTRY, language=DEFAULT_LANGUAGE):
    params = {"imdb_id": imdb_id, "country": country, "output_language": language}
    resp = requests.get(RAPID_API_URL, headers=HEADERS, params=params)
    title = resp.json()["title"]
    return [
        StreamingMovie(
            title=title,
            service=key,
            link=value[country]["link"],
            added=datetime.fromtimestamp(value[country]["added"])
            if value[country]["added"] > 0
            else 0,
            leaving=datetime.fromtimestamp(value[country]["leaving"])
            if value[country]["leaving"] > 0
            else 0,
        )
        for key, value in resp.json()["streamingInfo"].items()
    ]


if __name__ == "__main__":
    from pprint import pprint as pp
    import sys

    title = sys.argv[1]
    if title == "movie":
        imdb_id = sys.argv[2]
        ret = get_movie_data(imdb_id)
        pp(ret)
    else:
        year = sys.argv[2] if len(sys.argv) > 2 else None
        type_ = sys.argv[3] if len(sys.argv) > 3 else None
        ret = search_movie_by_title(title, year, type_)
        pp(ret)
