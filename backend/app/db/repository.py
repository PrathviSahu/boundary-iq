"""
BoundaryIQ SQLite Persistence Layer.

Production Deployment Notes:
- Target Cloud Architecture: Single-instance FastAPI backend on Render with a persistent disk.
- Recommended Database Path: /var/data/boundary_iq.db (configured via DATABASE_PATH env var).
- WAL Mode Co-location: In SQLite Write-Ahead Logging mode (PRAGMA journal_mode=WAL), the -wal
  and -shm companion files are automatically created in the exact same directory alongside the .db file.
  Therefore, mounting /var/data guarantees that all database state is persistent across restarts.
- Single-Instance Assumption: SQLite does NOT support concurrent write access across multiple independent
  compute containers/nodes. The Render deployment assumes a single service instance (num_instances: 1).
  For horizontal multi-instance scaling, a managed PostgreSQL database is required.
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from app.models.fantasy import FantasyTeamConfig

logger = logging.getLogger(__name__)

DEFAULT_SQUAD_PLAYERS = [
    "V Kohli", "JJ Bumrah", "RG Sharma", "HH Pandya", "AR Patel",
    "Arshdeep Singh", "Q de Kock", "H Klaasen", "DA Miller", "K Rabada", "KA Maharaj"
]

DEFAULT_CONFIG = FantasyTeamConfig(
    selected_players=DEFAULT_SQUAD_PLAYERS,
    captain="V Kohli",
    vice_captain="JJ Bumrah"
)


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            env_path = os.getenv("DATABASE_PATH", "").strip()
            if env_path:
                self.db_path = Path(env_path)
            else:
                # Default to backend/data/boundary_iq.db
                base_dir = Path(__file__).resolve().parent.parent.parent
                self.db_path = base_dir / "data" / "boundary_iq.db"

        # Ensure parent directory exists with permission error handling
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError) as e:
            logger.critical(f"Failed to create database directory {self.db_path.parent}: {e}")
            raise RuntimeError(
                f"Database directory creation failed for path '{self.db_path}'. "
                f"Ensure filesystem permissions allow writing (e.g. Render Persistent Disk mount): {e}"
            ) from e

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Enable Write-Ahead Logging for high concurrency without blocking reads
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        """Run schema migrations and initialize default records."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fantasy_teams (
                    team_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    selected_players TEXT NOT NULL,
                    captain TEXT NOT NULL,
                    vice_captain TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

        # Seed default teams if not already present
        if not self.get_team("default"):
            self.save_team("default", DEFAULT_CONFIG, name="Default Demo Squad")
        if not self.get_team("demo_team_1"):
            self.save_team("demo_team_1", DEFAULT_CONFIG, name="Demo Team 1")

    def get_team(self, team_id: str) -> Optional[FantasyTeamConfig]:
        """Fetch a saved fantasy team config by team_id."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT selected_players, captain, vice_captain FROM fantasy_teams WHERE team_id = ?",
                (team_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None

            players = json.loads(row["selected_players"])
            return FantasyTeamConfig(
                selected_players=players,
                captain=row["captain"],
                vice_captain=row["vice_captain"]
            )

    def save_team(self, team_id: str, config: FantasyTeamConfig, name: str = "") -> FantasyTeamConfig:
        """Persist or update a fantasy team config atomically."""
        team_name = name or team_id
        players_json = json.dumps(config.selected_players)

        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO fantasy_teams (team_id, name, selected_players, captain, vice_captain, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(team_id) DO UPDATE SET
                    name = excluded.name,
                    selected_players = excluded.selected_players,
                    captain = excluded.captain,
                    vice_captain = excluded.vice_captain,
                    updated_at = CURRENT_TIMESTAMP;
            """, (team_id, team_name, players_json, config.captain, config.vice_captain))
            conn.commit()

        return config

    def list_teams(self) -> List[Dict[str, Any]]:
        """List all saved teams with metadata."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT team_id, name, captain, vice_captain, updated_at FROM fantasy_teams ORDER BY updated_at DESC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def check_health(self) -> bool:
        """Verify database connectivity."""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT 1;")
                return cursor.fetchone()[0] == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

