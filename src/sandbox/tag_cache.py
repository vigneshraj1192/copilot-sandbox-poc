import sqlite3
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional

class TagCache:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_tags (
                    rel_path TEXT PRIMARY KEY,
                    file_hash TEXT NOT NULL,
                    tags_json TEXT NOT NULL
                )
            """)

    @staticmethod
    def compute_hash(data: bytes) -> str:
        return hashlib.md5(data).hexdigest()

    def get_tags(self, rel_path: str, current_hash: str) -> Optional[List[Dict[str, Any]]]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT file_hash, tags_json FROM file_tags WHERE rel_path = ?", (rel_path,))
            row = cur.fetchone()
            if row and row[0] == current_hash:
                return json.loads(row[1])
        return None

    def store_tags(self, rel_path: str, file_hash: str, tags: List[Dict[str, Any]]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO file_tags (rel_path, file_hash, tags_json)
                VALUES (?, ?, ?)
            """, (rel_path, file_hash, json.dumps(tags)))