"""
Offline ingestion script - run this manually whenever the rulebook changes.

This is the ONLY file in the project allowed to write to the `policies` table. The live
backend (rag_pipeline.py / backend.py) never does - it only ever SELECTs. Keeping writes
confined to this one script is what makes "the agent can read the rulebook but can't edit
it" an actual structural guarantee, not just a design intention.

Safe to re-run: it upserts by source_id instead of dropping the table, so editing a policy's
text just means editing sample_policies.json and running this again.

Run: python insert_policies.py
"""
import os
from pathlib import Path
import json
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

CONFIG = {
    "input_file": ROOT_DIR / "data" / "sample_policies.json",
    "pg_host": os.environ.get("PG_HOST", "localhost"),
    "pg_port": int(os.environ.get("PG_PORT", 5434)),
    "pg_dbname": os.environ.get("PG_DBNAME", "postgres"),
    # Deliberately uses full admin credentials, NOT the read-only role from schema.sql -
    # this script is the only place in the project that should ever have write access.
    "pg_user": os.environ.get("PG_ADMIN_USER", "postgres"),
    "pg_password": os.environ.get("PG_ADMIN_PASSWORD", "postgres"),
    "table_name": "policies",
}


def main():
    with open(CONFIG["input_file"], "r", encoding="utf-8") as f:
        records = json.load(f)
    if not isinstance(records, list) or not records:
        raise ValueError("Policy input must be a nonempty list.")
    ids = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Each policy must be an object.")
        for field in ("source_id", "title", "text"):
            if not isinstance(record.get(field), str) or not record[field].strip():
                raise ValueError(f"Missing or invalid policy {field}.")
        if record["source_id"] in ids:
            raise ValueError("Duplicate policy source_id in input.")
        ids.add(record["source_id"])
        if record.get("access_level", "public") not in {"public", "protected"}:
            raise ValueError("Invalid access level.")
        if record.get("category") not in {"fees", "registration", "courses", "attendance", "general"}:
            raise ValueError("Invalid category.")
        tags = record.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError("Policy tags must be a list of strings.")
    print(f"Loaded {len(records)} policies from {CONFIG['input_file']}")

    embed_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    texts = [r["text"] for r in records]
    print("Embedding policies...")
    embeddings = embed_model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    if embeddings.shape != (len(records), 384):
        raise ValueError("Embedding model returned unexpected dimensions.")

    conn = psycopg2.connect(
        host=CONFIG["pg_host"], port=CONFIG["pg_port"],
        dbname=CONFIG["pg_dbname"], user=CONFIG["pg_user"], password=CONFIG["pg_password"], connect_timeout=5,
    )
    try:
        cur = conn.cursor()

        # Apply the shared schema, including the public-only runtime view and tickets.
        cur.execute((ROOT_DIR / "database" / "schema.sql").read_text())

        for record, emb in zip(records, embeddings):
            vec_str = "[" + ",".join(map(str, emb.tolist())) + "]"
            cur.execute(
                f"""INSERT INTO {CONFIG['table_name']}
                        (source_id, category, title, text, access_level, tags, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (source_id) DO UPDATE SET
                        category = EXCLUDED.category,
                        title = EXCLUDED.title,
                        text = EXCLUDED.text,
                        access_level = EXCLUDED.access_level,
                        tags = EXCLUDED.tags,
                        embedding = EXCLUDED.embedding;""",
                (record["source_id"], record.get("category"), record.get("title"), record["text"],
                 record.get("access_level", "public"), record.get("tags", []), vec_str),
            )
        cur.execute(f"""
            CREATE INDEX IF NOT EXISTS policies_embedding_idx
            ON {CONFIG['table_name']} USING hnsw (embedding vector_cosine_ops);
        """)
        conn.commit()

        cur.execute(f"SELECT COUNT(*) FROM {CONFIG['table_name']};")
        print(f"Done: {cur.fetchone()[0]} policies now in '{CONFIG['table_name']}'")
        cur.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()



if __name__ == "__main__":
    main()
