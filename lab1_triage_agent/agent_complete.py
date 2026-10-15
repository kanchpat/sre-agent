"""Lab 1 (Reference Solution): Immediate Triage Multi-Agent System.

Implements a functional ADK multi-agent system that answers interactive incident
triage queries for `Incident-2277` using:
- Bring Your Own Data (BigQuery `sre_workshop` tables + Knowledge Catalog)
- Multiple Agents (`sre_triage_coordinator` + 3 specialist `LlmAgent`s)
- Skills (`SkillToolset` loading `skills/incident-triage-runbook/SKILL.md`)
- Governed MCP (`BigQueryMcpClient`)
- Long-Term Memory (`AgentMemoryBank` + ADK `InMemoryMemoryService`)
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

_REPO_ROOT = str(pathlib.Path(os.path.abspath(__file__)).parent.parent)
if _REPO_ROOT not in sys.path:
  sys.path.insert(0, _REPO_ROOT)

from lab1_triage_agent import agent as lab1_starter  # pylint: disable=g-import-not-at-top

build_triage_multi_agent_system = lab1_starter.build_triage_multi_agent_system
answer_triage_query = lab1_starter.answer_triage_query


def main() -> None:
  parser = argparse.ArgumentParser(
      description='Run Lab 1 Complete SRE Triage Multi-Agent System.'
  )
  parser.add_argument(
      '--query',
      default=(
          'Triage Incident-2277: Why are checkout and auth alerting, which one '
          'is the red herring, and what deployment caused the outage?'
      ),
      help='Natural-language triage question for the SRE Triage Agent.',
  )
  parser.add_argument(
      '--project_id',
      default='',
      help='Optional GCP Project ID (defaults to GOOGLE_CLOUD_PROJECT).',
  )
  parser.add_argument(
      '--location',
      default='us-central1',
      help='Vertex AI region (default: us-central1).',
  )
  parser.add_argument(
      '--agent_engine_id',
      default='',
      help='Optional Vertex AI Agent Engine ID for Sessions & Memory Bank.',
  )
  parser.add_argument(
      '--use_live_llm',
      action='store_true',
      help='Use live Gemini model via Vertex AI.',
  )
  args, _ = parser.parse_known_args()
  result = answer_triage_query(
      query=args.query,
      use_live_llm=args.use_live_llm,
      project_id=args.project_id or None,
      location=args.location or None,
      agent_engine_id=args.agent_engine_id or None,
  )
  print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
  main()
