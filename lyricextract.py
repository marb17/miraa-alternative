import os
import requests
from dotenv import load_dotenv
import json
from concurrent.futures import ThreadPoolExecutor
from lyricsgenius import Genius
import re

# global config
with open('globalconfig.json', 'r') as f:
    config = json.load(f)

rem_brak = bool(config["remove_brackets_genius_lyr_search"])


load_dotenv()

# genius data scraper setup
genius = Genius(os.getenv("LGENIUS_CLIENT_ACCESS_TOKEN"))

# tokens
genius_client_access_token = os.getenv('GENIUS_CLIENT_ACCESS_TOKEN')

# genius api link
genius_api_base = 'https://api.genius.com/'

# for the multi-processing thread so it can call faster
def fetch_search_for_multithreadding(hit_id: str) -> dict:
    headers = {'Authorization': 'Bearer ' + genius_client_access_token}

    try:
        response = requests.get(f"{genius_api_base}songs/{hit_id}", headers=headers)
        data = response.json()

        # find correct data
        if data['response']['song']['language'] == 'ja':
            return data['response']['song']['api_path']
        else:
            # return None if no match
            return None

    # error handling
    except requests.exceptions.RequestException as e:
        print(e)


def genius_get_song_id_jp(song: str, removepar=rem_brak) -> dict:
    if removepar:
        song = re.sub(r'\([^)]*\)|\[[^\]]*\]', '', song)

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
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(fetch_search_for_multithreadding, hit_list))

        # remove nones
        results = [result for result in results if result is not None]

        # if no matches found, return None
        if len(results) == 0:
            return None

        return results[0]
    # error handling
    except requests.exceptions.RequestException as e:
        print(e)

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
                return item['api_path']

        # if nothing is found
        return None

    # error handling
    except requests.exceptions.RequestException as e:
        print(e)

def find_url_from_api_path(api_path: int) -> str:
    header = {'Authorization': 'Bearer ' + genius_client_access_token}

    # remove first slash
    song_id = api_path[1:]

    try:
        print(f"{genius_api_base}{song_id}")
        response = requests.get(f"{genius_api_base}{song_id}", headers=header)
        data = response.json()

        # find url from the layers
        return data['response']['song']['url']
    except requests.exceptions.RequestException as e:
        print(e)

def extract_lyrics(api_path: str) -> str:
    # remove all non numbered characters
    api_path = int("".join([char for char in api_path if char.isdigit()]))

    # use web scraper to get lyrics
    song = genius.search_song(None, None, api_path)
    return song.lyrics

if __name__ == '__main__':
    pass