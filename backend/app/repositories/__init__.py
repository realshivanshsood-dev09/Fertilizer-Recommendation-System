"""
Repository layer for the Fertilizer Recommendation System.

Architecture:
    FastAPI route → service → repository → SQLAlchemy → PostgreSQL/SQLite

All database access is concentrated here; route handlers and services
remain independently testable without a database.
"""
