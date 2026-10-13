import sqlite3
from pathlib import Path
import shutil
from datetime import datetime
import json

from engine.utils.classes.dataclasses import DatabaseEntry
from engine.utils.classes.exceptions import DatabaseError
from engine.utils.functions.filesystem import read_json_file
from engine.utils.paths import DATABASE_DIR, TEMP_DIR


class MainDatabase:
    def __init__(self) -> None:
        Path(DATABASE_DIR).mkdir(parents=True, exist_ok=True)
        Path(DATABASE_DIR / "songs").mkdir(parents=False, exist_ok=True)
        Path(DATABASE_DIR / "raw_metadata").mkdir(parents=False, exist_ok=True)

        self.database = sqlite3.connect(Path(DATABASE_DIR / "database.db"))
        self.cursor = self.database.cursor()


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.database.close()
        return False

    def raw_execute(self, query: str, params: tuple = (), commit: bool = True, safe_exit: bool = True) -> None:
        try:
            self.cursor.execute(query, params)
            if commit:
                self.database.commit()
        except sqlite3.OperationalError as e:
            if safe_exit:
                raise DatabaseError(e) from e
            else:
                print(e)


    def create_table(self) -> None:
        try:
            self.raw_execute("CREATE TABLE songs("
                             "entry_id INTEGER PRIMARY KEY,"
                             "title TEXT NOT NULL,"
                             "artist TEXT NOT NULL,"
                             "album_name TEXT NOT NULL,"
                             "album_release_date TEXT NOT NULL,"
                             "youtube_id TEXT NOT NULL,"
                             "image_thumbnail TEXT NOT NULL,"
                             "audios TEXT NOT NULL,"
                             "json_path TEXT NOT NULL,"
                             "metadata TEXT NOT NULL"
                             ");")
        except DatabaseError:
            raise DatabaseError("Table already exists")

    def add_entry(self, entry: DatabaseEntry) -> None:
        json_path = str(entry.json_path.name)

        json_data = read_json_file(entry.json_path)
        title, artist = json_data["pre_processing"]["raw_metadata"]["name"], json_data["pre_processing"]["raw_metadata"]["artists"][0]["name"]
        youtube_id = json_data["pre_processing"]["youtube_id"]
        image_thumbnail = json_data["genius_data"]["header_image_url"]
        audios = {
            "audio": f"{youtube_id}.wav",
            "inst_audio": f"{youtube_id}_inst.wav",
            "vocal_audio": f"{youtube_id}_vocal.wav",
        }
        album_name, album_release_date = json_data["pre_processing"]["raw_metadata"]["album"]["name"], datetime.strptime(json_data["pre_processing"]["raw_metadata"]["album"]["release_date"], "%Y-%m-%d").date()

        metadata = {
            "duration": json_data["pre_processing"]["youtube_metadata"]["duration"],
        }

        query = "INSERT INTO songs (title, artist, album_name, album_release_date, youtube_id, image_thumbnail, audios, json_path, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);"
        params = (
            title, artist,
            album_name, album_release_date.isoformat(),
            youtube_id,
            image_thumbnail,
            json.dumps(audios),
            json_path,
            json.dumps(metadata),
        )

        self.raw_execute(query, params=params)

    def get_all_entries(self) -> list[DatabaseEntry]:
        self.raw_execute("SELECT * FROM songs;", commit=False)
        entries = self.cursor.fetchall()

        final_output = [
            DatabaseEntry(
                id=entry[0],
                title=entry[1],
                artist=entry[2],
                album_name=entry[3],
                album_release_date=datetime.fromisoformat(entry[4]).date(),
                youtube_id=entry[5],
                image_thumbnail=entry[6],
                audios=json.loads(entry[7]),
                json_path=Path(DATABASE_DIR / "raw_metadata" / entry[8]),
                metadata=json.loads(entry[9]),
            )
            for entry in entries
        ]

        return final_output

    def move_entry_to_temp(self, entry_id: int) -> None:
        self.raw_execute("SELECT json_path, audios FROM songs WHERE entry_id = ?;",
                         (entry_id,),
                         commit=False)
        row = self.cursor.fetchone()

        if not row:
            return

        audios = json.loads(row[1])

        json_path = Path(DATABASE_DIR / "raw_metadata" / row[0])
        audio_path = Path(DATABASE_DIR / "songs" / audios["audio"])
        audio_inst_path = Path(DATABASE_DIR / "songs" / audios["inst_audio"])
        audio_vocal_path = Path(DATABASE_DIR / "songs" / audios["vocal_audio"])

        shutil.move(json_path, Path(TEMP_DIR))
        shutil.move(audio_path, Path(TEMP_DIR))
        shutil.move(audio_inst_path, Path(TEMP_DIR))
        shutil.move(audio_vocal_path, Path(TEMP_DIR))

        self.raw_execute("DELETE FROM songs WHERE entry_id = ?;", (entry_id,))


if __name__ == '__main__':
    db = MainDatabase()

    # db.create_table()

    # db.add_entry(DatabaseEntry(Path(r"D:\python\miraa-alternative\src\.temp\想い人 - Ryokuoushoku Shakai.json")))
    # db.add_entry(DatabaseEntry(Path(r"D:\python\miraa-alternative\src\.temp\ライラック - 美波.json")))

    # print(db.get_all_entries())

    db.move_entry_to_temp(5)