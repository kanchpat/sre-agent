"""Lab 3 (Reference Solution): Council of Sub-Agents (ParallelAgent + Arbiter)."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

_REPO_ROOT = str(pathlib.Path(os.path.abspath(__file__)).parent.parent)
if _REPO_ROOT not in sys.path:
  sys.path.insert(0, _REPO_ROOT)

from lab3_council_agent import agent as lab3_starter  # pylint: disable=g-import-not-at-top
import provided  # pylint: disable=g-import-not-at-top

build_council_agent_system = lab3_starter.build_council_agent_system
run_council_deliberation = lab3_starter.run_council_deliberation


def main() -> None:
  parser = argparse.ArgumentParser(
      description='Run Lab 3 Complete SRE Council of Sub-Agents.'
  )
  parser.add_argument(
      '--query',
      default=(
          'Convene the SRE Council of Sub-Agents for Incident-2277: evaluate '
          'whether to roll back checkout@a3f9c21 or auth@7b2e110.'
      ),
      help='Deliberation prompt for the SRE Council Agent.',
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
  result = run_council_deliberation(
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
