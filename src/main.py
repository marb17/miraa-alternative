import lyricextract
import vocalsep
import ytdown
import lyricstimestamper
import llmfortitleextract
import splittag
import dictlookup
import llmjptoen

from concurrent.futures import ThreadPoolExecutor
import globalfuncs
import json
import shutil
import os
import re

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

llm_batch_size_explanation = config['llm_batch_size_explanation']
llm_batch_size_translation = config['llm_batch_size_translation']

# console line seperator thing
try:
    terminal_size = shutil.get_terminal_size()
    console_width = terminal_size.columns
except OSError:
    globalfuncs.logger.error(
        "Could not determine terminal size. Running in a non-terminal environment or terminal does not support size query.")
    console_width = 20

# main loop
def main(url: str, use_genius: str, use_jisho: str, skip_dict_lookup=False, skip_llm_exp=True, skip_llm_trans=True):
    """
    Returns JSON file, includes: lyrics, timestamps, translations, meanings, POS
    :param url: Input the URL of the song (YouTube Only)
    :param use_genius: if 'genius', uses Genius API to get lyrics, otherwise 'ai' uses AI transcription (unreliable)
    :param use_jisho: scraps jisho website data if true (slow), uses local jamdict if false
    :param skip_dict_lookup:
    :param skip_llm_exp:
    :return:
    """

    global unsplit_en_lyrics

    globalfuncs.logger.verbose(f"URL: {url}, use_genius: {use_genius}, skip_dict_lookup: {skip_dict_lookup}")

    # region download audio
    globalfuncs.logger.info("Starting Download of Song")
    filename, base58path = ytdown.youtube_download_audio(url)
    globalfuncs.logger.success("Finished downloading")
    # endregion

    # region filepath for current song dir
    filepath = f"../database/songs/{base58path}"
    filepath_json = f"../database/songs/{base58path}/data.json"
    # endregion

    # region creating or loading json file
    try:
        with open(filepath_json, "x", encoding='utf-8') as f:
            globalfuncs.write_json(filename, filepath_json, ['song_info', 'title'], as_list=False)
            globalfuncs.logger.verbose("Creating new data.json file")
        with open(filepath_json, 'r', encoding='utf-8') as f:
            file_data = json.load(f)
    except FileExistsError:
        with open(filepath_json, 'r', encoding='utf-8') as f:
            try:
                file_data = json.load(f)
            except json.decoder.JSONDecodeError:
                file_data = {}  # fallback if file is invalid
        globalfuncs.logger.verbose("Data file already exists.")
    # endregion

    globalfuncs.logger.plain(f"{"-" * console_width}")

    # region relative paths for audios
    filepath_audio = f"../database/songs/{base58path}/audio.wav"
    filepath_vocal = f"../database/songs/{base58path}/audio_vocals.wav"
    filepath_vocal_trans = f"../database/songs/{base58path}/audio_vocals_trans.wav"
    # endregion

    # region separate vox
    if os.path.exists(filepath_vocal) and os.path.exists(filepath_vocal_trans):
        globalfuncs.logger.verbose("Skipping Voice Separation, file already exists")
    else:
        globalfuncs.logger.info("Starting Vox Separation")
        vocalsep.separate_audio(filepath_audio)
        globalfuncs.logger.success("Finished Vox Separation")
    # endregion

    globalfuncs.logger.plain(f"{"-" * console_width}")

    # region get time stamped transcription for video sync
    if 'vox_lyrics' in file_data.get('transcribe', {}) and 'vox_timestamped_words' in file_data.get('transcribe', {}):
        vox_timestamped_words = file_data['transcribe']['vox_timestamped_words']
        vox_lyrics = file_data['transcribe']['vox_lyrics']
        globalfuncs.logger.verbose("Skipping timestamp words, data already exists")
    else:
        globalfuncs.logger.info("Start timestamp words")
        vox_timestamped_words, vox_lyrics = lyricstimestamper.transcribe(filepath_vocal_trans)

        globalfuncs.logger.verbose(str(vox_timestamped_words))
        globalfuncs.logger.verbose(str(vox_lyrics))

        for item in vox_timestamped_words: globalfuncs.write_json(item, filepath_json,
                                                                  ['transcribe', 'vox_timestamped_words'])
        for item in vox_lyrics: globalfuncs.write_json(item, filepath_json, ['transcribe', 'vox_lyrics'])

        globalfuncs.logger.success("Finished timestamp words")
    # endregion

    globalfuncs.logger.plain(f"{"-" * console_width}")

    # region retrieve lyrics (jp and en)
    if use_genius == 'genius':
        if 'jp_lyrics' in file_data.get('lyrics', {}).get('genius_jp', {}) and 'en_lyrics' in file_data.get('lyrics',{}).get('genius_en', {}):
            jp_lyrics = file_data['lyrics']['genius_jp']['jp_lyrics']
            jp_lyrics_no_headers = file_data['lyrics']['genius_jp']['jp_lyrics_no_headers']
            en_lyrics = file_data['lyrics']['genius_en']['en_lyrics']
            unsplit_jp_lyrics = file_data['lyrics']['genius_jp']['unsplit_jp_lyrics']
            unsplit_en_lyrics = file_data['lyrics']['genius_en']['unsplit_en_lyrics']
            missing_lines = file_data['lyrics']['genius_jp']['missing_lines']
            globalfuncs.logger.verbose("Skipping lyrics, data already exists")
        else:
            globalfuncs.logger.verbose('Using Genius Lyrics')

            jp_song_id = None

            fallbacks = [
                lambda: lyricextract.genius_get_song_id_jp(filename),
                lambda: lyricextract.genius_get_song_id_jp(
                    llmfortitleextract.get_title_from_song(filename, False, True)),
                lambda: lyricextract.genius_get_song_id_jp(
                    llmfortitleextract.get_title_from_song(filename, True, True)),
                lambda: lyricextract.genius_get_song_id_jp(
                    llmfortitleextract.get_title_from_song(filename, True, False)),
                lambda: lyricextract.genius_get_song_id_multi(
                    llmfortitleextract.get_title_from_song(filename, False, False), True),
                lambda: lyricextract.genius_get_song_id_multi(filename, False),
            ]

            llmfortitleextract.create_model()

            for attempt in fallbacks:
                try:
                    jp_song_id = attempt()
                    if jp_song_id:  # success
                        break
                except Exception:
                    continue
                raise Exception("Failed to get song id from audio file")

            llmfortitleextract.clear_model()

            globalfuncs.logger.success(f"Genius Link Obtained: {jp_song_id} | {filename}")
            en_song_id = lyricextract.genius_get_translated(jp_song_id)

            # multithread for faster load times
            with ThreadPoolExecutor() as executor:
                f_jp_lyrics = executor.submit(lyricextract.extract_lyrics, str(jp_song_id))
                f_en_lyrics = executor.submit(lyricextract.extract_lyrics, en_song_id)

                jp_lyrics_res = f_jp_lyrics.result()
                en_lyrics_res = f_en_lyrics.result()

                jp_lyrics_no_header = jp_lyrics_res[1].split('\n')

                jp_lyrics = jp_lyrics_res[0]
                en_lyrics = en_lyrics_res[0]

                # split the lyrics
                unsplit_jp_lyrics = jp_lyrics
                jp_lyrics = jp_lyrics.split('\n')

                unsplit_en_lyrics = en_lyrics
                en_lyrics = en_lyrics.split('\n')

            # find the differences for the two lyrics (jp with and w/o headers)

            missing_lines = []
            for counter in range(len(jp_lyrics)):
                lyric_line = jp_lyrics[counter]

                no_header_lyric_batch = []
                for sub_counter in range(0 + counter - len(missing_lines), 4 + counter - len(missing_lines)):
                    try:
                        no_header_lyric_batch.append(jp_lyrics_no_header[sub_counter])
                    except:
                        pass

                if lyric_line not in no_header_lyric_batch:
                    missing_lines.append(counter)

            # region JSON save
            globalfuncs.write_json(jp_song_id, filepath_json, ['lyrics', 'genius_jp', 'jp_song_id'], as_list=False)
            for item in jp_lyrics: globalfuncs.write_json(item, filepath_json, ['lyrics', 'genius_jp', 'jp_lyrics'],
                                                          as_list=True, extend=True)
            for item in jp_lyrics_no_header: globalfuncs.write_json(item, filepath_json,
                                                                    ['lyrics', 'genius_jp', 'jp_lyrics_no_headers'],
                                                                    as_list=True, extend=True)
            globalfuncs.write_json(unsplit_jp_lyrics, filepath_json, ['lyrics', 'genius_jp', 'unsplit_jp_lyrics'],
                                   as_list=False)
            globalfuncs.write_json(en_song_id, filepath_json, ['lyrics', 'genius_en', 'en_song_id'], as_list=False)
            for item in en_lyrics: globalfuncs.write_json(item, filepath_json, ['lyrics', 'genius_en', 'en_lyrics'],
                                                          as_list=True, extend=True)
            globalfuncs.write_json(unsplit_en_lyrics, filepath_json, ['lyrics', 'genius_en', 'unsplit_en_lyrics'],
                                   as_list=False)
            globalfuncs.write_json(missing_lines, filepath_json, ['lyrics', 'genius_jp', 'missing_lines'],
                                   as_list=False)
            # endregion

            globalfuncs.logger.success("Finished Lyrics")
    elif use_genius == 'ai':
        if 'ai_trans' in file_data.get('lyrics', {}):
            jp_lyrics = file_data['lyrics']['ai_trans']['jp_lyrics']
            en_lyrics = file_data['lyrics']['ai_trans']['en_lyrics']
            unsplit_jp_lyrics = file_data['lyrics']['ai_trans']['unsplit_jp_lyrics']
            unsplit_en_lyrics = file_data['lyrics']['ai_trans']['unsplit_en_lyrics']
            globalfuncs.logger.verbose("Skipping ai lyrics words, data already exists")
        else:
            globalfuncs.logger.verbose('Using AI Transcription')

            jp_lyrics = []
            unsplit_jp_lyrics = ''
            for lyric in vox_lyrics:
                jp_lyrics.append(lyric[2])
                unsplit_jp_lyrics = unsplit_jp_lyrics + lyric[2] + '\n'

            # * NOT TESTED (too damn lazy)
            en_lyrics = ''
            for lyric in vox_lyrics:
                en_lyrics = en_lyrics + llmjptoen.translate_lyric_to_en(unsplit_jp_lyrics, lyric) + '\n'

            unsplit_en_lyrics = en_lyrics
            en_lyrics = en_lyrics.split('\n')

            for item in jp_lyrics: globalfuncs.write_json(item, filepath_json, ['lyrics', 'ai_trans', 'jp_lyrics'],
                                                          as_list=True, extend=True)
            globalfuncs.write_json(unsplit_jp_lyrics, filepath_json, ['lyrics', 'ai_trans', 'unsplit_jp_lyrics'],
                                   as_list=False)
            for item in en_lyrics: globalfuncs.write_json(item, filepath_json, ['lyrics', 'ai_trans', 'en_lyrics'],
                                                          as_list=True, extend=True)
            globalfuncs.write_json(unsplit_en_lyrics, filepath_json, ['lyrics', 'ai_trans', 'unsplit_en_lyrics'],
                                   as_list=False)
    # endregion
    globalfuncs.logger.plain(f"{"-" * console_width}")

    globalfuncs.logger.verbose(str(jp_lyrics))
    globalfuncs.logger.verbose(str(unsplit_jp_lyrics))

    # region tag and get pos of word
    tagged_lyrics = []
    full_tagged_lyrics = []

    for line in jp_lyrics:
        if '[' in line or line == '':
            tagged_lyrics.append(None)
            full_tagged_lyrics.append(None)
        else:
            tagged_lyrics.append(splittag.morphemes_tag(str(line)))
            full_tagged_lyrics.append(splittag.full_parse_jp_text(str(line)))
    # endregion

    # * finding all types of particles for debug
    all_types_of_pos = set()

    # region convert jp pos to eng pos
    for line in full_tagged_lyrics:
        if line is None:
            continue
        for word in line:
            all_types_of_pos.add(word[1])  # debug line
            word[1] = splittag.translate_pos(word[1])

    if 'tagged' not in file_data.get('lyrics', {}):
        for item in tagged_lyrics: globalfuncs.write_json(item, filepath_json, ['lyrics', 'tagged', 'token'],
                                                          as_list=True)
        for item in full_tagged_lyrics: globalfuncs.write_json(item, filepath_json, ['lyrics', 'tagged', 'full_parse'],
                                                               as_list=True)
    # endregion

    globalfuncs.logger.verbose(str(tagged_lyrics))
    globalfuncs.logger.verbose(str(full_tagged_lyrics))

    globalfuncs.logger.plain(f"{"-" * console_width}")

    # region dictionary lookup
    if not skip_dict_lookup:
        if use_jisho:
            if 'jisho' in file_data.get('lyrics', {}).get('definition', {}):
                dict_lookup_res = file_data['lyrics']['definition']['jisho']
                globalfuncs.logger.verbose("Skipping dictionary lookup, data already exists")
            else:
                globalfuncs.logger.info(f"Getting definitions of each phrase using jisho-api")
                dict_lookup_res = dictlookup.get_meaning_full(jp_lyrics)
                globalfuncs.logger.verbose(str(dict_lookup_res))
                for item in dict_lookup_res: globalfuncs.write_json(item, filepath_json, ['lyrics', 'definition', 'jisho'],
                                                                    as_list=True, extend=True)
                globalfuncs.logger.success(f"Finished getting definitions")
        elif not use_jisho:
            if 'jamdict' in file_data.get('lyrics', {}).get('definition', {}):
                dict_lookup_res = file_data['lyrics']['definition']['jamdict']
                globalfuncs.logger.verbose("Skipping dictionary lookup, data already exists")
            else:
                globalfuncs.logger.info(f"Getting definitions of each phrase using jamdict")
                dict_lookup_res = dictlookup.get_meaning_full_jamdict(jp_lyrics)
                globalfuncs.logger.verbose(str(dict_lookup_res))
                for item in dict_lookup_res: globalfuncs.write_json(item, filepath_json, ['lyrics', 'definition', 'jamdict'],
                                                                    as_list=True, extend=True)
                globalfuncs.logger.success(f"Finished getting definitions")
    else:
        globalfuncs.logger.success("Skipping dictionary look up for words")

    globalfuncs.logger.plain(f"{"-" * console_width}")
    # endregion

    # region explanations for each token
    if not skip_llm_exp:
        globalfuncs.logger.info(f"Getting explanations of tokens")
        llmjptoen.create_model()

        llm_result = []

        try:
            cur_length_of_json_llm = len(file_data['llm']['explanation']['tokens'])
        except KeyError:
            cur_length_of_json_llm = 0

        try:
            llm_data = file_data['llm']['explanation']['tokens']
        except KeyError:
            llm_data = []

        counter = 0
        attempt_try = 0

        prompt_batch = []

        def call_llm_and_save():
            nonlocal prompt_batch, counter, attempt_try, llm_result

            attempt_try = 1

            while True:
                try:
                    response = llmjptoen.explain_word_in_line(prompt_batch)
                    break
                except:
                    attempt_try += 1
                    globalfuncs.logger.notice(f"LLM Failure, trying again. Attempt: {attempt_try}")

            for item, input_data in zip(response, prompt_batch):
                globalfuncs.logger.spam(f"{input_data} | {item}")
                if input_data[0] != '' or input_data[1] is not None:
                    globalfuncs.write_json(item, filepath_json, ['llm', 'explanation', 'tokens'], as_list=True,
                                           extend=False)
                    llm_result.append(item)
                    counter += 1
                else:
                    llm_result.append(None)
                    globalfuncs.write_json(None, filepath_json, ['llm', 'explanation', 'tokens'])
                    counter += 1

        for lyric, lyric_line in zip(dict_lookup_res, jp_lyrics):
            globalfuncs.logger.spam(f"{lyric_line} | {lyric}")
            if lyric is None or lyric == '':
                llm_result.append(None)
                globalfuncs.write_json(None, filepath_json, ['llm', 'explanation', 'tokens'])
                counter += 1
                continue

            pos = [pos for pos in lyric[1] if pos != 'Unknown']

            token = lyric[0]
            meaning = lyric[2]

            if meaning == [] or pos == []:
                llm_result.append(None)
                globalfuncs.write_json(None, filepath_json, ['llm', 'explanation', 'tokens'])
                counter += 1
                continue

            for word, s_pos, meaning in zip(token, pos, meaning):
                if counter < cur_length_of_json_llm:
                    llm_result.append(llm_data[counter])
                    globalfuncs.logger.verbose(f"Found {word} in data, skipping. Counter: {counter}")
                    counter += 1

                    continue

                if len(prompt_batch) == llm_batch_size_explanation:
                    call_llm_and_save()
                    prompt_batch = []

                prompt_batch.append([lyric_line, word, s_pos, unsplit_jp_lyrics])

        if prompt_batch:
            call_llm_and_save()
            prompt_batch = []

        llmjptoen.clear_model()
        globalfuncs.logger.info(f"Finished getting explanations of tokens")
    else:
        globalfuncs.logger.verbose(f"Skipping getting explanations of tokens")
    # endregion

    globalfuncs.logger.plain(f"{"-" * console_width}")

    # TODO add llm for translating jp lyrics to en lyrics, again....
    # ! NOT TESTED YET
    # region translating jp lyrics to en
    if not skip_llm_trans:
        llm_trans_result = []

        globalfuncs.logger.info(f"Translating each lyric")

        llmjptoen.create_model()

        prompt_batch = []
        attempt_try = 1

        for jp_lyric in jp_lyrics:
            prompt_batch.append([unsplit_jp_lyrics, jp_lyric, unsplit_en_lyrics])

            if len(prompt_batch) == llm_batch_size_translation:
                globalfuncs.logger.spam(f"{prompt_batch}")
                while True:
                    try:
                        responses = llmjptoen.batch_translate_lyric_to_en(prompt_batch)
                        break
                    except:
                        attempt_try += 1
                        globalfuncs.logger.notice(f"Translation failure, attempt: {attempt_try}")

                for item, lyric in zip(responses, prompt_batch):
                    if lyric[1] != '':
                        globalfuncs.logger.spam(f"{item}")
                        globalfuncs.write_json(item, filepath_json, ['lyrics', 'genius_jp', 'en_lyrics_ai_translate'],
                                               as_list=True, extend=True)
                    else:
                        globalfuncs.write_json('', filepath_json, ['lyrics', 'genius_jp', 'en_lyrics_ai_translate'],
                                               as_list=True, extend=True)

                prompt_batch = []

        if prompt_batch:
            pass
            # TODO add the thing for fallback
    else:
        globalfuncs.logger.verbose(f"Skipping translation of lyrics")

    llmjptoen.clear_model()
    # endregion

    # TODO add timestamp thing so u can display it later

if __name__ == '__main__':
    # main('https://www.youtube.com/watch?v=QnkqCv0dZTk', 'genius')
    main('youtube.com/watch?v=ZRtdQ81jPUQ', 'genius', False)
    # main('https://www.youtube.com/watch?v=Mhl9FaxiQ_E', 'genius')
