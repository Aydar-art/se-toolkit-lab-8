"""Stdio MCP server exposing observability operations as typed tools."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

from mcp_obs.settings import ObsSettings, resolve_settings


class LogsSearchParams(BaseModel):
    """Parameters for logs_search tool."""

    query: str = Field(
        default="_time:10m",
        description="LogsQL query string (e.g., '_time:10m service.name:backend severity:ERROR')",
    )
    limit: int = Field(default=20, description="Maximum number of log entries to return")


class LogsErrorCountParams(BaseModel):
    """Parameters for logs_error_count tool."""

    minutes: int = Field(default=60, description="Time window in minutes")
    service: str = Field(
        default="", description="Optional service name filter (e.g., 'Learning Management Service')"
    )


class TracesListParams(BaseModel):
    """Parameters for traces_list tool."""

    service: str = Field(
        default="Learning Management Service", description="Service name to filter traces"
    )
    limit: int = Field(default=10, description="Maximum number of traces to return")


class TracesGetParams(BaseModel):
    """Parameters for traces_get tool."""

    trace_id: str = Field(..., description="The trace ID to fetch")


def _text(data: Any) -> list[TextContent]:
    """Convert data to text content."""
    if isinstance(data, BaseModel):
        payload = data.model_dump()
    elif isinstance(data, list):
        payload = [item.model_dump() if isinstance(item, BaseModel) else item for item in data]
    else:
        payload = data
    return [TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, indent=2))]


async def query_victorialogs(
    base_url: str, query: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Query VictoriaLogs using LogsQL."""
    url = f"{base_url}/select/logsql/query"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params={"query": query, "limit": limit},
            timeout=30.0,
        )
        response.raise_for_status()
        # VictoriaLogs returns JSON array of log entries
        return response.json() if response.text else []


async def query_victoriatraces_traces(
    base_url: str, service: str, limit: int = 10
) -> list[dict[str, Any]]:
    """List traces from VictoriaTraces using Jaeger-compatible API."""
    url = f"{base_url}/select/jaeger/api/traces"
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            params={"service": service, "limit": limit},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        # Jaeger API returns {"data": [...]}
        return data.get("data", []) if isinstance(data, dict) else []


async def query_victoriatraces_trace(
    base_url: str, trace_id: str
) -> dict[str, Any] | None:
    """Get a specific trace by ID from VictoriaTraces."""
    url = f"{base_url}/select/jaeger/api/traces/{trace_id}"
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        # Jaeger API returns {"data": [...]}
        traces = data.get("data", []) if isinstance(data, dict) else []
        return traces[0] if traces else None


def create_server(settings: ObsSettings) -> Server:
    """Create the observability MCP server."""
    server = Server("obs")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="mcp_obs_logs_search",
                description="Search logs in VictoriaLogs using LogsQL query",
                inputSchema=LogsSearchParams.model_json_schema(),
            ),
            Tool(
                name="mcp_obs_logs_error_count",
                description="Count error logs per service over a time window",
                inputSchema=LogsErrorCountParams.model_json_schema(),
            ),
            Tool(
                name="mcp_obs_traces_list",
                description="List recent traces for a service from VictoriaTraces",
                inputSchema=TracesListParams.model_json_schema(),
            ),
            Tool(
                name="mcp_obs_traces_get",
                description="Fetch a specific trace by ID from VictoriaTraces",
                inputSchema=TracesGetParams.model_json_schema(),
            ),
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict[str, Any] | None
    ) -> list[TextContent]:
        try:
            if name == "mcp_obs_logs_search":
                params = LogsSearchParams.model_validate(arguments or {})
                result = await query_victorialogs(
                    settings.victorialogs_url, params.query, params.limit
                )
                return _text(result)

            elif name == "mcp_obs_logs_error_count":
                params = LogsErrorCountParams.model_validate(arguments or {})
                # Build a LogsQL query for errors in the time window
                time_filter = f"_time:{params.minutes}m"
                service_filter = f' service.name:"{params.service}"' if params.service else ""
                query = f'{time_filter}{service_filter} severity:ERROR'
                result = await query_victorialogs(
                    settings.victorialogs_url, query, limit=1000
                )
                # Count errors per service
                error_counts: dict[str, int] = {}
                for entry in result:
                    service = entry.get("service.name", "unknown")
                    error_counts[service] = error_counts.get(service, 0) + 1
                return _text(
                    {
                        "time_window_minutes": params.minutes,
                        "total_errors": sum(error_counts.values()),
                        "errors_by_service": error_counts,
                    }
                )

            elif name == "mcp_obs_traces_list":
                params = TracesListParams.model_validate(arguments or {})
                result = await query_victoriatraces_traces(
                    settings.victoriatraces_url, params.service, params.limit
                )
                # Simplify trace data for display
                simplified = [
                    {
                        "trace_id": trace.get("traceID"),
                        "spans": len(trace.get("spans", [])),
                        "start_time": trace.get("startTime"),
                        "duration": trace.get("duration"),
                    }
                    for trace in result
                ]
                return _text(simplified)

            elif name == "mcp_obs_traces_get":
                params = TracesGetParams.model_validate(arguments or {})
                result = await query_victoriatraces_trace(
                    settings.victoriatraces_url, params.trace_id
                )
                if result is None:
                    return _text({"error": f"Trace {params.trace_id} not found"})
                # Simplify trace data
                spans = result.get("spans", [])
                simplified_spans = [
                    {
                        "operation_name": span.get("operationName"),
                        "service": span.get("process", {}).get("serviceName", "unknown"),
                        "duration": span.get("duration"),
                        "logs": len(span.get("logs", [])),
                    }
                    for span in spans
                ]
                return _text(
                    {
                        "trace_id": result.get("traceID"),
                        "duration": result.get("duration"),
                        "spans": simplified_spans,
                    }
                )

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as exc:
            return [TextContent(type="text", text=f"Error: {type(exc).__name__}: {exc}")]

    _ = list_tools, call_tool
    return server


async def main() -> None:
    """Main entry point."""
    settings = resolve_settings()
    server = create_server(settings)
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
