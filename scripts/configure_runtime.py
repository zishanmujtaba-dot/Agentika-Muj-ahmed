"""Offline setup: restrict the application's PostgreSQL role and save local credentials.

Run after database/schema.sql, using PG_ADMIN_USER/PG_ADMIN_PASSWORD in .env.
Never import or invoke this script from the HTTP application.
"""
import os
import secrets
from pathlib import Path

import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv, set_key

ROOT_DIR = Path(__file__).resolve().parents[1]


def main():
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        raise SystemExit("Copy .env.example to .env before configuring runtime access.")
    load_dotenv(env_path)
    admin = os.environ.get("PG_ADMIN_USER", "postgres")
    runtime = os.environ.get("PG_READONLY_USER", "echo_runtime")
    if runtime in {admin, "postgres"}:
        runtime = "echo_runtime"
    if runtime == admin:
        raise SystemExit("Runtime and ingestion administrator must be different roles.")
    password = os.environ.get("PG_READONLY_PASSWORD", "")
    if not password or password in {"postgres", "change_me", "set_by_configure_runtime"}:
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
                cur.execute(sql.SQL("GRANT SELECT ON public_policies TO {}").format(role))
                cur.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE ON escalations TO {}").format(role))
                cur.execute(sql.SQL("GRANT USAGE, SELECT ON SEQUENCE escalations_id_seq TO {}").format(role))
        set_key(str(env_path), "PG_READONLY_USER", runtime)
        set_key(str(env_path), "PG_READONLY_PASSWORD", password)
        env_path.chmod(0o600)
    finally:
        conn.close()
    print("Restricted PostgreSQL runtime role configured; credentials saved to .env. Restart the backend.")
    print("Graph credentials are unchanged; Neo4j query read mode is not a database privilege boundary.")


if __name__ == "__main__":
    main()
