"""
Database Migration Script - Add Performance Indexes

This script adds the new indexes defined in models.py to existing databases.
Run this after updating the models to add indexes without recreating tables.

Usage:
    python -m app.db.migrations.add_indexes
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text, inspect
from app.db.database import engine, init_db
from app.db.models import Message, Artifact


def index_exists(inspector, table_name: str, index_name: str) -> bool:
    """Check if an index exists on a table."""
    indexes = inspector.get_indexes(table_name)
    return any(idx['name'] == index_name for idx in indexes)


def add_indexes():
    """Add new indexes to existing database."""
    print("=" * 60)
    print("DATABASE INDEX MIGRATION")
    print("=" * 60)

    inspector = inspect(engine)

    # Indexes to add for Message table
    message_indexes = [
        ("idx_message_conversation_created", "CREATE INDEX idx_message_conversation_created ON messages(conversation_id, created_at)"),
        ("idx_message_agent_name", "CREATE INDEX idx_message_agent_name ON messages(agent_name)"),
        ("idx_message_conversation_role", "CREATE INDEX idx_message_conversation_role ON messages(conversation_id, role)"),
    ]

    # Indexes to add for Artifact table
    artifact_indexes = [
        ("idx_artifact_filename", "CREATE INDEX idx_artifact_filename ON artifacts(filename)"),
        ("idx_artifact_conversation_filename", "CREATE INDEX idx_artifact_conversation_filename ON artifacts(conversation_id, filename)"),
        ("idx_artifact_conversation_created", "CREATE INDEX idx_artifact_conversation_created ON artifacts(conversation_id, created_at)"),
    ]

    added_count = 0
    skipped_count = 0

    with engine.connect() as conn:
        # Add Message indexes
        print("\n📋 Processing Message table indexes...")
        for index_name, create_sql in message_indexes:
            if index_exists(inspector, "messages", index_name):
                print(f"  ⏭️  {index_name} - already exists, skipping")
                skipped_count += 1
            else:
                try:
                    conn.execute(text(create_sql))
                    conn.commit()
                    print(f"  ✅ {index_name} - created successfully")
                    added_count += 1
                except Exception as e:
                    print(f"  ❌ {index_name} - failed: {e}")

        # Add Artifact indexes
        print("\n📦 Processing Artifact table indexes...")
        for index_name, create_sql in artifact_indexes:
            if index_exists(inspector, "artifacts", index_name):
                print(f"  ⏭️  {index_name} - already exists, skipping")
                skipped_count += 1
            else:
                try:
                    conn.execute(text(create_sql))
                    conn.commit()
                    print(f"  ✅ {index_name} - created successfully")
                    added_count += 1
                except Exception as e:
                    print(f"  ❌ {index_name} - failed: {e}")

    print("\n" + "=" * 60)
    print(f"MIGRATION COMPLETE")
    print(f"  Added: {added_count} indexes")
    print(f"  Skipped: {skipped_count} indexes (already exist)")
    print("=" * 60)


def verify_indexes():
    """Verify all indexes exist."""
    print("\n🔍 Verifying indexes...")

    inspector = inspect(engine)

    expected_indexes = {
        "messages": [
            "idx_message_conversation_created",
            "idx_message_agent_name",
            "idx_message_conversation_role"
        ],
        "artifacts": [
            "idx_artifact_filename",
            "idx_artifact_conversation_filename",
            "idx_artifact_conversation_created"
        ]
    }

    all_good = True
    for table_name, index_names in expected_indexes.items():
        existing_indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]

        for index_name in index_names:
            if index_name in existing_indexes:
                print(f"  ✅ {table_name}.{index_name}")
            else:
                print(f"  ❌ {table_name}.{index_name} - MISSING!")
                all_good = False

    if all_good:
        print("\n✅ All indexes verified successfully!")
    else:
        print("\n❌ Some indexes are missing!")

    return all_good


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Database index migration")
    parser.add_argument("--verify-only", action="store_true",
                        help="Only verify indexes, don't add them")
    args = parser.parse_args()

    if args.verify_only:
        verify_indexes()
    else:
        add_indexes()
        verify_indexes()
