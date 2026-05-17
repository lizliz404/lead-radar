from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from lead_radar.models import LeadSignal, RawPost, ScanResult


class SQLiteStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scan_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_name TEXT NOT NULL,
                    scanned_at TEXT NOT NULL,
                    total_posts INTEGER NOT NULL,
                    candidate_count INTEGER NOT NULL,
                    report_path TEXT,
                    notification_status TEXT NOT NULL DEFAULT 'not_requested',
                    notification_channels TEXT NOT NULL DEFAULT '[]',
                    notification_error TEXT
                )
                """
            )
            self._ensure_column(
                conn,
                "scan_runs",
                "notification_status",
                "TEXT NOT NULL DEFAULT 'not_requested'",
            )
            self._ensure_column(
                conn,
                "scan_runs",
                "notification_channels",
                "TEXT NOT NULL DEFAULT '[]'",
            )
            self._ensure_column(conn, "scan_runs", "notification_error", "TEXT")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    url TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT,
                    author TEXT,
                    community TEXT,
                    created_at TEXT NOT NULL,
                    upvotes INTEGER NOT NULL,
                    num_comments INTEGER NOT NULL,
                    raw_json TEXT,
                    PRIMARY KEY (source, source_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    score REAL NOT NULL,
                    signal_strength TEXT NOT NULL,
                    buying_intent TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    evidence_json TEXT NOT NULL,
                    pain_summary TEXT NOT NULL,
                    recommended_action TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    review_status TEXT NOT NULL DEFAULT 'new',
                    review_note TEXT,
                    reviewed_at TEXT,
                    FOREIGN KEY (run_id) REFERENCES scan_runs(id)
                )
                """
            )
            self._ensure_column(conn, "signals", "signal_strength", "TEXT")
            conn.execute(
                """
                UPDATE signals
                SET signal_strength = buying_intent
                WHERE signal_strength IS NULL OR signal_strength = ''
                """
            )
            self._ensure_column(conn, "signals", "buying_intent", "TEXT")
            conn.execute(
                """
                UPDATE signals
                SET buying_intent = signal_strength
                WHERE buying_intent IS NULL OR buying_intent = ''
                """
            )
            self._ensure_column(conn, "signals", "review_status", "TEXT NOT NULL DEFAULT 'new'")
            self._ensure_column(conn, "signals", "review_note", "TEXT")
            self._ensure_column(conn, "signals", "reviewed_at", "TEXT")

    def save_scan_result(self, result: ScanResult) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO scan_runs (topic_name, scanned_at, total_posts, candidate_count, report_path)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    result.topic_name,
                    result.scanned_at.isoformat(),
                    result.total_posts,
                    result.candidate_count,
                    result.report_path,
                ),
            )
            run_id = int(cursor.lastrowid)

            for signal in result.signals:
                self._upsert_post(conn, signal.post)
                self._insert_signal(conn, run_id, signal)

            return run_id

    def update_notification_status(
        self,
        run_id: int,
        *,
        status: str,
        channels: list[str],
        error: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE scan_runs
                SET notification_status = ?,
                    notification_channels = ?,
                    notification_error = ?
                WHERE id = ?
                """,
                (status, json.dumps(channels, ensure_ascii=False), error, run_id),
            )

    def update_signal_review(
        self,
        *,
        run_id: int,
        source: str,
        source_id: str,
        status: str,
        note: str = "",
    ) -> None:
        reviewed_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE signals
                SET review_status = ?,
                    review_note = ?,
                    reviewed_at = ?
                WHERE run_id = ? AND source = ? AND source_id = ?
                """,
                (status, note.strip() or None, reviewed_at, run_id, source, source_id),
            )

    def get_signal_reviews(self, run_id: int) -> dict[tuple[str, str], dict[str, str | None]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT source, source_id, review_status, review_note, reviewed_at
                FROM signals
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchall()
        return {
            (source, source_id): {
                "status": review_status,
                "note": review_note,
                "reviewed_at": reviewed_at,
            }
            for source, source_id, review_status, review_note, reviewed_at in rows
        }

    def get_review_summary(self, run_id: int | None = None) -> dict[str, object]:
        where_clause = "WHERE run_id = ?" if run_id is not None else ""
        params = (run_id,) if run_id is not None else ()
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT review_status, COUNT(*)
                FROM signals
                {where_clause}
                GROUP BY review_status
                ORDER BY review_status
                """,
                params,
            ).fetchall()
        by_status = {status: count for status, count in rows}
        total = sum(by_status.values())
        positive = sum(by_status.get(status, 0) for status in ("useful", "contacted", "replied", "converted"))
        reviewed = total - by_status.get("new", 0)
        return {
            "run_id": run_id,
            "total": total,
            "reviewed": reviewed,
            "positive": positive,
            "positive_rate": positive / reviewed if reviewed else 0.0,
            "by_status": by_status,
        }

    def _ensure_column(
        self,
        conn: sqlite3.Connection,
        table_name: str,
        column_name: str,
        column_type: str,
    ) -> None:
        columns = {row[1] for row in conn.execute(f"PRAGMA table_info({table_name})")}
        if column_name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")

    def _upsert_post(self, conn: sqlite3.Connection, post: RawPost) -> None:
        conn.execute(
            """
            INSERT OR REPLACE INTO posts (
                source, source_id, url, title, body, author, community,
                created_at, upvotes, num_comments, raw_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                post.source,
                post.source_id,
                post.url,
                post.title,
                post.body,
                post.author,
                post.community,
                post.created_at.isoformat(),
                post.upvotes,
                post.num_comments,
                json.dumps(post.raw, ensure_ascii=False),
            ),
        )

    def _insert_signal(self, conn: sqlite3.Connection, run_id: int, signal: LeadSignal) -> None:
        conn.execute(
            """
            INSERT INTO signals (
                run_id, source, source_id, score, signal_strength, buying_intent, confidence,
                evidence_json, pain_summary, recommended_action, tags_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                signal.post.source,
                signal.post.source_id,
                signal.score,
                signal.signal_strength,
                signal.signal_strength,
                signal.confidence,
                json.dumps(signal.evidence, ensure_ascii=False),
                signal.pain_summary,
                signal.recommended_action,
                json.dumps(signal.tags, ensure_ascii=False),
            ),
        )
