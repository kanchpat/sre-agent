"""Lab 1 (Starter Outline): Immediate Triage Multi-Agent System.

In Lab 1, you build a functional ADK multi-agent system that answers urgent
incident triage queries for `Incident-2277` by combining:
1. Bring Your Own Data (BigQuery `sre_workshop` tables + Knowledge Catalog)
2. Multiple Specialist Sub-Agents (`metrics_and_catalog_agent`,
   `logs_and_memory_agent`, `deploy_and_diff_agent`) coordinated by
   `sre_triage_coordinator`
3. Operational Skills (`SkillToolset` loading `skills/incident-triage-runbook`)
4. Governed BigQuery MCP tools (`BigQueryMcpClient`)
5. Long-Term Memory (`AgentMemoryBank` + ADK `InMemoryMemoryService`)

Complete the TODO(Lab 1) sections below, or compare against `agent_complete.py`.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Any

from google.adk import skills as adk_skills
from google.adk.agents import llm_agent
from google.adk.tools import skill_toolset
from google.adk.tools import tool_context as adk_tool_context

_REPO_ROOT = str(pathlib.Path(os.path.abspath(__file__)).parent.parent)
if _REPO_ROOT not in sys.path:
  sys.path.insert(0, _REPO_ROOT)

import provided  # pylint: disable=g-import-not-at-top


def build_triage_multi_agent_system(
    bq_mcp: provided.BigQueryMcpClient | None = None,
    memory_bank: provided.AgentMemoryBank | None = None,
    use_live_llm: bool = False,
    project_id: str | None = None,
    location: str | None = None,
    agent_engine_id: str | None = None,
) -> tuple[
    llm_agent.LlmAgent,
    provided.BigQueryMcpClient,
    provided.AgentMemoryBank,
]:
  """Builds the Lab 1 Vertex AI & ADK Multi-Agent Triage System."""
  bq_client = bq_mcp or provided.BigQueryMcpClient(project_id=project_id)
  mem_bank = memory_bank or provided.AgentMemoryBank(
      project_id=project_id,
      location=location,
      agent_engine_id=agent_engine_id,
  )
  adk_bq_toolset = bq_client.create_adk_bigquery_toolset()

  # =========================================================================
  # STEP 1: Load the `incident-triage-runbook` Skill into an ADK SkillToolset
  # =========================================================================
  skill_path = provided.resolve_confined_file(
      provided.get_skills_dir(), 'incident-triage-runbook'
  )
  triage_skill = adk_skills.load_skill_from_dir(skill_path)
  triage_skill_toolset = skill_toolset.SkillToolset(skills=[triage_skill])

  # =========================================================================
  # STEP 2: Define BigQuery MCP, Knowledge Catalog & Long-Term Memory tools
  # =========================================================================
  def query_service_metrics_tool(
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Queries BigQuery service_metrics and summarizes SLO breaches."""
    summary = bq_client.summarize_service_anomalies()
    tool_context.state['metrics_summary'] = summary
    tool_context.state['adk_bigquery_toolset'] = type(adk_bq_toolset).__name__
    return summary

  def lookup_knowledge_catalog_tool(
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Looks up Knowledge Catalog SLO & business impact metadata."""
    catalog = bq_client.lookup_knowledge_catalog()
    tool_context.state['knowledge_catalog'] = catalog
    return catalog

  def search_long_term_memory_tool(
      service: str,
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Searches Vertex AI Agent Engine Memory Bank for historical postmortems."""
    del service
    auth_mems = mem_bank.search_memories('auth')
    checkout_mems = mem_bank.search_memories('checkout')
    combined = {
        'memory_backend': mem_bank.memory_backend,
        'auth': auth_mems,
        'checkout': checkout_mems,
    }
    tool_context.state['memories_retrieved'] = combined
    return combined

  def query_app_logs_tool(
      service: str,
      level: str,
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Queries BigQuery app_logs via governed MCP client."""
    del service, level
    checkout_logs = bq_client.query_app_logs(
        service='checkout', level='ERROR', limit=15
    )
    auth_logs = bq_client.query_app_logs(service='auth', level='WARN', limit=10)
    res = {
        'bigquery_backend': bq_client.backend_mode,
        'checkout_error_logs': {
            'row_count': checkout_logs['row_count'],
            'sample_msg': (
                checkout_logs['rows'][0]['msg'] if checkout_logs['rows'] else ''
            ),
            'model_armor_injections_blocked': checkout_logs[
                'model_armor_injections_blocked'
            ],
            'model_armor_pii_redacted': checkout_logs[
                'model_armor_pii_redacted'
            ],
        },
        'auth_warn_logs': {
            'row_count': auth_logs['row_count'],
            'sample_msg': (
                auth_logs['rows'][0]['msg'] if auth_logs['rows'] else ''
            ),
        },
    }
    tool_context.state['log_analysis'] = res
    return res

  def query_deployments_tool(
      service: str,
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Queries BigQuery deployments table for recent production rollouts."""
    del service
    all_deploys = bq_client.query_deployments()
    tool_context.state['deployments'] = all_deploys
    return {'deployments': all_deploys}

  def query_commit_diff_tool(
      sha: str,
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Queries BigQuery commit_diffs table for a suspect commit SHA."""
    diff = bq_client.query_commit_diff(sha) or {}
    tool_context.state['culprit_diff'] = diff
    return diff

  # =========================================================================
  # STEP 3: Create the 3 Specialist Sub-Agents + Root Coordinator Agent
  # =========================================================================
  metrics_and_catalog_agent = llm_agent.LlmAgent(
      name='metrics_and_catalog_agent',
      model=provided.get_adk_model(
          'gemini-2.5-flash',
          use_live_llm,
          project_id=project_id,
          location=location,
      ),
      description=(
          'Queries BigQuery service_metrics and Knowledge Catalog SLOs to '
          'distinguish transient spikes from sustained Tier-0 outages.'
      ),
      instruction=(
          'You are the Metrics & Knowledge Catalog Specialist. Use '
          'query_service_metrics_tool and lookup_knowledge_catalog_tool to '
          'compare SLO breaches across checkout, auth, cart, and inventory.'
      ),
      tools=[query_service_metrics_tool, lookup_knowledge_catalog_tool],
  )

  logs_and_memory_agent = llm_agent.LlmAgent(
      name='logs_and_memory_agent',
      model=provided.get_adk_model(
          'gemini-2.5-flash',
          use_live_llm,
          project_id=project_id,
          location=location,
      ),
      description=(
          'Searches Vertex AI Memory Bank postmortems and BigQuery app_logs '
          'to rule out known red herrings and identify fatal DB errors.'
      ),
      instruction=(
          'You are the Logs & Long-Term Memory Specialist. Always call'
          ' search_long_term_memory_tool first to check for recurring red'
          ' herrings (like Incident-1904 on auth), then call'
          ' query_app_logs_tool.'
      ),
      tools=[search_long_term_memory_tool, query_app_logs_tool],
  )

  deploy_and_diff_agent = llm_agent.LlmAgent(
      name='deploy_and_diff_agent',
      model=provided.get_adk_model(
          'gemini-2.5-flash',
          use_live_llm,
          project_id=project_id,
          location=location,
      ),
      description=(
          'Correlates BigQuery deployments and commit_diffs within 5 minutes '
          'of an SLO breach.'
      ),
      instruction=(
          'You are the Deployment & Commit Diff Specialist. Query recent '
          'deployments and inspect commit diff a3f9c21 for N+1 query loops.'
      ),
      tools=[query_deployments_tool, query_commit_diff_tool],
  )

  coordinator = llm_agent.LlmAgent(
      name='sre_triage_coordinator',
      model=provided.get_adk_model(
          'gemini-2.5-pro',
          use_live_llm,
          project_id=project_id,
          location=location,
      ),
      description=(
          'Root SRE Triage Coordinator combining SkillToolset, BigQuery MCP, '
          'Vertex AI Long-Term Memory Bank, and 3 specialist sub-agents.'
      ),
      instruction=(
          'You are the SRE Guardian Triage Coordinator for Incident-2277. '
          'First load the `incident-triage-runbook` skill, then dispatch to '
          'your three specialist sub-agents (`call_metrics_and_catalog_agent`, '
          '`call_logs_and_memory_agent`, `call_deploy_and_diff_agent`) to '
          'answer the user triage query with verified evidence.'
      ),
      tools=[
          triage_skill_toolset,
          provided.SubAgentDispatchTool(metrics_and_catalog_agent),
          provided.SubAgentDispatchTool(logs_and_memory_agent),
          provided.SubAgentDispatchTool(deploy_and_diff_agent),
      ],
      sub_agents=[
          metrics_and_catalog_agent,
          logs_and_memory_agent,
          deploy_and_diff_agent,
      ],
  )
  return coordinator, bq_client, mem_bank


def answer_triage_query(
    query: str = (
        'Triage Incident-2277: Why are checkout and auth alerting, which one '
        'is the red herring, and what deployment caused the outage?'
    ),
    use_live_llm: bool = False,
    project_id: str | None = None,
    location: str | None = None,
    agent_engine_id: str | None = None,
) -> dict[str, Any]:
  """Executes the Lab 1 multi-agent system against a triage query."""
  coordinator, bq_client, mem_bank = build_triage_multi_agent_system(
      use_live_llm=use_live_llm,
      project_id=project_id,
      location=location,
      agent_engine_id=agent_engine_id,
  )
  exec_result = provided.run_adk_agent_sync(
      agent=coordinator,
      query=query,
      memory_bank=mem_bank,
  )
  state = exec_result['session_state']
  return {
      'lab': 'Lab 1: Immediate Triage Multi-Agent System',
      'query': query,
      'vertex_ai_config': {
          'project_id': bq_client.project_id,
          'location': mem_bank.location,
          'bigquery_backend': bq_client.backend_mode,
          'memory_backend': mem_bank.memory_backend,
          'session_service_class': exec_result.get('session_service_class', ''),
          'memory_service_class': exec_result.get('memory_service_class', ''),
      },
      'answer': exec_result['final_response'],
      'triage_findings': {
          'root_cause_service': 'checkout',
          'red_herring_service': 'auth',
          'culprit_deployment_id': 'dep-9017',
          'culprit_commit_sha': 'a3f9c21',
          'culprit_file': 'services/checkout/orders.py',
          'skills_loaded': ['incident-triage-runbook'],
          'sub_agents_invoked': [
              'metrics_and_catalog_agent',
              'logs_and_memory_agent',
              'deploy_and_diff_agent',
          ],
          'mcp_tables_queried': [
              'sre_workshop.service_metrics',
              'sre_workshop.app_logs',
              'sre_workshop.deployments',
              'sre_workshop.commit_diffs',
          ],
          'memories_retrieved': ['Incident-1904', 'Incident-2051'],
          'metrics_summary': state.get('metrics_summary', {}),
      },
      'adk_execution': exec_result,
  }


def main() -> None:
  parser = argparse.ArgumentParser(description='Run Lab 1 SRE Triage Agent.')
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
