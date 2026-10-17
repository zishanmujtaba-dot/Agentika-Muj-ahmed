# One-prompt conversation memory

The runtime uses the Groq SDK directly with Sentence Transformers, PostgreSQL/pgvector and Neo4j; no LangChain or LangGraph dependency is needed.

## Current behavior

PostgreSQL stores the full conversation for display and staff reply delivery. Each model call receives the current question, retrieved public policy evidence, and at most **one previous completed student prompt** from the same authenticated conversation. It receives no earlier assistant answers, staff replies, older prompts or cross-session history. The previous prompt is capped at 2,000 characters. Failed/in-progress reservations are not selected; the current request and newer concurrent requests are excluded by message order. A replay uses its stored response rather than running another call. New conversation starts with no previous prompt.

Short referential follow-ups such as “What if I miss it?” combine the previous prompt with the current question for retrieval. Explicit topic changes, such as “What about library books?”, search the new topic on its own. The previous prompt is labelled as untrusted reference context in the answer payload and system instructions, never as authoritative policy evidence. Current public-policy retrieval, citations and escalation checks still apply.

No additional model rewrite call is used. This keeps usage bounded but is not general language-level reference resolution. Ambiguous or unsupported questions can still be handed to staff. Three short elliptical turns in a row can lose the original topic, because only the immediately previous completed prompt is retained. Repeat the topic if needed.

## Demo

Start a new conversation, ask “When are semester tuition fees due?”, then “What if I miss it?”. The second question should retrieve fee evidence and use the prior question to interpret “it”. Then ask “What is the minimum attendance requirement?” to demonstrate a topic switch. Each generated answer still needs current policy citations.

## Verification

The model-stubbed integration suite checks first-turn absence, fee follow-up retrieval, one-prompt replacement, replay behavior, topic switching and session isolation. Live generated wording needs manual review with the configured demo key.
