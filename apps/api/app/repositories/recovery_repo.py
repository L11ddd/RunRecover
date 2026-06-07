from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.config import get_settings, sqlite_path_from_url
from app.schemas import (
    AnalyzeRecoveryRequest,
    FeedbackRequest,
    RecommendationMeta,
    RecoveryAdvice,
    RecoveryHistoryItem,
    ScoreResult,
)


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
              user_level TEXT NOT NULL DEFAULT 'regular',
              user_profile_json TEXT,
              run_type TEXT NOT NULL,
              run_type_main TEXT,
              run_type_modifier_json TEXT NOT NULL DEFAULT '[]',
              run_time_period TEXT NOT NULL,
              rpe INTEGER NOT NULL,
              sleep_hours REAL NOT NULL,
              fatigue_level INTEGER NOT NULL,
              soreness_level INTEGER NOT NULL,
              avg_hr INTEGER,
              max_hr INTEGER,
              diet_preference TEXT,
              tomorrow_plan TEXT,
              past_48h_training TEXT NOT NULL DEFAULT 'rest',
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
              duration_load INTEGER NOT NULL DEFAULT 0,
              session_load REAL NOT NULL DEFAULT 0,
              model_version TEXT NOT NULL DEFAULT 'scoring_v0.3',
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(run_record_id) REFERENCES run_records(id)
            );

            CREATE TABLE IF NOT EXISTS recommendations (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              recovery_result_id INTEGER NOT NULL,
              advice_json TEXT NOT NULL,
              timeline_json TEXT NOT NULL,
              safety_flags_json TEXT NOT NULL,
              llm_provider TEXT NOT NULL DEFAULT 'template',
              llm_model TEXT,
              prompt_version TEXT NOT NULL DEFAULT 'recovery_reasons_v0.4',
              used_fallback INTEGER NOT NULL DEFAULT 0,
              llm_latency_ms INTEGER,
              validation_passed INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(recovery_result_id) REFERENCES recovery_results(id)
            );

            CREATE TABLE IF NOT EXISTS feedback (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              recovery_result_id INTEGER NOT NULL,
              helpfulness_rating TEXT NOT NULL,
              next_day_status TEXT NOT NULL,
              followed_advice TEXT NOT NULL,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY(recovery_result_id) REFERENCES recovery_results(id)
            );
            """
        )
        _ensure_column(connection, "run_records", "run_type_main", "TEXT")
        _ensure_column(
            connection,
            "run_records",
            "user_level",
            "TEXT NOT NULL DEFAULT 'regular'",
        )
        _ensure_column(connection, "run_records", "user_profile_json", "TEXT")
        _ensure_column(
            connection,
            "run_records",
            "run_type_modifier_json",
            "TEXT NOT NULL DEFAULT '[]'",
        )
        _ensure_column(
            connection,
            "run_records",
            "past_48h_training",
            "TEXT NOT NULL DEFAULT 'rest'",
        )
        _ensure_column(
            connection,
            "recovery_results",
            "duration_load",
            "INTEGER NOT NULL DEFAULT 0",
        )
        _ensure_column(
            connection,
            "recovery_results",
            "session_load",
            "REAL NOT NULL DEFAULT 0",
        )
        _ensure_column(
            connection,
            "recovery_results",
            "model_version",
            "TEXT NOT NULL DEFAULT 'scoring_v0.3'",
        )
        _ensure_column(
            connection,
            "recommendations",
            "llm_provider",
            "TEXT NOT NULL DEFAULT 'template'",
        )
        _ensure_column(connection, "recommendations", "llm_model", "TEXT")
        _ensure_column(
            connection,
            "recommendations",
            "prompt_version",
            "TEXT NOT NULL DEFAULT 'recovery_reasons_v0.4'",
        )
        _ensure_column(
            connection,
            "recommendations",
            "used_fallback",
            "INTEGER NOT NULL DEFAULT 0",
        )
        _ensure_column(connection, "recommendations", "llm_latency_ms", "INTEGER")
        _ensure_column(
            connection,
            "recommendations",
            "validation_passed",
            "INTEGER NOT NULL DEFAULT 1",
        )


def _ensure_column(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    if column_name not in existing_columns:
        connection.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"
        )


def save_analysis(
    run_input: AnalyzeRecoveryRequest,
    score_result: ScoreResult,
    reasons: list[dict],
    advice: RecoveryAdvice,
    safety_flags: list[str],
    recommendation_meta: RecommendationMeta,
) -> int:
    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO run_records (
              distance_km, duration_min, user_level, user_profile_json,
              run_type, run_type_main, run_type_modifier_json,
              run_time_period, rpe,
              sleep_hours, fatigue_level, soreness_level, avg_hr, max_hr,
              diet_preference, tomorrow_plan, past_48h_training, symptoms_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_input.distance_km,
                run_input.duration_min,
                run_input.user_level,
                run_input.user_profile.model_dump_json()
                if run_input.user_profile is not None
                else None,
                run_input.run_type or run_input.run_type_main,
                run_input.run_type_main,
                json.dumps(run_input.run_type_modifier, ensure_ascii=False),
                run_input.run_time_period,
                run_input.rpe,
                run_input.sleep_hours,
                run_input.fatigue_level,
                run_input.soreness_level,
                run_input.avg_hr,
                run_input.max_hr,
                run_input.diet_preference,
                run_input.tomorrow_plan,
                run_input.past_48h_training,
                json.dumps(run_input.symptoms, ensure_ascii=False),
            ),
        )
        run_record_id = cursor.lastrowid

        cursor = connection.execute(
            """
            INSERT INTO recovery_results (
              run_record_id, score, level, reasons_json, component_scores_json,
              duration_load, session_load, model_version
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_record_id,
                score_result.score,
                score_result.level,
                json.dumps(reasons, ensure_ascii=False),
                json.dumps(score_result.component_scores, ensure_ascii=False),
                score_result.component_scores.get("duration_load", 0),
                score_result.derived_metrics.get("session_load", 0),
                score_result.model_version,
            ),
        )
        recovery_result_id = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO recommendations (
              recovery_result_id, advice_json, timeline_json, safety_flags_json,
              llm_provider, llm_model, prompt_version, used_fallback,
              llm_latency_ms, validation_passed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recovery_result_id,
                advice.model_dump_json(),
                json.dumps([item.model_dump() for item in advice.timeline], ensure_ascii=False),
                json.dumps(safety_flags, ensure_ascii=False),
                recommendation_meta.llm_provider,
                recommendation_meta.llm_model,
                recommendation_meta.prompt_version,
                int(recommendation_meta.used_fallback),
                recommendation_meta.llm_latency_ms,
                int(recommendation_meta.validation_passed),
            ),
        )

    if recovery_result_id is None:
        raise RuntimeError("Failed to persist recovery result.")
    return int(recovery_result_id)


