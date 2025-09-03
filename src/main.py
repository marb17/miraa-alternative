import lyricextract
import vocalsep
import ytdown
import lyricstimestamper
import json
import shutil
import llmfortitleextract
import splittag
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
def main(url, skip_vox_sep=True, skip_lyrics=False, skip_transcribe=False):
    # download audio
    print("Starting Download of Song")
    filename, base58path = ytdown.youtube_download_audio(url)
    print("Finished downloading")

    print("-" * console_width)

    # relative paths for audios
    filepath = f"../database/songs/{base58path}/audio.wav"
    filepath_vocal = f"../database/songs/{base58path}/audio_vocals.wav"

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
        jp_song_id = None

        # Define your fallback attempts
        fallbacks = [
            lambda: lyricextract.genius_get_song_id_jp(filename),
            lambda: lyricextract.genius_get_song_id_jp(llm.get_title_from_song(filename, False, True)),
            lambda: lyricextract.genius_get_song_id_jp(llm.get_title_from_song(filename, True, True)),
            lambda: lyricextract.genius_get_song_id_jp(llm.get_title_from_song(filename, True, False)),
            lambda: lyricextract.genius_get_song_id_multi(llm.get_title_from_song(filename, False, False), True),
            lambda: lyricextract.genius_get_song_id_multi(filename, False),
        ]

        # If llm.create_model() is required before some calls
        # ! UNCOMMENT AFTER DONE TESTING
        # llm.create_model()
        #
        # for attempt in fallbacks:
        #     try:
        #         jp_song_id = attempt()
        #         if jp_song_id:  # success
        #             break
        #     except Exception:
        #         continue
        #     raise Exception("Failed to get song id from audio file")
        #
        # llm.clear_model()

        # ! REMOVE AFTER TESTING
        jp_song_id = '/songs/4844746'

        print("Genius Link Obtained: ", jp_song_id, " | ", filename)
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

    # split the lyrics
    jp_lyrics = jp_lyrics.split('\n')

    print("-" * console_width)

    print(jp_lyrics)

    tagged_lyrics = []
    full_tagged_lyrics = []

    # tag and get pos of word
    for line in jp_lyrics:
        if '[' in line or line == '':
            tagged_lyrics.append(None)
            full_tagged_lyrics.append(None)
        else:
            tagged_lyrics.append(splittag.parse_jp_text(line))
            full_tagged_lyrics.append(splittag.full_parse_jp_text(line))

    # finding all types of particles for debug
    all_types_of_pos = set()

    # convert jp pos to eng pos
    for line in full_tagged_lyrics:
        if line is None:
            continue
        for word in line:
            all_types_of_pos.add(word[1]) # debug line
            word[1] = splittag.translate_pos(word[1])

    tagged_lyrics = json.dumps(tagged_lyrics)
    full_tagged_lyrics = json.dumps(full_tagged_lyrics)

    print(tagged_lyrics)
    print(full_tagged_lyrics)
    # print(all_types_of_pos)

if __name__ == '__main__':
    # main('https://www.youtube.com/watch?v=QnkqCv0dZTk')
    # main('youtube.com/watch?v=ZRtdQ81jPUQ')
    main('https://www.youtube.com/watch?v=Mhl9FaxiQ_E')