class Downloader:
    def __init__(self, spotify_client_id: str = '', spotify_client_secret: str = '') -> None:
        if spotify_client_id == '' or spotify_client_secret == '':
            raise Exception('Spotify client id and secret are required')