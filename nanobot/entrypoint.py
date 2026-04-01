#!/usr/bin/env python3
"""Resolve environment variables into nanobot config and launch the gateway."""

import json
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Load config.json, inject env vars, write config.resolved.json, and exec nanobot gateway."""
    config_path = Path("/app/nanobot/config.json")
    resolved_path = Path("/tmp/nanobot/config.resolved.json")
    workspace_path = Path("/app/nanobot/workspace")

    # Create directory for resolved config
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    # Load the base config
    with open(config_path) as f:
        config = json.load(f)

    # Inject LLM provider settings from env vars
    llm_api_key = os.environ.get("LLM_API_KEY")
    llm_api_base = os.environ.get("LLM_API_BASE_URL")
    llm_api_model = os.environ.get("LLM_API_MODEL")

    if llm_api_key:
        config["providers"]["custom"]["apiKey"] = llm_api_key
    if llm_api_base:
        config["providers"]["custom"]["apiBase"] = llm_api_base
    if llm_api_model:
        config["agents"]["defaults"]["model"] = llm_api_model

    # Inject gateway settings
    gateway_host = os.environ.get("NANOBOT_GATEWAY_CONTAINER_ADDRESS")
    gateway_port = os.environ.get("NANOBOT_GATEWAY_CONTAINER_PORT")

    if gateway_host:
        config["gateway"]["host"] = gateway_host
    if gateway_port:
        config["gateway"]["port"] = int(gateway_port)

    # Inject webchat channel settings if enabled
    webchat_host = os.environ.get("NANOBOT_WEBCHAT_CONTAINER_ADDRESS")
    webchat_port = os.environ.get("NANOBOT_WEBCHAT_CONTAINER_PORT")
    nanobot_access_key = os.environ.get("NANOBOT_ACCESS_KEY")

    if webchat_host or webchat_port:
        config["channels"]["webchat"] = {"enabled": True, "allowFrom": ["*"]}
        if webchat_host:
            config["channels"]["webchat"]["host"] = webchat_host
        if webchat_port:
            config["channels"]["webchat"]["port"] = int(webchat_port)
        if nanobot_access_key:
            config["channels"]["webchat"]["accessKey"] = nanobot_access_key

    # Inject MCP server settings
    # LMS MCP server
    lms_backend_url = os.environ.get("NANOBOT_LMS_BACKEND_URL")
    lms_api_key = os.environ.get("NANOBOT_LMS_API_KEY")

    if lms_backend_url or lms_api_key:
        if "lms" not in config["tools"]["mcpServers"]:
            config["tools"]["mcpServers"]["lms"] = {
                "command": "python",
                "args": ["-m", "mcp_lms"],
            }
        if lms_backend_url:
            # Update the args to include the base URL
            args = config["tools"]["mcpServers"]["lms"].get("args", [])
            if len(args) < 3:
                args = ["-m", "mcp_lms", lms_backend_url]
            else:
                args[2] = lms_backend_url
            config["tools"]["mcpServers"]["lms"]["args"] = args
        if lms_api_key:
            if "env" not in config["tools"]["mcpServers"]["lms"]:
                config["tools"]["mcpServers"]["lms"]["env"] = {}
            config["tools"]["mcpServers"]["lms"]["env"]["NANOBOT_LMS_API_KEY"] = lms_api_key

    # Observability MCP server (for Task 3)
    obs_logs_url = os.environ.get("NANOBOT_VICTORIALOGS_URL")
    obs_traces_url = os.environ.get("NANOBOT_VICTORIATRACES_URL")

    if obs_logs_url or obs_traces_url:
        config["tools"]["mcpServers"]["obs"] = {
            "command": "python",
            "args": ["-m", "mcp_obs"],
            "env": {},
        }
        if obs_logs_url:
            config["tools"]["mcpServers"]["obs"]["env"]["NANOBOT_VICTORIALOGS_URL"] = obs_logs_url
        if obs_traces_url:
            config["tools"]["mcpServers"]["obs"]["env"]["NANOBOT_VICTORIATRACES_URL"] = obs_traces_url

    # Webchat MCP server (for structured UI)
    # The UI relay runs inside the nanobot-webchat channel, accessible at the webchat host/port
    webchat_relay_url = os.environ.get("NANOBOT_UI_RELAY_URL")
    webchat_token = os.environ.get("NANOBOT_UI_RELAY_TOKEN")

    # Build the relay URL from webchat container address if not explicitly provided
    if not webchat_relay_url:
        webchat_host = os.environ.get("NANOBOT_WEBCHAT_CONTAINER_ADDRESS", "0.0.0.0")
        webchat_port = os.environ.get("NANOBOT_WEBCHAT_CONTAINER_PORT", "8765")
        # Use localhost from the perspective of the MCP server running in the same container
        webchat_relay_url = f"http://localhost:{webchat_port}"

    if not webchat_token:
        webchat_token = nanobot_access_key or ""

    if webchat_relay_url or webchat_token:
        config["tools"]["mcpServers"]["webchat"] = {
            "command": "python",
            "args": ["-m", "mcp_webchat"],
            "env": {},
        }
        if webchat_relay_url:
            config["tools"]["mcpServers"]["webchat"]["env"]["NANOBOT_UI_RELAY_URL"] = webchat_relay_url
        if webchat_token:
            config["tools"]["mcpServers"]["webchat"]["env"]["NANOBOT_UI_RELAY_TOKEN"] = webchat_token

    # Write the resolved config
    with open(resolved_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"Using config: {resolved_path}")

    # Launch nanobot gateway using the console script (full path)
    nanobot_path = Path("/app/.venv/bin/nanobot")
    subprocess.run([
        str(nanobot_path),
        "gateway",
        "--config", str(resolved_path),
        "--workspace", str(workspace_path)
    ], check=True)


if __name__ == "__main__":
    main()
