import os
import requests
from dotenv import load_dotenv
import json
from concurrent.futures import ThreadPoolExecutor
from lyricsgenius import Genius
import re
from urllib.parse import quote
import itertools
import difflib
import globalfuncs

# global config
with open('../config/globalconfig.json', 'r') as f:
    config = json.load(f)

rem_brak = bool(config["remove_brackets_genius_lyr_search"])
console_out = bool(config["console_out_genius_lyr_search"])

load_dotenv()

# genius data scraper setup
genius = Genius(os.getenv("LGENIUS_CLIENT_ACCESS_TOKEN"))
genius_no_headers = Genius(os.getenv("LGENIUS_CLIENT_ACCESS_TOKEN"), remove_section_headers=True)

# tokens
genius_client_access_token = os.getenv('GENIUS_CLIENT_ACCESS_TOKEN')

# genius api link
genius_api_base = 'https://api.genius.com/'

# main functions
# for the multi-processing thread so it can call faster
def fetch_search_for_multithreadding(hit_id: str, check_for_artist_title: bool, filename: str) -> dict:
    """
    Checks if song id of song matches song title given using title and artist checks
    :param hit_id: Song ID to check
    :param check_for_artist_title: A more accurate system to check if the song is right, recommended to check artist title
    :param filename: The title and artist for the algorithm to check, in this format. "Title - Artist"
    :return:
    """
    headers = {'Authorization': 'Bearer ' + genius_client_access_token}

    try:
        response = requests.get(f"{genius_api_base}songs/{hit_id}", headers=headers)
        data = response.json()

        # find correct data
        if check_for_artist_title:
            match = re.match(r"^(.*?)\s*-\s*(.*)$", filename)
            if match:
                song, artist = match.groups()
            else:
                raise Exception("Regex failure")

            if difflib.SequenceMatcher(None, str(data['response']['song']['primary_artist_names']), str(artist)).ratio() < 0.3:
                globalfuncs.logger.verbose(f"Artist fail -> {data['response']['song']['primary_artist_names']} | {artist}")
                return None
            elif difflib.SequenceMatcher(None, str(data['response']['song']['full_title']), str(song)).ratio() < 0.1:
                globalfuncs.logger.verbose(f"Title 1 fail -> {data['response']['song']['full_title']} | {song}")
                return None
            elif difflib.SequenceMatcher(None, str(data['response']['song']['title']), str(song)).ratio() < 0.1:
                globalfuncs.logger.verbose(f"Title 2 fail -> {data['response']['song']['title']} | {song}")
                return None

        if data['response']['song']['language'] == 'ja':
            return data['response']['song']['api_path']
        else:
            # return None if no match
            return None

    # error handling
    except requests.exceptions.RequestException as e:
        globalfuncs.logger.error(e)


def genius_get_song_id_jp(song: str, removepar=rem_brak, consoleout=console_out) -> dict:
    """
    Finds the song ID of a song using the title and artist
    :param song: Title and artist name in this format, "Title - Artist"
    :param removepar: Removes parentheses from the input
    :param consoleout: Outputs console information
    :return: The song ID
    """
    if removepar:
        song = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', song)

    if consoleout:
        globalfuncs.logger.verbose(f"{song} | {quote(song, safe='')}")

    url_search = f"{genius_api_base}search?q={song}"

    # call api
    header = {'Authorization': 'Bearer ' + genius_client_access_token}

    # try to get song info using top result
    try:
        response = requests.get(url_search, headers=header)
        data = response.json()
        hits = data['response']['hits']
        hit_list = [hit['result']['id'] for hit in hits]

        # multi-threading setup
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(fetch_search_for_multithreadding, hit_list, itertools.repeat(True), itertools.repeat(song)))

        # remove nones
        results = [result for result in results if result is not None]

        # if no matches found, return None
        if len(results) == 0:
            raise Exception(f"Song not found: {song}")

        return results[0]
    # error handling
    except requests.exceptions.RequestException as e:
        globalfuncs.logger.error(e)

def genius_get_song_id_multi(song: str, search_filter: bool, consoleout=console_out) -> dict:
    if consoleout:
        globalfuncs.logger.verbose(f"{song} | {quote(song, safe='')}")

    url = "https://genius.com/api/search/multi"
    params = {'q': song}

    try:
        response = requests.get(url, params=params).json()
    except requests.exceptions.RequestException as e:
        globalfuncs.logger.error(e)
        raise Exception

    hits = response["response"]["sections"]
    hits = [hit for hit in hits if hit['type'] == "top_hit" or hit['type'] == 'song']

    hit_list = []

    for hit in hits:
        for sub_hit in hit['hits']:
            hit_list.append(sub_hit['result']['id'])

    with ThreadPoolExecutor(max_workers=20) as executor:
        results = list(executor.map(fetch_search_for_multithreadding, hit_list, itertools.repeat(search_filter), itertools.repeat(song)))

    # remove nones
    results = [result for result in results if result is not None]

    # if no matches found, return None
    if len(results) == 0:
        raise Exception(f"Song not found: {song}")

    if results is None:
        raise Exception("Song not found")

    globalfuncs.logger.success(f"{results}")

    return results[0]

def genius_get_translated(song_id):
    header = {'Authorization': 'Bearer ' + genius_client_access_token}

    # remove first slash
    song_id = song_id[1:]

    try:
        response = requests.get(f"{genius_api_base}{song_id}", headers=header)
        data = response.json()

        # many many digging through layers
        translated_song_id = data['response']['song']['song_relationships']

        list_of_translations = []

        # find translation area
        for item in translated_song_id:
            if item['relationship_type'] == 'translations':
                list_of_translations = item['songs']
                list_of_translations = [item for item in list_of_translations]

        # find english translation area and output api_path
        for item in list_of_translations:
            if item['primary_artist_names'] == "Genius English Translations":
                globalfuncs.logger.success(f"Obtained English Translation: {str(item['title'])} | {str(item['api_path'])}")
                return item['api_path']

        # if nothing is found
        raise Exception(f"Song not found: {song_id}")

    # error handling
    except requests.exceptions.RequestException as e:
        globalfuncs.logger.error(e)

def extract_lyrics(api_path: str) -> tuple[str, str]:
    # remove all non numbered characters
    api_path = int("".join([char for char in api_path if char.isdigit()]))

    # use web scraper to get lyrics
    song = genius.search_song(None, None, api_path)
    song_no_headers = genius_no_headers.search_song(None, None, api_path)
    return song.lyrics, song_no_headers.lyrics