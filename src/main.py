import lyricextract
import vocalsep
import ytdown
import lyricstimestampasr

from concurrent.futures import ThreadPoolExecutor

from globalfuncs import base58_to_str, str_to_base58

# main loop
def main(url, skip_vox_sep=True):
    print("Starting Download of Song")
    filename, base58path = ytdown.get_audio(url)
    print("Finished downloading")

    filepath = f"../database/songs/{base58path}/{base58path}.wav"
    filepath_vocal = f"../database/songs/{base58path}/{base58path}_vocals.wav"

    if not skip_vox_sep:
        print("Starting Vox Separation")
        vocalsep.seperate_audio(filepath)
        print("Finished Vox Separation")
    else:
        print("Skipping Vox Separation")

    print("Start timestamp words")
    timestampped_words = lyricstimestampasr.transcribe(filepath_vocal)
    print("Finished timestamp words")

    print("Getting Lyrics (Japanese % English)")
    jp_song_id = lyricextract.genius_get_song_id_jp('', filename)
    print(jp_song_id, filename)
    en_song_id = lyricextract.genius_get_translated(jp_song_id)

    with ThreadPoolExecutor() as executor:
        f_jp_lyrics = executor.submit(lyricextract.extract_lyrics, jp_song_id)
        f_en_lyrics = executor.submit(lyricextract.extract_lyrics, en_song_id)

        jp_lyrics = f_jp_lyrics.result()
        en_lyrics = f_en_lyrics.result()

    print("Finished Lyrics")

    jp_lyrics = jp_lyrics.split('\n')

    print(jp_lyrics)


if __name__ == '__main__':
    main('https://www.youtube.com/watch?v=QnkqCv0dZTk')