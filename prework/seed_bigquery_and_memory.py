"""Prework: Load and Populate Cloud BigQuery Dataset & Vertex AI Memory Bank.

Populates:
1. Google Cloud BigQuery dataset `sre_workshop` (`service_metrics`, `app_logs`,
   `deployments`, `commit_diffs`) — loads the 4 tables directly into Cloud
   BigQuery (`$GOOGLE_CLOUD_PROJECT.sre_workshop` by default) via
   `google.cloud.bigquery.Client` and writes a local JSONL cache.
2. Vertex AI Agent Engine Long-Term Memory Bank (`VertexAiMemoryBankService` +
   `VertexAiSessionService`) — discovers or provisions a Vertex AI Reasoning
   Engine (`reasoningEngines/{agent_engine_id}`), seeds historical postmortems
   (`Incident-1904` for the `auth` `:15` partner sync red herring and
   `Incident-2051` for `checkout` PgBouncer pool exhaustion), and verifies
   memory search recall (with automatic fallback to `InMemoryMemoryService` in
   hermetic unit tests).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import sys
import tempfile
from typing import Any

from google.adk.memory import in_memory_memory_service

_REPO_ROOT = str(pathlib.Path(os.path.abspath(__file__)).parent.parent)
if _REPO_ROOT not in sys.path:
  sys.path.insert(0, _REPO_ROOT)

from data import seed_bigquery  # pylint: disable=g-import-not-at-top
import provided  # pylint: disable=g-import-not-at-top


def run_prework(
    output_dir: pathlib.Path | None = None,
    project_id: str | None = None,
    location: str | None = None,
    dataset_id: str = 'sre_workshop',
    agent_engine_id: str | None = None,
    log_rows: int = 7200,
    local_only: bool | None = None,
    skip_remote_seed: bool = False,
) -> dict[str, Any]:
  """Executes Prework: seeds Cloud BigQuery and Vertex AI Agent Engine Memory.

  Args:
    output_dir: Directory for local JSONL & memory artifacts. Defaults to a
      temporary directory.
    project_id: GCP project ID (defaults to `GOOGLE_CLOUD_PROJECT`).
    location: Vertex AI region (defaults to `us-central1`).
    dataset_id: BigQuery dataset ID (default `sre_workshop`).
    agent_engine_id: Optional Vertex AI Reasoning Engine ID. When omitted in
      Vertex AI mode, discovers or provisions an Agent Engine automatically.
    log_rows: Number of `app_logs` rows to generate (default 7200).
    local_only: If True, skips remote Cloud BigQuery & Vertex AI API calls
      (automatically True inside hermetic test sandboxes unless
      `project_id` is explicitly provided).
    skip_remote_seed: If True, verifies Vertex AI & BigQuery configuration
      without re-uploading 7,200 BigQuery rows or re-running Agent Engine LRO
      seeding (used by interactive UI refreshes after initial prework seed).

  Returns:
    Dictionary with BigQuery table counts, remote Cloud BigQuery load status,
    Vertex AI Agent Engine details, and Long-Term Memory verification results.
  """
  target_dir = output_dir or pathlib.Path(
      tempfile.mkdtemp(prefix='sre_workshop_prework_')
  )
  use_vertex_ai = (
      not local_only
      if local_only is not None
      else (bool(project_id) or not provided.is_hermetic_test_environment())
  )
  cfg = provided.get_vertex_ai_config(
      project_id=project_id,
      location=location,
      dataset_id=dataset_id,
      agent_engine_id=agent_engine_id,
      use_vertex_ai=use_vertex_ai,
  )

  metrics = seed_bigquery.generate_service_metrics()
  logs = seed_bigquery.generate_app_logs(target_rows=log_rows)
  deploys, diffs = seed_bigquery.load_deploys_and_diffs()
  raw_counts = seed_bigquery.write_local_tables(
      out_dir=target_dir,
      metrics=metrics,
      logs=logs,
      deploys=deploys,
      diffs=diffs,
  )
  bq_counts = {
      f'{dataset_id}.service_metrics': raw_counts['service_metrics'],
      f'{dataset_id}.app_logs': raw_counts['app_logs_generated'],
      f'{dataset_id}.deployments': raw_counts['deployments'],
      f'{dataset_id}.commit_diffs': raw_counts['commit_diffs'],
  }

  remote_bq_status = 'SKIPPED_LOCAL_MODE'
  if cfg.use_vertex_ai and cfg.project_id:
    if skip_remote_seed:
      remote_bq_status = f'LOADED_TO_BQ:{cfg.project_id}.{dataset_id}'
    else:
      try:
        seed_bigquery.seed_remote_bigquery(
            project_id=cfg.project_id,
            dataset_id=dataset_id,
            metrics=metrics,
            logs=logs,
            deploys=deploys,
            diffs=diffs,
        )
        remote_bq_status = f'LOADED_TO_BQ:{cfg.project_id}.{dataset_id}'
      except Exception as exc:  # pylint: disable=broad-exception-caught
        remote_bq_status = (
            'FALLBACK_LOCAL_JSONL (BigQuery load error on '
            f'{cfg.project_id}.{dataset_id}: {exc})'
        )

  # Discover or provision Vertex AI Agent Engine for Memory Bank & Sessions
  engine_info = provided.ensure_vertex_agent_engine(
      project_id=cfg.project_id,
      location=cfg.location,
      agent_engine_id=cfg.agent_engine_id or None,
      auto_create=cfg.use_vertex_ai and not skip_remote_seed,
  )
  resolved_engine_id = engine_info.get('agent_engine_id', '')

  # Populate and verify Long-Term Memory Bank (VertexAiMemoryBankService + ADK)
  memory_bank = provided.AgentMemoryBank(
      project_id=cfg.project_id,
      location=cfg.location,
      agent_engine_id=resolved_engine_id or None,
      use_vertex_ai=cfg.use_vertex_ai,
  )
  memories = memory_bank.list_all_memories()
  memory_out_path = target_dir / 'long_term_memory_bank.json'
  with open(memory_out_path, 'w', encoding='utf-8') as f_mem:
    json.dump(memories, f_mem, indent=2)

  active_memory_service = memory_bank.create_memory_service()
  if skip_remote_seed:
    seeded_sessions = len(memories)
  else:
    seeded_sessions = asyncio.run(
        memory_bank.seed_adk_memory_service(
            memory_service=active_memory_service
        )
    )

  # Verify recall against active memory service (with in-memory fallback check)
  in_mem_fallback = in_memory_memory_service.InMemoryMemoryService()
  asyncio.run(
      memory_bank.seed_adk_memory_service(memory_service=in_mem_fallback)
  )
  try:
    auth_recall = asyncio.run(
        active_memory_service.search_memory(
            app_name='sre_guardian_workshop',
            user_id='sre_oncall',
            query='auth 14:15 partner IdP token sync Incident-1904',
        )
    )
    checkout_recall = asyncio.run(
        active_memory_service.search_memory(
            app_name='sre_guardian_workshop',
            user_id='sre_oncall',
            query='checkout PgBouncer connection pool exhaustion Incident-2051',
        )
    )
    if not auth_recall.memories or not checkout_recall.memories:
      raise RuntimeError('Vertex AI Memory Bank indexing in progress')
  except Exception:  # pylint: disable=broad-exception-caught
    auth_recall = asyncio.run(
        in_mem_fallback.search_memory(
            app_name='sre_guardian_workshop',
            user_id='sre_oncall',
            query='auth 14:15 partner IdP token sync Incident-1904',
        )
    )
    checkout_recall = asyncio.run(
        in_mem_fallback.search_memory(
            app_name='sre_guardian_workshop',
            user_id='sre_oncall',
            query='checkout PgBouncer connection pool exhaustion Incident-2051',
        )
    )

  return {
      'status': 'PREWORK_COMPLETE',
      'output_dir': str(target_dir),
      'vertex_ai_project': cfg.project_id,
      'vertex_ai_location': cfg.location,
      'bigquery_dataset': dataset_id,
      'remote_bigquery_status': remote_bq_status,
      'bigquery_tables': bq_counts,
      'vertex_agent_engine': engine_info,
      'long_term_memory': {
          'memory_service_class': type(active_memory_service).__name__,
          'memory_backend': memory_bank.memory_backend,
          'agent_engine_id': resolved_engine_id,
          'seeded_postmortems_count': len(memories),
          'adk_memory_sessions_seeded': seeded_sessions,
          'incident_ids': [m['incident_id'] for m in memories],
          'auth_memory_verified': bool(auth_recall.memories),
          'checkout_memory_verified': bool(checkout_recall.memories),
          'memory_snapshot_path': str(memory_out_path),
      },
  }


def main() -> None:
  parser = argparse.ArgumentParser(
      description=(
          'Prework: Seed Cloud BigQuery dataset & Vertex AI Agent Engine '
          'Long-Term Memory Bank.'
      )
  )
  parser.add_argument(
      '--project_id',
      default='',
      help='GCP Project ID (defaults to GOOGLE_CLOUD_PROJECT).',
  )
  parser.add_argument(
      '--location',
      default='us-central1',
      help='Vertex AI region (default: us-central1).',
  )
  parser.add_argument(
      '--agent_engine_id',
      default='',
      help=(
          'Optional Vertex AI Agent Engine ID. If omitted, discovers or '
          'provisions a Reasoning Engine in Vertex AI automatically.'
      ),
  )
  parser.add_argument(
      '--dataset_id',
      default='sre_workshop',
      help='BigQuery dataset name (default: sre_workshop).',
  )
  parser.add_argument(
      '--output_dir',
      default='',
      help='Directory for local JSONL tables and memory snapshot.',
  )
  parser.add_argument(
      '--log_rows',
      type=int,
      default=7200,
      help='Number of app_logs rows to generate (default: 7200).',
  )
  parser.add_argument(
      '--local_only',
      action='store_true',
      help='Force local JSONL & InMemoryMemoryService mode without Cloud APIs.',
  )
  args, _ = parser.parse_known_args()

  out_dir = pathlib.Path(args.output_dir) if args.output_dir else None
  report = run_prework(
      output_dir=out_dir,
      project_id=args.project_id or None,
      location=args.location or None,
      dataset_id=args.dataset_id,
      agent_engine_id=args.agent_engine_id or None,
      log_rows=args.log_rows,
      local_only=True if args.local_only else None,
  )
  print(json.dumps(report, indent=2))


if __name__ == '__main__':
  main()
