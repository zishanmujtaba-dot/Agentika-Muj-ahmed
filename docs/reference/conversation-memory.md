# Conversation memory assessment

## Current implementation

The runtime uses plain Python orchestration, the Groq SDK, Sentence Transformers, PostgreSQL/pgvector and the Neo4j driver. It does not use LangChain or LangGraph. PostgreSQL stores authenticated conversation messages and staff replies; browser polling reloads them. Persistent history is different from model memory: `build_prompt()` sends the current question plus retrieved public policies, and `call_llm()` supplies that payload with its system instructions. Previous messages are not supplied to the model.

## Decision for this demo

Keep standalone evidence-based calls. The core use case is answering independent policy questions, and the existing approach has lower token usage and a smaller chance of treating a previous mistaken answer as policy. Neither LangChain nor LangGraph is necessary to implement memory. Adding either framework alone would not make the model remember a conversation.

Memory is useful for a conversational follow-up such as “What if I miss it?” after asking about the tuition deadline. The model cannot reliably resolve “it” from the current payload. The fact that each API call is independent does not prevent conversational context: the application can explicitly include selected earlier turns. It simply does not do so today. For the demo, use “What if I miss the tuition deadline?” instead.

## If conversational follow-ups become required

Use the existing authenticated database history rather than a separate global or process-local memory buffer. Select at most the last three completed student/assistant exchanges from the same session, cap the combined context length, and ignore pending or failed requests. Resolve the new question into a standalone retrieval question before searching; merely appending old messages to the final answer prompt will not fix retrieval for “What if I miss it?”. Prefer deterministic handling where clear and a bounded rewrite call only for ambiguous follow-ups, noting the extra latency and tokens.

Treat earlier student messages, model answers and staff replies as untrusted conversation context, never authoritative policy evidence. Retrieve current public policies again and retain citation validation and restricted-request handling. A staff answer applies to that conversation, not automatically to other students or the public rulebook. Ask for clarification if multiple antecedents are plausible. Do not retain sensitive details unnecessarily or carry context across New conversation.

Before enabling this, test pronoun resolution, topic changes, old incorrect answers, malicious instructions in history, concurrent requests, session isolation and reset behavior. This is a proposed extension; no model-memory behavior has been added in this update.
