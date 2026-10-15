"""Cloud Run HTTP server for SRE Guardian (Incident-2277) Live Lab Chat & Console.

Serves:
  - GET  /           : Interactive Split-Screen Lab Chat & Backend Console UI
  - POST /api/chat   : Executes a live chat turn for the selected workshop lab
                       (Prework, Lab 1, Lab 2, Lab 3, Lab 4) against Cloud
                       BigQuery, Vertex AI Agent Engine, and Vertex AI Gemini.
  - GET  /api/health : Health & Vertex AI / BigQuery backend metadata.
"""

from __future__ import annotations

from http import server as http_server
import json
import os
import pathlib
import sys
from typing import Any
from urllib import parse as urlparse

_REPO_ROOT = str(pathlib.Path(__file__).resolve().parents[1])
if _REPO_ROOT not in sys.path:
  sys.path.insert(0, _REPO_ROOT)

import chat_ux


class SreGuardianChatHandler(http_server.BaseHTTPRequestHandler):
  """HTTP request handler for the interactive Lab Chat & Backend Console."""

  def do_GET(self) -> None:  # pylint: disable=invalid-name
    """Handles GET requests for /, /api/health, and /api/chat."""
    parsed = urlparse.urlparse(self.path)
    if parsed.path == '/api/health':
      payload = {
          'status': 'ok',
          'service': 'sre-guardian-ux',
          'mode': 'interactive-lab-chat-and-console',
          'project_id': chat_ux.PROJECT_ID,
          'location': chat_ux.LOCATION,
          'bigquery_dataset': f'{chat_ux.PROJECT_ID}.{chat_ux.DATASET_ID}',
          'vertex_agent_engine_id': chat_ux.AGENT_ENGINE_ID,
      }
      body = json.dumps(payload, indent=2).encode('utf-8')
      self.send_response(200)
      self.send_header('Content-Type', 'application/json; charset=utf-8')
      self.send_header('Content-Length', str(len(body)))
      self.end_headers()
      self.wfile.write(body)
      return

    if parsed.path == '/api/chat':
      qs = urlparse.parse_qs(parsed.query)
      lab_id = qs.get('lab_id', ['lab1'])[0]
      user_message = qs.get('message', [''])[0].strip()
      persona = qs.get('persona', ['incident_commander'])[0]
      armor_str = qs.get('model_armor_enabled', ['true'])[0].lower()
      model_armor_enabled = armor_str not in ('false', '0', 'no')
      result = chat_ux.handle_chat_turn(
          lab_id=lab_id,
          user_message=user_message,
          persona=persona,
          model_armor_enabled=model_armor_enabled,
      )
      body = json.dumps(result, indent=2, default=str).encode('utf-8')
      self.send_response(200)
      self.send_header('Content-Type', 'application/json; charset=utf-8')
      self.send_header('Content-Length', str(len(body)))
      self.end_headers()
      self.wfile.write(body)
      return

    html_bytes = chat_ux.CHAT_UX_HTML.encode('utf-8')
    self.send_response(200)
    self.send_header('Content-Type', 'text/html; charset=utf-8')
    self.send_header('Content-Length', str(len(html_bytes)))
    self.end_headers()
    self.wfile.write(html_bytes)

  def do_POST(self) -> None:  # pylint: disable=invalid-name
    """Handles POST /api/chat requests from the interactive lab chat pane."""
    parsed = urlparse.urlparse(self.path)
    if parsed.path != '/api/chat':
      self.send_response(404)
      self.end_headers()
      return

    length = int(self.headers.get('Content-Length', '0'))
    raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
    try:
      req = json.loads(raw_body)
    except json.JSONDecodeError:
      req = {}

    lab_id = str(req.get('lab_id', 'lab1'))
    user_message = str(req.get('message', '')).strip()
    persona = str(req.get('persona', 'incident_commander'))
    model_armor_enabled = bool(req.get('model_armor_enabled', True))

    result = chat_ux.handle_chat_turn(
        lab_id=lab_id,
        user_message=user_message,
        persona=persona,
        model_armor_enabled=model_armor_enabled,
    )
    body = json.dumps(result, indent=2, default=str).encode('utf-8')
    self.send_response(200)
    self.send_header('Content-Type', 'application/json; charset=utf-8')
    self.send_header('Content-Length', str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def log_message(self, fmt: str, *args: Any) -> None:
    """Suppresses noisy per-request stderr logs."""
    del fmt, args


def main() -> None:
  port = int(os.environ.get('PORT', '8080'))
  httpd = http_server.ThreadingHTTPServer(
      ('0.0.0.0', port), SreGuardianChatHandler
  )
  print(
      f'SRE Guardian Interactive Lab Chat UX listening on http://0.0.0.0:{port}',
      flush=True,
  )
  httpd.serve_forever()


if __name__ == '__main__':
  main()
