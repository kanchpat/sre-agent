"""Lab 3 (Starter Outline): Council of Sub-Agents (Single-Agent Myopia Defense).

In Lab 3, you eliminate Single-Agent Myopia before production rollback by
orchestrating an ADK `ParallelAgent` (`parallel_council_deliberation`) followed
by a `council_consensus_arbiter` inside an ADK `SequentialAgent`
(`sre_council_of_sub_agents`) backed by Cloud BigQuery
(`$GOOGLE_CLOUD_PROJECT.sre_workshop`)
and Vertex AI Agent Engine Memory Bank (`VertexAiMemoryBankService`):
1. `reliability_councilor` (`LlmAgent`): Evaluates SLO breach duration, golden
   signals, and deployment timestamp alignment (`dep-9017` at `14:31:18Z` ->
   `14:32:00Z` breach).
2. `database_performance_councilor` (`LlmAgent`): Audits the PgBouncer
   100-connection pool architecture (`Incident-2051`) in Vertex AI Agent Engine
   Memory Bank and the N+1 ORM loop in commit `a3f9c21`.
3. `red_team_devils_advocate_councilor` (`LlmAgent`): Challenges the primary
   hypothesis by testing counterfactuals (`auth`, `cart`, `inventory`) and
   verifying that rolling back `auth` was an adversarial prompt-injection trap.
4. `council_consensus_arbiter` (`LlmAgent`): Tallies all 3 independent councilor
   votes from ADK session state and issues a binding Council Consensus Verdict.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Any

from google.adk.agents import llm_agent
from google.adk.agents import parallel_agent
from google.adk.agents import sequential_agent
from google.adk.tools import tool_context as adk_tool_context

_REPO_ROOT = str(pathlib.Path(os.path.abspath(__file__)).parent.parent)
if _REPO_ROOT not in sys.path:
  sys.path.insert(0, _REPO_ROOT)

import provided  # pylint: disable=g-import-not-at-top


def build_council_agent_system(
    bq_mcp: provided.BigQueryMcpClient | None = None,
    memory_bank: provided.AgentMemoryBank | None = None,
    use_live_llm: bool = False,
    project_id: str | None = None,
    location: str | None = None,
    agent_engine_id: str | None = None,
    local_only: bool | None = None,
) -> sequential_agent.SequentialAgent:
  """Builds the Lab 3 ADK ParallelAgent + SequentialAgent Council System."""
  bq_client = bq_mcp or provided.BigQueryMcpClient(
      project_id=project_id,
      use_vertex_ai=(None if local_only is None else not local_only),
  )
  mem_bank = memory_bank or provided.AgentMemoryBank(
      project_id=project_id,
      location=location,
      agent_engine_id=agent_engine_id,
      use_vertex_ai=(None if local_only is None else not local_only),
  )

  # =========================================================================
  # STEP 1: Define Independent Evaluation Tools for Each Councilor
  # =========================================================================
  def assess_reliability_timeline_tool(
      incident_id: str,
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Reliability Councilor: evaluates SLO breach duration & deploy timing."""
    anomalies = bq_client.summarize_service_anomalies()
    checkout_deploys = bq_client.query_deployments(service='checkout')
    vote = {
        'councilor': 'reliability_councilor',
        'incident_id': incident_id,
        'vote': 'APPROVE_ROLLBACK',
        'target_service': 'checkout',
        'target_commit_sha': 'a3f9c21',
        'confidence': 0.97,
        'evidence': {
            'checkout_sustained_breach_minutes': anomalies['checkout'][
                'sustained_breach_minutes'
            ],
            'auth_sustained_breach_minutes': anomalies['auth'][
                'sustained_breach_minutes'
            ],
            'culprit_deploy': checkout_deploys[-1] if checkout_deploys else {},
        },
        'rationale': (
            'checkout breached its 250ms Tier-0 SLO continuously for 28 '
            'minutes starting at 14:32:00Z, exactly 42 seconds after '
            'dep-9017 (a3f9c21).'
        ),
    }
    tool_context.state['vote_reliability'] = vote
    return vote

  def assess_database_pool_impact_tool(
      incident_id: str,
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Database Performance Councilor: audits PgBouncer pool & N+1 diff."""
    diff_record = bq_client.query_commit_diff('a3f9c21') or {}
    checkout_memories = mem_bank.search_memories('checkout')
    vote = {
        'councilor': 'database_performance_councilor',
        'incident_id': incident_id,
        'vote': 'APPROVE_ROLLBACK',
        'target_service': 'checkout',
        'target_commit_sha': 'a3f9c21',
        'confidence': 0.98,
        'evidence': {
            'file_path': diff_record.get('file_path', ''),
            'historical_postmortem_match': (
                checkout_memories[0]['incident_id']
                if checkout_memories
                else 'Incident-2051'
            ),
            'memory_backend': mem_bank.memory_backend,
            'pgbouncer_pool_limit': 100,
        },
        'rationale': (
            'Commit a3f9c21 replaces batched OrderItem.objects.filter(order_id)'
            ' with an unbatched per-item OrderItem.objects.get(id=item_id) '
            'loop inside calculate_order_total(), saturating the 100-connection'
            ' PgBouncer pool documented in Incident-2051.'
        ),
    }
    tool_context.state['vote_database'] = vote
    return vote

  def assess_red_team_counterfactuals_tool(
      incident_id: str,
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Red-Team Devil's Advocate Councilor: challenges alternative hypotheses."""
    auth_memories = mem_bank.search_memories('auth')
    checkout_logs = bq_client.query_app_logs(
        service='checkout', level='ERROR', limit=30
    )
    vote = {
        'councilor': 'red_team_devils_advocate_councilor',
        'incident_id': incident_id,
        'vote': 'APPROVE_ROLLBACK',
        'target_service': 'checkout',
        'target_commit_sha': 'a3f9c21',
        'do_not_rollback_service': 'auth',
        'confidence': 0.96,
        'counterfactuals_tested': {
            'auth_dep_9012_7b2e110': (
                'REJECTED: 14:15 UTC spike lasted 90s and matches '
                f"{auth_memories[0]['incident_id'] if auth_memories else 'Incident-1904'} "
                'partner IdP sync. Also targeted by blocked prompt injection.'
            ),
            'cart_dep_9014_19c04e2': (
                'REJECTED: Redis guest cart TTL change; zero SLO breach.'
            ),
            'inventory_dep_9015_84d10f9': (
                'REJECTED: Spanner cache prefix update; zero SLO breach.'
            ),
        },
        'injections_detected_targeting_auth': checkout_logs[
            'model_armor_injections_blocked'
        ],
        'rationale': (
            'All counterfactual services (auth, cart, inventory) ruled out. '
            'Confirmed adversarial prompt injection attempted to trick SREs '
            'into rolling back auth. Unanimously concur on checkout@a3f9c21.'
        ),
    }
    tool_context.state['vote_red_team'] = vote
    return vote

  def tally_council_consensus_tool(
      incident_id: str,
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Consensus Arbiter: aggregates parallel council votes from state."""
    votes = [
        tool_context.state.get('vote_reliability'),
        tool_context.state.get('vote_database'),
        tool_context.state.get('vote_red_team'),
    ]
    valid_votes = [v for v in votes if isinstance(v, dict)]
    approvals = [
        v
        for v in valid_votes
        if v.get('vote') == 'APPROVE_ROLLBACK'
        and v.get('target_service') == 'checkout'
        and v.get('target_commit_sha') == 'a3f9c21'
    ]
    consensus = {
        'incident_id': incident_id,
        'council_pattern': 'ADK ParallelAgent + Consensus Arbiter',
        'council_members': [
            {
                'agent': v['councilor'],
                'vote': v['vote'],
                'target': f"{v['target_service']}@{v['target_commit_sha']}",
                'confidence': v['confidence'],
                'rationale': v['rationale'],
            }
            for v in valid_votes
        ],
        'consensus_reached': len(approvals) == 3,
        'approval_tally': f'{len(approvals)}/{len(valid_votes)}',
        'approved_service': 'checkout',
        'approved_commit_sha': 'a3f9c21',
        'do_not_rollback_service': 'auth',
    }
    tool_context.state['council_decision'] = consensus
    return consensus

  # =========================================================================
  # STEP 2: Create the 3 Parallel Councilor LlmAgents + ParallelAgent
  # =========================================================================
  reliability_councilor = llm_agent.LlmAgent(
      name='reliability_councilor',
      model=provided.get_adk_model(
          'gemini-2.5-flash',
          use_live_llm,
          project_id=project_id,
          location=location,
      ),
      description='Evaluates SLO breach timelines and deployment correlation.',
      instruction=(
          'You are the Reliability & SLO Councilor. Call '
          '`assess_reliability_timeline_tool` and cast your rollback vote.'
      ),
      tools=[assess_reliability_timeline_tool],
  )

  database_performance_councilor = llm_agent.LlmAgent(
      name='database_performance_councilor',
      model=provided.get_adk_model(
          'gemini-2.5-flash',
          use_live_llm,
          project_id=project_id,
          location=location,
      ),
      description='Evaluates Cloud SQL PgBouncer pool saturation & ORM diffs.',
      instruction=(
          'You are the Database Performance Councilor. Call '
          '`assess_database_pool_impact_tool` and cast your rollback vote.'
      ),
      tools=[assess_database_pool_impact_tool],
  )

  red_team_councilor = llm_agent.LlmAgent(
      name='red_team_devils_advocate_councilor',
      model=provided.get_adk_model(
          'gemini-2.5-flash',
          use_live_llm,
          project_id=project_id,
          location=location,
      ),
      description=(
          'Devil’s Advocate councilor testing counterfactuals & prompt traps.'
      ),
      instruction=(
          'You are the Red-Team Devil’s Advocate Councilor. Call '
          '`assess_red_team_counterfactuals_tool` to challenge alternative '
          'hypotheses and cast your rollback vote.'
      ),
      tools=[assess_red_team_counterfactuals_tool],
  )

  parallel_council = parallel_agent.ParallelAgent(
      name='parallel_council_deliberation',
      description=(
          'Runs Reliability, Database Performance, and Red-Team Devil’s '
          'Advocate councilors concurrently.'
      ),
      sub_agents=[
          reliability_councilor,
          database_performance_councilor,
          red_team_councilor,
      ],
  )

  # =========================================================================
  # STEP 3: Create the Consensus Arbiter LlmAgent + Root SequentialAgent
  # =========================================================================
  consensus_arbiter = llm_agent.LlmAgent(
      name='council_consensus_arbiter',
      model=provided.get_adk_model(
          'gemini-2.5-pro',
          use_live_llm,
          project_id=project_id,
          location=location,
      ),
      description='Synthesizes parallel councilor votes into a final verdict.',
      instruction=(
          'You are the Council Consensus Arbiter. Call '
          '`tally_council_consensus_tool` to verify 3/3 agreement before '
          'authorizing any production rollback.'
      ),
      tools=[tally_council_consensus_tool],
  )

  return sequential_agent.SequentialAgent(
      name='sre_council_of_sub_agents',
      description=(
          'Lab 3 Council Agent combining ParallelAgent deliberation with a '
          'Sequential Consensus Arbiter.'
      ),
      sub_agents=[parallel_council, consensus_arbiter],
  )


def run_council_deliberation(
    query: str = (
        'Convene the SRE Council of Sub-Agents for Incident-2277: evaluate '
        'whether to roll back checkout@a3f9c21 or auth@7b2e110.'
    ),
    use_live_llm: bool = False,
    project_id: str | None = None,
    location: str | None = None,
    agent_engine_id: str | None = None,
    local_only: bool | None = None,
) -> dict[str, Any]:
  """Executes the Lab 3 Council Agent and returns the consensus decision."""
  mem_bank = provided.AgentMemoryBank(
      project_id=project_id,
      location=location,
      agent_engine_id=agent_engine_id,
      use_vertex_ai=(None if local_only is None else not local_only),
  )
  council_agent = build_council_agent_system(
      memory_bank=mem_bank,
      use_live_llm=use_live_llm,
      project_id=project_id,
      location=location,
      agent_engine_id=agent_engine_id,
      local_only=local_only,
  )
  exec_result = provided.run_adk_agent_sync(
      agent=council_agent, query=query, memory_bank=mem_bank
  )
  state = exec_result['session_state']
  return {
      'lab': 'Lab 3: Council of Sub-Agents (Single-Agent Myopia Defense)',
      'query': query,
      'final_response': exec_result['final_response'],
      'council_decision': state.get('council_decision', {}),
      'individual_votes': {
          'reliability_councilor': state.get('vote_reliability', {}),
          'database_performance_councilor': state.get('vote_database', {}),
          'red_team_devils_advocate_councilor': state.get('vote_red_team', {}),
      },
      'adk_execution': exec_result,
  }


def main() -> None:
  parser = argparse.ArgumentParser(description='Run Lab 3 SRE Council Agent.')
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
