import lyricextract
import vocalsep
import ytdown
import lyricstimestamper
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from globalfuncs import base58_to_str, str_to_base58

# global config
with open('globalconfig.json', 'r') as f:
    config = json.load(f)

console_line_breaks = bool(config['console_print_line_separators'])

# console line seperator thing
try:
    terminal_size = shutil.get_terminal_size()
    console_width = terminal_size.columns
except OSError:
    print("Could not determine terminal size. Running in a non-terminal environment or terminal does not support size query.")
    console_width = 20

# main loop
def main(url, skip_vox_sep=True, skip_lyrics=False, skip_transcribe=True):
    # download audio
    print("Starting Download of Song")
    filename, base58path = ytdown.youtube_download_audio(url)
    print("Finished downloading")

    print("-" * console_width)

    # relative paths for audios
    filepath = f"../database/songs/{base58path}/{base58path}.wav"
    filepath_vocal = f"../database/songs/{base58path}/{base58path}_vocals.wav"

    # separate vox
    if not skip_vox_sep:
        print("Starting Vox Separation")
        vocalsep.separate_audio(filepath)
        print("Finished Vox Separation")
    else:
        print("Skipping Vox Separation")

    print("-" * console_width)

    # get time stampped transcription for video sync
    if not skip_transcribe:
        print("Start timestamp words")
        timestampped_words = lyricstimestamper.transcribe(filepath_vocal)
        print("Finished timestamp words")
    else:
        print("Skipping timestamp words")

    print("-" * console_width)

    # retrieve lyrics (jp and en)
    if not skip_lyrics:
        try:
            print("Getting Lyrics (Japanese % English)")
            jp_song_id = lyricextract.genius_get_song_id_jp(filename)
        except Exception:
            # TODO add llm function

        print(jp_song_id, filename)
        en_song_id = lyricextract.genius_get_translated(jp_song_id)

        # multithread for faster load times
        with ThreadPoolExecutor() as executor:
            f_jp_lyrics = executor.submit(lyricextract.extract_lyrics, jp_song_id)
            f_en_lyrics = executor.submit(lyricextract.extract_lyrics, en_song_id)

            jp_lyrics = f_jp_lyrics.result()
            en_lyrics = f_en_lyrics.result()

        print("Finished Lyrics")
    else:
        print("Skipping Lyrics")

    # split the
    jp_lyrics = jp_lyrics.split('\n')

    print("-" * console_width)

if __name__ == '__main__':
    # main('https://www.youtube.com/watch?v=QnkqCv0dZTk')
    main('youtube.com/watch?v=ZRtdQ81jPUQ')