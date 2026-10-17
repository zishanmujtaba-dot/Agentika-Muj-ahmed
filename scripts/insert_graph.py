"""
Offline ingestion script for the Neo4j graph - run manually, same spirit as insert_policies.py.

Loads sample_org.json (departments, teachers, courses, semesters, and which department each
policy escalates to) into Neo4j. This is the ONLY script that writes to the graph. The live
backend only ever reads from it (see rag_pipeline.py's graph_lookup functions).

Run: python insert_graph.py
(Run insert_policies.py first/also - this script assumes Policy nodes may not exist yet and
creates lightweight Policy nodes here too, just enough to attach relationships to; the full
policy text still lives in Postgres, not duplicated here.)
"""
import os
from pathlib import Path
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7689")
NEO4J_AUTH = (os.environ.get("NEO4J_USER", "neo4j"), os.environ.get("NEO4J_PASSWORD", "password123"))


def main():
    with open(ROOT_DIR / "data" / "sample_org.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH)
    driver.verify_connectivity()

    with driver.session() as session:
        for dept in data["departments"]:
            session.run("MERGE (d:Department {name: $name})", name=dept["name"])

        for contact in data["staff_contacts"]:
            session.run(
                """
                MATCH (d:Department {name: $department})
                MERGE (c:StaffContact {email: $email})
                SET c.name = $name, c.phone = $phone, c.role = $role
                MERGE (d)-[:HAS_CONTACT]->(c)
                """,
                department=contact["department"], email=contact["email"],
                name=contact["name"], phone=contact["phone"], role=contact["role"],
            )

        for teacher in data["teachers"]:
            session.run(
                """
                MATCH (d:Department {name: $department})
                MERGE (t:Teacher {email: $email})
                SET t.name = $name
                MERGE (t)-[:BELONGS_TO]->(d)
                """,
                department=teacher["department"], email=teacher["email"], name=teacher["name"],
            )

        for course in data["courses"]:
            session.run(
                """
                MATCH (d:Department {name: $department})
                MERGE (c:Course {code: $code})
                SET c.title = $title
                MERGE (c)-[:BELONGS_TO]->(d)
                """,
                department=course["department"], code=course["code"], title=course["title"],
            )

        for sem in data["semesters"]:
            session.run("MERGE (s:Semester {label: $label})", label=sem["label"])

        for t in data["teaches"]:
            session.run(
                """
                MATCH (teacher:Teacher {name: $teacher}), (course:Course {code: $course})
                MERGE (teacher)-[:TEACHES]->(course)
                """,
                teacher=t["teacher"], course=t["course"],
            )

        for o in data["offered_in"]:
            session.run(
                """
                MATCH (course:Course {code: $course}), (sem:Semester {label: $semester})
                MERGE (course)-[:OFFERED_IN]->(sem)
                """,
                course=o["course"], semester=o["semester"],
            )

        # Lightweight Policy nodes - just enough identity (source_id) to hang relationships off.
        # The actual policy text/category/access_level stays in Postgres as the source of truth;
        # this avoids keeping two copies of the real content in sync.
        for pe in data["policy_escalations"]:
            session.run(
                """
                MATCH (d:Department {name: $department})
                MERGE (p:Policy {source_id: $source_id})
                MERGE (p)-[:ESCALATES_TO]->(d)
                """,
                source_id=pe["policy_source_id"], department=pe["department"],
            )

        for rel in data.get("policy_related", []):
            session.run(
                """
                MATCH (a:Policy {source_id: $from_id}), (b:Policy {source_id: $to_id})
                MERGE (a)-[:RELATED_TO]->(b)
                """,
                from_id=rel["from"], to_id=rel["to"],
            )

    print("Neo4j graph loaded: departments, teachers, courses, semesters, policy routing.")
    driver.close()


if __name__ == "__main__":
    main()
