"""Lab 4 (Reference Solution): Agent Registry, Skill Registry, Agent Identity, Model Armor, SCC & Cross-Agent A2A Execution."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

_REPO_ROOT = str(pathlib.Path(os.path.abspath(__file__)).parent.parent)
if _REPO_ROOT not in sys.path:
  sys.path.insert(0, _REPO_ROOT)

from lab4_governance_and_a2a import agent as lab4_starter  # pylint: disable=g-import-not-at-top
import provided  # pylint: disable=g-import-not-at-top

FLEET_AGENTS_MANIFEST = lab4_starter.FLEET_AGENTS_MANIFEST
AUTHORIZED_TOOLS_MANIFEST = lab4_starter.AUTHORIZED_TOOLS_MANIFEST
build_governance_and_a2a_agents = lab4_starter.build_governance_and_a2a_agents
run_lab4_governance_and_a2a = lab4_starter.run_lab4_governance_and_a2a


def main() -> None:
  parser = argparse.ArgumentParser(
      description=(
          'Run Lab 4 Complete: Agent Registry, Skill Registry, OBO Identity, '
          'Model Armor, SCC & Cross-Agent A2A Rollback.'
      )
  )
  parser.add_argument(
      '--persona',
      choices=list(provided.CALLER_PERSONAS.keys()),
      default='incident_commander',
      help='OBO human caller identity persona.',
  )
  parser.add_argument(
      '--query',
      default=(
          'Audit the Agent Registry and Skill Registry, verify Model Armor & '
          'OBO Caller Identity, and execute the governed rollback of '
          'checkout@a3f9c21 by calling change_mgmt_a2a_agent.'
      ),
      help='Governance & A2A execution query.',
  )
  parser.add_argument(
      '--project_id',
      default=provided.DEFAULT_VERTEX_PROJECT,
      help='GCP project ID for BigQuery and Vertex AI Agent Engine.',
  )
  parser.add_argument(
      '--location',
      default=provided.DEFAULT_VERTEX_LOCATION,
      help='GCP region for Vertex AI Agent Engine (default: us-central1).',
  )
  parser.add_argument(
      '--agent_engine_id',
      default=None,
      help='Optional Vertex AI Agent Engine ID.',
  )
  parser.add_argument(
      '--local_only',
      action='store_true',
      help='Run in local in-memory mode without calling GCP APIs.',
  )
  parser.add_argument(
      '--use_live_llm',
      action='store_true',
      help='Use live Gemini model via Vertex AI.',
  )
  args = parser.parse_args()
  result = run_lab4_governance_and_a2a(
      caller_persona=args.persona,
      query=args.query,
      use_live_llm=args.use_live_llm,
      project_id=args.project_id,
      location=args.location,
      agent_engine_id=args.agent_engine_id,
      local_only=args.local_only,
  )
  print(json.dumps(result, indent=2, default=str))


if __name__ == '__main__':
  main()
