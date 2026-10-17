"""Offline setup: restrict the application's PostgreSQL role and save local credentials.

Run after database/schema.sql, using PG_ADMIN_USER/PG_ADMIN_PASSWORD in .env.
Never import or invoke this script from the HTTP application.
"""
import os
import argparse
import secrets
from pathlib import Path

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv, set_key

ROOT_DIR = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-env-write', action='store_true', help='Use existing environment credentials without writing a file (container setup).')
    args = parser.parse_args()
    env_path = ROOT_DIR / ".env"
    if not args.no_env_write and not env_path.exists():
        raise SystemExit("Copy .env.example to .env before configuring runtime access.")
    load_dotenv(env_path)
    admin = os.environ.get("PG_ADMIN_USER", "postgres")
    runtime = os.environ.get("PG_READONLY_USER", "echo_runtime")
    if args.no_env_write and runtime in {admin, "postgres"}:
        raise SystemExit("Set PG_READONLY_USER=echo_runtime for container setup.")
    if runtime in {admin, "postgres"}:
        runtime = "echo_runtime"
    if runtime == admin:
        raise SystemExit("Runtime and ingestion administrator must be different roles.")
    password = os.environ.get("PG_READONLY_PASSWORD", "")
    invalid_password = not password or password in {"postgres", "change_me", "set_by_configure_runtime"}
    if args.no_env_write and invalid_password:
        raise SystemExit("Set your own PG_READONLY_PASSWORD in .env before container setup.")
    if args.no_env_write and os.environ.get("STAFF_PASSWORD", "") in {"", "set_by_configure_runtime"}:
        raise SystemExit("Set your own STAFF_PASSWORD in .env before container setup.")
    if invalid_password:
        password = secrets.token_urlsafe(32)
    database = os.environ.get("PG_DBNAME", "postgres")
    conn = psycopg2.connect(
        host=os.environ.get("PG_HOST", "localhost"),
        port=int(os.environ.get("PG_PORT", "5434")), dbname=database,
        user=admin, password=os.environ.get("PG_ADMIN_PASSWORD", "postgres"),
        connect_timeout=5,
    )
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (runtime,))
                if cur.fetchone() is None:
                    cur.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(runtime)))
                else:
                    # Do not repurpose an owner or a role inheriting other privileges.
                    cur.execute(
                        "SELECT EXISTS(SELECT 1 FROM pg_class WHERE relowner = "
                        "(SELECT oid FROM pg_roles WHERE rolname = %s)) OR EXISTS("
                        "SELECT 1 FROM pg_auth_members WHERE member = "
                        "(SELECT oid FROM pg_roles WHERE rolname = %s))", (runtime, runtime),
                    )
                    if cur.fetchone()[0]:
                        raise RuntimeError("Runtime role owns relations or has memberships; use a dedicated role.")
                role = sql.Identifier(runtime)
                cur.execute(sql.SQL(
                    "ALTER ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                    "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD %s"
                ).format(role), (password,))
                cur.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
                    sql.Identifier(database), role))
                cur.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
                cur.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(role))
                cur.execute(sql.SQL("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {}").format(role))
                cur.execute(sql.SQL("GRANT SELECT, INSERT ON conversations, conversation_messages TO {}").format(role))
                cur.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE ON chat_requests TO {}").format(role))
                cur.execute(sql.SQL("GRANT USAGE, SELECT ON SEQUENCE conversation_messages_id_seq TO {}").format(role))
                cur.execute(sql.SQL("GRANT SELECT ON public_policies TO {}").format(role))
                cur.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE ON escalations TO {}").format(role))
                cur.execute(sql.SQL("GRANT USAGE, SELECT ON SEQUENCE escalations_id_seq TO {}").format(role))
        if not args.no_env_write:
            set_key(str(env_path), "PG_READONLY_USER", runtime)
            set_key(str(env_path), "PG_READONLY_PASSWORD", password)
            staff_password = os.environ.get("STAFF_PASSWORD", "")
            if not staff_password or staff_password == "set_by_configure_runtime":
                staff_password = secrets.token_urlsafe(24)
            set_key(str(env_path), "STAFF_USERNAME", os.environ.get("STAFF_USERNAME", "staff"))
            set_key(str(env_path), "STAFF_PASSWORD", staff_password)
            env_path.chmod(0o600)
    finally:
        conn.close()
    print("Restricted PostgreSQL runtime role configured. Restart the backend after credential changes.")
    print("Use your configured STAFF_USERNAME / STAFF_PASSWORD for staff sign-in. No secrets displayed.")
    print("Graph credentials are unchanged; Neo4j query read mode is not a database privilege boundary.")


if __name__ == "__main__":
    main()
