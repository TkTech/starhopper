import dataclasses
import enum
import json
import sqlite3


class ItemType(enum.IntEnum):
    UNKNOWN = 0
    FILE = 10
    EDID = 20
    FORM_ID = 30


@dataclasses.dataclass
class SearchResult:
    file_path: str
    navigation_path: list[str | int | list[int, int]]
    stored_text: str
    item_type: ItemType


connection = sqlite3.connect(":memory:", check_same_thread=False)
connection.executescript(
    """
    CREATE TABLE IF NOT EXISTS search_index (
        id INTEGER PRIMARY KEY,
        /* The path on disk where the match is located */
        file_path TEXT NOT NULL,
        /* A viewer-specific path to the match */
        navigation_path TEXT NOT NULL,
        /* Stored text to be retrieved */
        stored_text TEXT NOT NULL,
        /* The text to be searched against*/
        search_text TEXT NOT NULL,
        /* The type of item this is */
        item_type INTEGER NOT NULL
    );
    CREATE UNIQUE INDEX IF NOT EXISTS search_index_unique ON search_index (
        file_path,
        navigation_path,
        stored_text
    );
    CREATE INDEX IF NOT EXISTS search_index_search_text ON search_index (
        search_text
    );
    CREATE INDEX IF NOT EXISTS search_index_item_type ON search_index (
        item_type
    );
    """
)
connection.commit()


def add_to_index(
    file_path: str,
    navigation_path: list[str],
    search_text: str,
    item_type: ItemType,
):
    connection.execute(
        """
        INSERT INTO search_index (
            file_path,
            navigation_path,
            stored_text,
            search_text,
            item_type
        )
        VALUES (?, ?, ?, lower(?), ?)
        ON CONFLICT (file_path, navigation_path, stored_text) DO UPDATE SET
            search_text = excluded.search_text
        """,
        (
            file_path,
            json.dumps(navigation_path),
            search_text,
            search_text,
            item_type.value,
        ),
    )


def search_index(query: str) -> list[SearchResult]:
    results = connection.execute(
        """
        SELECT file_path, navigation_path, stored_text, item_type
        FROM search_index
        WHERE search_text LIKE ?
        ORDER BY file_path ASC
        LIMIT 100
        """,
        (query,),
    ).fetchall()
    for result in results:
        yield SearchResult(
            result[0], json.loads(result[1]), result[2], ItemType(result[3])
        )
