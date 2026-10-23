"""Lab 2 (Reference Solution): Model Armor Guardrails, Self-Reflection, LLM Judge & Observability."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

_REPO_ROOT = str(pathlib.Path(os.path.abspath(__file__)).parent.parent)
if _REPO_ROOT not in sys.path:
  sys.path.insert(0, _REPO_ROOT)

from lab2_guardrails_reflection_sandbox import agent as lab2_starter  # pylint: disable=g-import-not-at-top
import provided  # pylint: disable=g-import-not-at-top

build_lab2_pipeline = lab2_starter.build_lab2_pipeline
run_lab2_verification = lab2_starter.run_lab2_verification


def main() -> None:
  """CLI entry point for standalone execution."""
  parser = argparse.ArgumentParser(
      description=(
          'Run Lab 2 Complete Model Armor Guardrails & Self-Reflection.'
      )
  )
  parser.add_argument(
      '--query',
      default=(
          'Enforce Model Armor guardrails on BigQuery app_logs and user '
          'prompts, and run Self-Reflection + LLM Judge.'
      ),
      help='Verification query for the Lab 2 pipeline.',
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
  result = run_lab2_verification(
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
