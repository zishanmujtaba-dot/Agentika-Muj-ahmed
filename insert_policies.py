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
import json
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

CONFIG = {
    "input_file": "sample_policies.json",
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
    print(f"Loaded {len(records)} policies from {CONFIG['input_file']}")

    embed_model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    conn = psycopg2.connect(
        host=CONFIG["pg_host"], port=CONFIG["pg_port"],
        dbname=CONFIG["pg_dbname"], user=CONFIG["pg_user"], password=CONFIG["pg_password"],
    )
    cur = conn.cursor()

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {CONFIG['table_name']} (
            source_id TEXT PRIMARY KEY,
            category TEXT,
            title TEXT,
            text TEXT NOT NULL,
            access_level TEXT NOT NULL DEFAULT 'public' CHECK (access_level IN ('public','protected')),
            tags TEXT[],
            embedding VECTOR(384)
        );
    """)
    conn.commit()

    texts = [r["text"] for r in records]
    print("Embedding policies...")
    embeddings = embed_model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

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
    conn.commit()

    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS policies_embedding_idx
        ON {CONFIG['table_name']} USING hnsw (embedding vector_cosine_ops);
    """)
    conn.commit()

    cur.execute(f"SELECT COUNT(*) FROM {CONFIG['table_name']};")
    print(f"Done: {cur.fetchone()[0]} policies now in '{CONFIG['table_name']}'")
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
