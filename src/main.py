import lyricextract
import vocalsep
import ytdown
import lyricstimestamper
import llmfortitleextract
import splittag
import dictlookup

from concurrent.futures import ThreadPoolExecutor
import globalfuncs
import json
import shutil

'''
Green: Success
Yellow: Warn / Fallback
Cyan: Check Fail
Red: Error
Blue: On Process
Magenta: Info
'''

# global config
with open('globalconfig.json', 'r') as f:
    config = json.load(f)

console_line_breaks = bool(config['console_print_line_separators'])

# console line seperator thing
try:
    terminal_size = shutil.get_terminal_size()
    console_width = terminal_size.columns
except OSError:
    globalfuncs.logger.error("Could not determine terminal size. Running in a non-terminal environment or terminal does not support size query.")
    console_width = 20

# main loop
def main(url: str, use_genius: bool, skip_download=True, skip_vox_sep=False, skip_lyrics=True, skip_transcribe=True, skip_dict_lookup=True):
    """
    Returns JSON file, includes: lyrics, timestamps, translations, meanings, POS
    :param url: Input the URL of the song (YouTube Only)
    :param use_genius: if True, uses Genius API to get lyrics, otherwise uses AI transcription (unreliable)
    :param skip_download:
    :param skip_vox_sep:
    :param skip_lyrics:
    :param skip_transcribe:
    :param skip_dict_lookup:
    :return:
    """

    # download audio
    if not skip_download:
        globalfuncs.logger.info("Starting Download of Song")
        filename, base58path = ytdown.youtube_download_audio(url)
        globalfuncs.logger.success("Finished downloading")
    else:
        globalfuncs.logger.success("Skipping Youtube Download")
        base58path, filename = '6Zgp7o1Mfz3R6ANKskxuimK1j1XwVGA6N7kuaPDb3GrdT2EK8HzFbcdorugKBBU89YP9nL1EHjouDo2XrSBSZKkSS9cnV5eH2nne5p34o1YqXr6Fi3C5AfirERVz5R1d2M', 'GIVEN (ギヴン) - Fuyu no hanashi (冬のはな) (A Winter Story) (Kan|Rom|Eng) Lyrics/歌詞'

    globalfuncs.logger.plain(f"{"-" * console_width}")

    # relative paths for audios
    filepath = f"../database/songs/{base58path}/audio.wav"
    filepath_vocal = f"../database/songs/{base58path}/audio_vocals.wav"

    # separate vox
    if not skip_vox_sep:
        globalfuncs.logger.info("Starting Vox Separation")
        vocalsep.separate_audio(filepath)
        globalfuncs.logger.success("Finished Vox Separation")
    else:
        globalfuncs.logger.success("Skipping Vox Separation")

    globalfuncs.logger.plain(f"{"-" * console_width}")

    # get time stampped transcription for video sync
    if not skip_transcribe:
        globalfuncs.logger.info("Start timestamp words")
        vox_timestampped_words, vox_lyrics = lyricstimestamper.transcribe(filepath_vocal)

        globalfuncs.logger.verbose(str(vox_timestampped_words))
        globalfuncs.logger.verbose(str(vox_lyrics))

        globalfuncs.logger.success("Finished timestamp words")
    else:
        globalfuncs.logger.success("Skipping timestamp words")

    globalfuncs.logger.plain(f"{"-" * console_width}")

    # retrieve lyrics (jp and en)
    if not skip_lyrics:
        if use_genius == 'genius':
            globalfuncs.logger.verbose('Using Genius Lyrics')

            jp_song_id = None

            fallbacks = [
                lambda: lyricextract.genius_get_song_id_jp(filename),
                lambda: lyricextract.genius_get_song_id_jp(llmfortitleextract.get_title_from_song(filename, False, True)),
                lambda: lyricextract.genius_get_song_id_jp(llmfortitleextract.get_title_from_song(filename, True, True)),
                lambda: lyricextract.genius_get_song_id_jp(llmfortitleextract.get_title_from_song(filename, True, False)),
                lambda: lyricextract.genius_get_song_id_multi(llmfortitleextract.get_title_from_song(filename, False, False), True),
                lambda: lyricextract.genius_get_song_id_multi(filename, False),
            ]

            # ! UNCOMMENT AFTER DEBUGGING
            # llmfortitleextract.create_model()
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
            # llmfortitleextract.clear_model()

            # ! REMOVE AFTER DEBUGGING
            jp_song_id = '/songs/8842895'

            globalfuncs.logger.success(f"Genius Link Obtained: {jp_song_id} | {filename}")
            en_song_id = lyricextract.genius_get_translated(jp_song_id)

            # multithread for faster load times
            with ThreadPoolExecutor() as executor:
                f_jp_lyrics = executor.submit(lyricextract.extract_lyrics, jp_song_id)
                f_en_lyrics = executor.submit(lyricextract.extract_lyrics, en_song_id)

                jp_lyrics = f_jp_lyrics.result()
                en_lyrics = f_en_lyrics.result()

                # split the lyrics
                unsplit_jp_lyrics = jp_lyrics
                jp_lyrics = jp_lyrics.split('\n')

            globalfuncs.logger.success("Finished Lyrics")
        elif use_genius == 'ai':
            globalfuncs.logger.verbose('Using AI Transcription')

            jp_lyrics = []
            unsplit_jp_lyrics = ''
            for lyric in vox_lyrics:
                jp_lyrics.append(lyric[2])
                unsplit_jp_lyrics = unsplit_jp_lyrics + lyric[2] + '\n'

            # TODO make llm
    else:
        globalfuncs.logger.success("Skipping Lyrics")

    globalfuncs.logger.plain(f"{"-" * console_width}")

    globalfuncs.logger.verbose(str(jp_lyrics))
    globalfuncs.logger.verbose(str(unsplit_jp_lyrics))

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

    # tagged_lyrics = json.dumps(tagged_lyrics)
    # full_tagged_lyrics = json.dumps(full_tagged_lyrics)

    globalfuncs.logger.verbose(str(tagged_lyrics))
    globalfuncs.logger.verbose(str(full_tagged_lyrics))
    # globalfuncs.logger.verbose(all_types_of_pos)

    globalfuncs.logger.plain(f"{"-" * console_width}")

    if not skip_dict_lookup:
        globalfuncs.logger.info(f"Getting definitions of each phrase")
        dict_lookup_res = dictlookup.get_meaning_full(jp_lyrics)
        globalfuncs.logger.verbose(str(dict_lookup_res))
        globalfuncs.logger.success(f"Finished getting definitions")
    else:
        globalfuncs.logger.success("Skipping dictionary look up for words")

    globalfuncs.logger.plain(f"{"-" * console_width}")

if __name__ == '__main__':
    # main('https://www.youtube.com/watch?v=QnkqCv0dZTk', 'ai')
    # main('youtube.com/watch?v=ZRtdQ81jPUQ')
    main('https://www.youtube.com/watch?v=Mhl9FaxiQ_E', 'ai', 'vox')