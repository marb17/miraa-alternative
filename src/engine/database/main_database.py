import sqlite3
from pathlib import Path

from engine.utils.classes.dataclasses import DatabaseEntry
from engine.utils.classes.exceptions import DatabaseError
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
                             "song_path TEXT NOT NULL) "
                             
                             ";")
        except DatabaseError:
            raise DatabaseError("Table already exists")

    def add_entry(self, entry: DatabaseEntry) -> None:
        title, artist = entry.title, entry.artist
        json_path, song_path = str(entry.json_path), str(entry.song_path)

        query = "INSERT INTO songs (title, artist, json_path, song_path) VALUES (?, ?, ?, ?);"
        params = (title, artist, json_path, song_path)

        self.raw_execute(query, params=params)

    def get_all_entries(self) -> list[DatabaseEntry]:
        pass


if __name__ == '__main__':
    db = MainDatabase()

    db.create_table()

    db.add_entry(DatabaseEntry("test", "test", Path("test"), Path("test")))