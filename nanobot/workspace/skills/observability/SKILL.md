---
name: observability
description: Use observability tools to investigate system health, errors, and traces
always: true
---

# Observability Skill

Use the observability MCP tools to investigate system health, find errors, and trace failures.

## Available Tools

- `mcp_obs_logs_search` — Search logs in VictoriaLogs using LogsQL query
- `mcp_obs_logs_error_count` — Count error logs per service over a time window
- `mcp_obs_traces_list` — List recent traces for a service from VictoriaTraces
- `mcp_obs_traces_get` — Fetch a specific trace by ID from VictoriaTraces

## Strategy

### When the user asks about errors or system health

1. **Start with `mcp_obs_logs_error_count`** to get a high-level view of recent errors
   - Use a time window matching the user's question (e.g., "last 10 minutes" → 10 minutes)
   - If no time is specified, use 60 minutes as default

2. **If errors are found, use `mcp_obs_logs_search`** to inspect the actual error messages
   - Focus on the service with the most errors
   - Look for `trace_id` in the log entries

3. **If a trace_id is found, use `mcp_obs_traces_get`** to fetch the full trace
   - This shows the complete request flow across services
   - Identify where the failure occurred in the span hierarchy

4. **Summarize findings concisely** — don't dump raw JSON
   - Mention which service(s) had errors
   - Explain what the error was (from log messages)
   - If you have trace data, describe the failing request path
   - Suggest what might be causing the issue

### Example investigation flow for "What went wrong?" or "Any errors?"

1. Call `mcp_obs_logs_error_count({"minutes": 10})` to check for recent errors
2. If errors found, call `mcp_obs_logs_search({"query": "_time:10m severity:ERROR", "limit": 10})`
3. Extract `trace_id` from a relevant error log
4. Call `mcp_obs_traces_get({"trace_id": "<extracted_id>"})` to see the full trace
5. Summarize: "Found X errors in the last 10 minutes. The main issue appears to be [description]. The trace shows the failure occurred at [span/service]."

### When the user asks about a specific service

Filter logs and traces by that service:
- For logs: `_time:10m service.name:"Service Name" severity:ERROR`
- For traces: Use `mcp_obs_traces_list` with the service name

## Response Style

- Keep responses concise and actionable
- Highlight the most important finding first
- Use bullet points for multiple issues
- Include timestamps and counts when relevant
- Don't dump raw JSON — summarize the key insights

## Error Handling

- If observability services are unreachable, say so clearly
- If no errors are found, report "No errors detected in the specified time window"
- If a trace_id is invalid or not found, try listing recent traces instead
