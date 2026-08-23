import sqlite3
from pathlib import Path
from rapidfuzz import fuzz

from engine.utils.classes.dataclasses import DatabaseEntry
from engine.utils.classes.exceptions import DatabaseError
from engine.utils.functions.filesystem import read_json_file
from engine.utils.paths import DATABASE_DIR


class MainDatabase:
    def __init__(self) -> None:
        self.database = sqlite3.connect("database.db")
        self.cursor = self.database.cursor()

        Path(DATABASE_DIR / "songs").mkdir(parents=False, exist_ok=True)
        Path(DATABASE_DIR / "raw_metadata").mkdir(parents=False, exist_ok=True)

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
                             "json_path TEXT NOT NULL,"
                             "youtube_id TEXT NOT NULL) "
                             
                             ";")
        except DatabaseError:
            raise DatabaseError("Table already exists")

    def add_entry(self, entry: DatabaseEntry) -> None:
        json_path = str(entry.json_path.name)

        json_data = read_json_file(entry.json_path)
        title, artist = json_data["pre_processing"]["raw_metadata"]["name"], json_data["pre_processing"]["raw_metadata"]["artists"][0]["name"]
        youtube_id = json_data["pre_processing"]["youtube_id"]

        query = "INSERT INTO songs (title, artist, json_path, youtube_id) VALUES (?, ?, ?, ?);"
        params = (title, artist, json_path, youtube_id)

        self.raw_execute(query, params=params)

    def get_all_entries(self) -> list[DatabaseEntry]:
        self.raw_execute("SELECT * FROM songs;")
        entries = self.cursor.fetchall()

        final_output = [
            DatabaseEntry(
                id=entry[0],
                title=entry[1],
                artist=entry[2],
                json_path=Path(DATABASE_DIR / "raw_metadata" / entry[3]),
                youtube_id=entry[4]
            )
            for entry in entries
        ]

        return final_output




if __name__ == '__main__':
    db = MainDatabase()

    # db.create_table()

    # db.add_entry(DatabaseEntry(Path(r"D:\python\miraa-alternative\src\.temp\想い人 - Ryokuoushoku Shakai.json")))
    # db.add_entry(DatabaseEntry(Path(r"D:\python\miraa-alternative\src\.temp\ライラック - 美波.json")))

    print(db.get_all_entries())