def save_feedback(recovery_id: int, feedback: FeedbackRequest) -> int:
    with connect() as connection:
        existing = connection.execute(
            "SELECT id FROM recovery_results WHERE id = ?",
            (recovery_id,),
        ).fetchone()
        if existing is None:
            raise ValueError("Recovery result not found.")

        cursor = connection.execute(
            """
            INSERT INTO feedback (
              recovery_result_id, helpfulness_rating, next_day_status, followed_advice
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                recovery_id,
                feedback.helpfulness_rating,
                feedback.next_day_status,
                feedback.followed_advice,
            ),
        )

    if cursor.lastrowid is None:
        raise RuntimeError("Failed to persist feedback.")
    return int(cursor.lastrowid)


def list_recent_history(limit: int = 7) -> list[RecoveryHistoryItem]:
    safe_limit = max(1, min(limit, 20))
    with connect() as connection:
        rows = connection.execute(
            """
            SELECT
              recovery_results.id AS recovery_id,
              recovery_results.created_at AS created_at,
              run_records.distance_km AS distance_km,
              run_records.duration_min AS duration_min,
              COALESCE(run_records.run_type_main, run_records.run_type) AS run_type_main,
              run_records.run_type_modifier_json AS run_type_modifier_json,
              run_records.rpe AS rpe,
              recovery_results.score AS score,
              recovery_results.level AS level,
              recommendations.advice_json AS advice_json
            FROM recovery_results
            JOIN run_records ON run_records.id = recovery_results.run_record_id
            JOIN recommendations ON recommendations.recovery_result_id = recovery_results.id
            ORDER BY recovery_results.created_at DESC, recovery_results.id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()

    history: list[RecoveryHistoryItem] = []
    for row in rows:
        advice = json.loads(row["advice_json"])
        modifiers = json.loads(row["run_type_modifier_json"] or "[]")
        history.append(
            RecoveryHistoryItem(
                recovery_id=row["recovery_id"],
                created_at=row["created_at"],
                distance_km=row["distance_km"],
                duration_min=row["duration_min"],
                run_type_main=row["run_type_main"],
                run_type_modifier=modifiers,
                rpe=row["rpe"],
                score=row["score"],
                level=row["level"],
                tomorrow_advice=advice["tomorrow"]["content"],
            )
        )
    return history
