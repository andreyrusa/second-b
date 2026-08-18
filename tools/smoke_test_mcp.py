"""Smoke-test the MCP server over real stdio JSON-RPC.
Run after ingesting something (e.g. the demo fixtures): exercises all 5 tools."""
import json
import subprocess
import sys
from pathlib import Path

server = subprocess.Popen(
    [sys.executable, str(Path(__file__).resolve().parent / "mcp_server.py")],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    text=True, encoding="utf-8",
)

def send(msg):
    server.stdin.write(json.dumps(msg) + "\n")
    server.stdin.flush()

def recv():
    line = server.stdout.readline()
    return json.loads(line) if line else None

send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
    "protocolVersion": "2025-06-18",
    "capabilities": {}, "clientInfo": {"name": "smoke", "version": "0"}}})
init = recv()
print("initialize ->", init["result"]["serverInfo"])

send({"jsonrpc": "2.0", "method": "notifications/initialized"})

send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
tools = recv()
print("tools ->", [t["name"] for t in tools["result"]["tools"]])

for call_id, (name, args) in enumerate([
    ("search_kb", {"query": "liquidación de pagos"}),
    ("find_job", {"job_name": "InformeDiario"}),
    ("get_chain", {"name": "LIQUIDACION"}),
    ("who_owns", {"entity": "SEPA"}),
    ("recent_changes", {"days": 30}),
], start=3):
    send({"jsonrpc": "2.0", "id": call_id, "method": "tools/call",
          "params": {"name": name, "arguments": args}})
    resp = recv()
    content = resp["result"]["content"]
    text = content[0]["text"] if content else "(sin contenido)"
    print(f"{name} -> {text[:220].replace(chr(10), ' ')}")

server.terminate()
print("MCP smoke test OK")
