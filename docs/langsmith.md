# LangSmith observability

ECHO uses the standalone LangSmith Python SDK for nested execution traces. LangChain and LangGraph are not installed. Tracing is enabled by default but needs a valid LangSmith API key; no key means the pipeline runs normally without uploads.

## Configure

Create a LangSmith API key in your own account and add it to the ignored local `.env`:

```dotenv
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=echo-helpdesk
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

If the key is organization-scoped or spans multiple workspaces, also set `LANGSMITH_WORKSPACE_ID` from workspace settings. For organization-scoped service keys, set `LANGSMITH_ORGANIZATION_ID` when required; ECHO forwards it in the organization header. A 403 can indicate the wrong region, missing workspace scope, or a key that lacks access.

Use the API endpoint appropriate to your LangSmith account region if different. Never commit the key. Recreate the local app after changing configuration:

```sh
docker compose --profile app up -d --build --no-deps --wait --wait-timeout 180 --timeout 35 app
```

For cloud hosting, configure these four variables on the app service when provider deployment resumes. Do not restart any cloud deployment just to enable observability during the provider outage. LangSmith is separate from Alternate Clouds and Groq; each has its own account/usage terms.

Ask a non-sensitive sample policy question, then open the `echo-helpdesk` tracing project in LangSmith. No new endpoint or frontend action is required. `LANGSMITH_TRACING=false` disables exports explicitly. SDK setup/export failures are best-effort and must not cause a second Groq call or prevent a normal answer.

## Trace hierarchy

```text
ECHO question
  Local intent detection
  Public policy retrieval
  Neo4j routing and expansion
  Groq grounded answer
  Citation validation
  Human handoff (when needed)
```

Only stages actually executed appear. A restricted request can hand off before retrieval or Groq. A failed retrieval or unsupported answer creates the corresponding handoff span. Replayed request IDs return the previously stored response and do not create another answer-pipeline trace.

## Exported data

Inputs are empty and hidden by the client. Outputs contain explicit aggregate fields only: answer status/reason, whether a human is needed, source/citation/candidate counts, best retrieval distance, whether a department was found, intent category and whether the provider failed. LangSmith also receives generated trace IDs, span names, timing, project identity and static application metadata. These allow tracing without recording the conversation.

No student questions, previous-prompt memory, generated answers, citation quotes, policy bodies, session IDs, conversation tokens, staff replies or credentials are intentionally exported. Errors contain only their Python exception class, not exception messages or tracebacks. This integration does not export raw prompts or token-level model usage and does not claim cost accounting or automated answer-quality evaluation.

## Verification

Offline SDK tests mock the create/update transport while exercising the real LangSmith tracing context and run-tree hierarchy. They check nested parentage, excluded private strings, default/configured enablement, explicit disablement, sanitized exceptions and fail-open behavior. Normal integration and retrieval checks disable external tracing and Groq. Live delivery was subsequently verified with the configured US service key and explicit organization/workspace scope: completed ECHO question and human-handoff spans were read back from the echo-helpdesk project without Groq usage or stored tickets.

Official SDK reference: https://github.com/langchain-ai/langsmith-sdk/tree/main/python
