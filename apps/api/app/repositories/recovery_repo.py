from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.config import get_settings, sqlite_path_from_url
from app.schemas import AnalyzeRecoveryRequest, RecoveryAdvice, ScoreResult


def get_database_path() -> Path:
    return sqlite_path_from_url(get_settings().database_url)


def connect() -> sqlite3.Connection:
    db_path = get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS run_records (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              distance_km REAL NOT NULL,
              duration_min REAL NOT NULL,
              run_type TEXT NOT NULL,
              run_time_period TEXT NOT NULL,
              rpe INTEGER NOT NULL,
              sleep_hours REAL NOT NULL,
              fatigue_level INTEGER NOT NULL,
              soreness_level INTEGER NOT NULL,
              avg_hr INTEGER,
              max_hr INTEGER,
              diet_preference TEXT,
              tomorrow_plan TEXT,
              symptoms_json TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS recovery_results (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              run_record_id INTEGER NOT NULL,
              score INTEGER NOT NULL,
              level TEXT NOT NULL,
              reasons_json TEXT NOT NULL,
              component_scores_json TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(run_record_id) REFERENCES run_records(id)
            );

            CREATE TABLE IF NOT EXISTS recommendations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              recovery_result_id INTEGER NOT NULL,
              advice_json TEXT NOT NULL,
              timeline_json TEXT NOT NULL,
              safety_flags_json TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(recovery_result_id) REFERENCES recovery_results(id)
            );
            """
        )


def save_analysis(
    run_input: AnalyzeRecoveryRequest,
    score_result: ScoreResult,
    reasons: list[dict],
    advice: RecoveryAdvice,
    safety_flags: list[str],
) -> int:
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO run_records (
              distance_km, duration_min, run_type, run_time_period, rpe,
              sleep_hours, fatigue_level, soreness_level, avg_hr, max_hr,
              diet_preference, tomorrow_plan, symptoms_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_input.distance_km,
                run_input.duration_min,
                run_input.run_type,
                run_input.run_time_period,
                run_input.rpe,
                run_input.sleep_hours,
                run_input.fatigue_level,
                run_input.soreness_level,
                run_input.avg_hr,
                run_input.max_hr,
                run_input.diet_preference,
                run_input.tomorrow_plan,
                json.dumps(run_input.symptoms, ensure_ascii=False),
            ),
        )
        run_record_id = cursor.lastrowid

        cursor = connection.execute(
            """
            INSERT INTO recovery_results (
              run_record_id, score, level, reasons_json, component_scores_json
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                run_record_id,
                score_result.score,
                score_result.level,
                json.dumps(reasons, ensure_ascii=False),
                json.dumps(score_result.component_scores, ensure_ascii=False),
            ),
        )
        recovery_result_id = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO recommendations (
              recovery_result_id, advice_json, timeline_json, safety_flags_json
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                recovery_result_id,
                advice.model_dump_json(),
                json.dumps([item.model_dump() for item in advice.timeline], ensure_ascii=False),
                json.dumps(safety_flags, ensure_ascii=False),
            ),
        )

    if recovery_result_id is None:
        raise RuntimeError("Failed to persist recovery result.")
    return int(recovery_result_id)
