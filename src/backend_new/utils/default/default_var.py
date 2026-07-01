DEFAULT_CONFIG = {
    "version": "1.0.0",
    "init": False,

    "downloader": {
        "view_limit": 10,
        "retry_count": 3,
        "retry_sleep": 5,

        "current_song_always_first_youtube_result": True,
        "query_always_first_youtube_result": True
    },

    "spotify_downloader": {
        "output_format": {
            "duration": True,
            "album": True,
            "popularity": True
        },
        "token": True
    },

    "youtube_downloader": {
        "use_cookies": False,
        "output_format": {
            "duration": True,
            "uploader": True,
            "view_count": True,
            "id": True
        }
    },

    "skip_processes": {
        "download_song": False,
        "genius_metadata": False,
        "vocal_separation": False,
        "split_and_tag": False,
        "translate_lyrics": False
    }
}
DEFAULT_ENV_VARS = [
    "SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET", "SPOTIFY_REDIRECT_URI", "GENIUS_ACCESS_TOKEN"
]
DEFAULT_DICTS_MESSAGE = """# Please download these recommended dictionaries:

- [JA-EN] **jitendex-yomitan**
  - This is the main structural dictionary, providing most of the comprehensive English definitions
- [JA-JA Names] **JMnedict**
  - Contains real-world words
    - Names
    - Places
    - Pop-Culture Titles
    - etc.
- [JA-JA Encyclopedia] **PixivLight**
  - Contains more modern / slang vocabularies
  - Catches internet memes
  - Vocaloid tracking terms
  - Modern abbreviations
  - Comtemporary subculture jargon
- [JA-JA Onomatopoeia] **擬音語・擬態語辞典**
  - Contains mimetic and sound-effect words (onomatopoeia)
    - e.g. gira-gira
- [JA-JA Yoji] **四字熟語の百科事典**
  - Dedicated to four-character idiomatic compounds
  - Often appears in dramatic or poetic song hooks
- [JA-JA] **ことわざ・慣用句の百科事典**
  - Handles traditional proverbs and idiomatic expressions
  - Can possibly provide symbolic meaning behind a phrase instead of a literal translation
- [JA-JA] **大辞林 第四版**
  - One of the best modern dictionaries for breaking down:
    - Compound verbs
    - Subtle semantic shifts
    - Artistic nuances
    - etc.

# Sources:
- https://github.com/MarvNC/yomitan-dictionaries

# How to install
- To install these dictionaries, please download the dictionaries and place them in the "dicts" directory
- The app will automatically extract the .zip files if not yet done and automatically detect each dictionary each run
"""
DEFAULT_DICTS = ["PixivLight",
              "JMnedict",
              "jitendex-yomitan",
              "擬音語・擬態語辞典",
              "四字熟語の百科事典",
              "ことわざ・慣用句の百科事典",
              "大辞林　第四版"]
DEFAULT_DICTS_FOLDER_LINK = 'https://drive.google.com/drive/folders/1xURpMJN7HTtSLuVs9ZtIbE7MDRCdoU29?usp=drive_link'
