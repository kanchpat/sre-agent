"""Lab 4 (Starter Outline): Agent Registry, Skill Registry, Agent Identity, Model Armor, SCC & Cross-Agent A2A Rollback.

In Lab 4, you govern and execute the final production remediation across two
separate ADK agents (`sre_governance_coordinator` calling
`change_mgmt_a2a_agent` over A2A) enforced by:
1. Agent Registry (`AgentGatewayEnforcer.register_fleet`): Inventories all
   agents (`sre_triage_coordinator`, `sre_council_of_sub_agents`,
   `sre_governance_coordinator`, `change_mgmt_a2a_agent`) and MCP/A2A tools.
2. Skill Registry (`EnterpriseSkillRegistry` implementing
   `google.adk.skills.SkillRegistry`): Registers and version-pins
   `incident-triage-runbook` (`v2.1.0`) and `governed-rollback-playbook`
   (`v1.4.0`), exposing them via `SkillToolset`.
3. Agent Identity (`CallerIdentity` OBO Delegation): Verifies that
   `junior_oncall` (`roles/sre.juniorOncall`) is blocked at the Gateway while
   `incident_commander` (`roles/sre.incidentCommander`) is authorized.
4. Model Armor & Semantic Governance Policy (`SGP-001`, `SGP-002`): Protects
   `auth` from adversarial prompt-injection rollbacks and redacts SDP PII.
5. Security Command Center (SCC) Threat Detection: Emits structured SCC alerts
   whenever a policy violation (`SGP-002`) or unauthorized OBO attempt occurs.
6. Cross-Agent A2A Execution & Vertex AI Memory Bank Persistence:
   `sre_governance_coordinator` invokes `change_mgmt_a2a_agent` via
   `SubAgentDispatchTool` (`call_change_mgmt_a2a_agent`) to execute the governed
   rollback of `checkout@a3f9c21` and persist the `Incident-2277` postmortem
   into Vertex AI Agent Engine Memory Bank (`VertexAiMemoryBankService`).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from typing import Any

from google.adk.agents import llm_agent
from google.adk.tools import tool_context as adk_tool_context

_REPO_ROOT = str(pathlib.Path(os.path.abspath(__file__)).parent.parent)
if _REPO_ROOT not in sys.path:
  sys.path.insert(0, _REPO_ROOT)

import provided  # pylint: disable=g-import-not-at-top

FLEET_AGENTS_MANIFEST: list[dict[str, Any]] = [
    {
        'name': 'sre_triage_coordinator',
        'model': 'gemini-2.5-pro',
        'role': 'Lab 1 Triage Orchestrator',
    },
    {
        'name': 'metrics_and_catalog_agent',
        'model': 'gemini-2.5-flash',
        'role': 'Lab 1 BigQuery Metrics & Knowledge Catalog Specialist',
    },
    {
        'name': 'logs_and_memory_agent',
        'model': 'gemini-2.5-flash',
        'role': 'Lab 1 Logs & Vertex AI Memory Bank Specialist',
    },
    {
        'name': 'sre_council_of_sub_agents',
        'model': 'gemini-2.5-pro',
        'role': 'Lab 3 Parallel Council & Consensus Arbiter',
    },
    {
        'name': 'sre_governance_coordinator',
        'model': 'gemini-2.5-pro',
        'role': 'Lab 4 Governance & Policy Caller Agent',
    },
    {
        'name': 'change_mgmt_a2a_agent',
        'model': 'gemini-2.5-flash',
        'role': 'Lab 4 Remote A2A Change Management Execution Agent',
    },
]

AUTHORIZED_TOOLS_MANIFEST: list[str] = [
    'mcp://bigquery/sre_workshop.service_metrics',
    'mcp://bigquery/sre_workshop.app_logs',
    'mcp://bigquery/sre_workshop.deployments',
    'mcp://bigquery/sre_workshop.commit_diffs',
    'mcp://knowledge-catalog/lookup_context',
    'a2a://change-mgmt-agent/execute_governed_rollback',
]


def build_governance_and_a2a_agents(
    caller_persona: str = 'incident_commander',
    gateway: provided.AgentGatewayEnforcer | None = None,
    skill_registry: provided.EnterpriseSkillRegistry | None = None,
    memory_bank: provided.AgentMemoryBank | None = None,
    use_live_llm: bool = False,
    project_id: str | None = None,
    location: str | None = None,
    agent_engine_id: str | None = None,
    local_only: bool | None = None,
) -> tuple[
    llm_agent.LlmAgent,
    llm_agent.LlmAgent,
    provided.AgentGatewayEnforcer,
    provided.EnterpriseSkillRegistry,
    provided.AgentMemoryBank,
]:
  """Builds the Lab 4 Caller Agent and Remote A2A Change Management Agent."""
  if caller_persona not in provided.CALLER_PERSONAS:
    raise ValueError(f'Unknown caller_persona: {caller_persona!r}')
  caller = provided.CALLER_PERSONAS[caller_persona]

  gw = gateway or provided.AgentGatewayEnforcer()
  s_reg = skill_registry or provided.EnterpriseSkillRegistry()
  mem_bank = memory_bank or provided.AgentMemoryBank(
      project_id=project_id,
      location=location,
      agent_engine_id=agent_engine_id,
      use_vertex_ai=(None if local_only is None else not local_only),
  )

  # Register fleet in Agent Registry and skills in EnterpriseSkillRegistry
  s_reg.register_default_workshop_skills()
  rollback_skill_toolset = s_reg.to_skill_toolset(
      skill_names=['governed-rollback-playbook']
  )

  # =========================================================================
  # STEP 1: Define Remote A2A Change Management Agent & Rollback Tool
  # =========================================================================
  def execute_governed_rollback_action_tool(
      target_service: str,
      target_sha: str,
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Executed by change_mgmt_a2a_agent: enforces SGP, OBO & SCC at Gateway."""
    # First test and block any adversarial attempt to roll back `auth` (SGP-002)
    blocked_auth_attempt = gw.authorize_and_route_rollback(
        caller=caller,
        target_service='auth',
        target_sha='7b2e110',
        council_approved=False,
        evidence_complete=False,
    )
    # Also verify what happens when junior_oncall attempts checkout rollback
    junior_caller = provided.CALLER_PERSONAS['junior_oncall']
    junior_obo_attempt = gw.authorize_and_route_rollback(
        caller=junior_caller,
        target_service=target_service,
        target_sha=target_sha,
        council_approved=True,
        evidence_complete=True,
    )
    # Now execute the actual caller's governed rollback request
    active_decision = gw.authorize_and_route_rollback(
        caller=caller,
        target_service=target_service,
        target_sha=target_sha,
        council_approved=True,
        evidence_complete=True,
    )

    stored_postmortem: dict[str, Any] | None = None
    if active_decision['allowed']:
      stored_postmortem = mem_bank.store_postmortem({
          'incident_id': 'Incident-2277',
          'service': target_service,
          'title': (
              'Checkout Tier-0 HTTP 500 Outage from N+1 OrderItem Query in '
              f'dep-9017 ({target_sha})'
          ),
          'root_cause_Pattern': 'n_plus_1_db_connection_pool_exhaustion',
          'summary': (
              f'Deploy dep-9017 (commit {target_sha}) introduced an unbatched '
              'OrderItem.objects.get loop in services/checkout/orders.py, '
              'saturating the 100-connection PgBouncer pool at 14:32 UTC.'
          ),
          'resolution': (
              f'Executed governed A2A rollback of {target_service}@{target_sha}'
              f' on behalf of {caller.user_email} ({caller.role}).'
          ),
      })

    a2a_payload = {
        'executing_agent': 'change_mgmt_a2a_agent',
        'called_by_agent': 'sre_governance_coordinator',
        'obo_caller_identity': {
            'user_email': caller.user_email,
            'role': caller.role,
            'display_name': caller.display_name,
            'can_execute_prod_rollback': caller.can_execute_prod_rollback,
        },
        'active_caller_rollback_decision': active_decision,
        'sgp_002_auth_protection_simulation': blocked_auth_attempt,
        'junior_oncall_obo_simulation': junior_obo_attempt,
        'scc_threat_alerts': list(gw.scc_threat_alerts),
        'stored_postmortem': stored_postmortem,
    }
    tool_context.state['a2a_execution_result'] = a2a_payload
    return a2a_payload

  change_mgmt_a2a_agent = llm_agent.LlmAgent(
      name='change_mgmt_a2a_agent',
      model=provided.get_adk_model(
          'gemini-2.5-flash',
          use_live_llm,
          project_id=project_id,
          location=location,
      ),
      description=(
          'Remote Change Management A2A Agent that validates OBO identity, '
          'Semantic Governance Policies (SGP-001/SGP-002), and executes '
          'production rollbacks.'
      ),
      instruction=(
          'You are the Remote Change Management A2A Agent. When invoked by '
          '`sre_governance_coordinator`, call '
          '`execute_governed_rollback_action_tool` for `checkout` commit '
          '`a3f9c21` and return the Gateway enforcement and SCC audit trail.'
      ),
      tools=[execute_governed_rollback_action_tool],
  )

  # =========================================================================
  # STEP 2: Define Caller Agent (`sre_governance_coordinator`) Tools
  # =========================================================================
  def inspect_fleet_and_skill_registries_tool(
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Registers & audits the Agent Registry and Enterprise Skill Registry."""
    agent_reg_snapshot = gw.register_fleet(
        agents=FLEET_AGENTS_MANIFEST,
        tools=AUTHORIZED_TOOLS_MANIFEST,
    )
    skill_records = s_reg.list_governance_records()
    combined = {
        'agent_registry': agent_reg_snapshot,
        'skill_registry': {
            'registry_class': (
                'EnterpriseSkillRegistry(google.adk.skills.SkillRegistry)'
            ),
            'registered_skill_count': len(skill_records),
            'skills': skill_records,
        },
    }
    tool_context.state['registries_audit'] = combined
    return combined

  def verify_model_armor_and_policy_tool(
      target_service: str,
      tool_context: adk_tool_context.ToolContext,
  ) -> dict[str, Any]:
    """Runs Model Armor sanitization check before A2A delegation."""
    armor = provided.ModelArmorInspector(enabled=True)
    bq = provided.BigQueryMcpClient(
        model_armor=armor,
        project_id=project_id,
        use_vertex_ai=(None if local_only is None else not local_only),
    )
    log_check = bq.query_app_logs(
        service=target_service, level='ERROR', limit=100
    )
    armor_status = {
        'template_id': 'sre-guardian-model-armor-prod',
        'target_service': target_service,
        'injections_blocked': log_check['model_armor_injections_blocked'],
        'pii_redacted': log_check['model_armor_pii_redacted'],
        'semantic_policies_enforced': [
            'SGP-001-REQUIRE-EVIDENCE-AND-COUNCIL',
            'SGP-002-PROTECT-AUTH-RED-HERRING',
        ],
    }
    tool_context.state['model_armor_audit'] = armor_status
    return armor_status

  # =========================================================================
  # STEP 3: Wire `sre_governance_coordinator` -> `change_mgmt_a2a_agent` via A2A
  # =========================================================================
  sre_governance_coordinator = llm_agent.LlmAgent(
      name='sre_governance_coordinator',
      model=provided.get_adk_model(
          'gemini-2.5-pro',
          use_live_llm,
          project_id=project_id,
          location=location,
      ),
      description=(
          'SRE Governance Coordinator that audits Agent & Skill Registries, '
          'verifies Model Armor, and invokes `change_mgmt_a2a_agent` over A2A.'
      ),
      instruction=(
          'You are the SRE Governance Coordinator. Load the '
          '`governed-rollback-playbook` skill from the Skill Registry, verify '
          'Agent & Skill Registries and Model Armor status, and then execute '
          'the rollback by calling `call_change_mgmt_a2a_agent`.'
      ),
      tools=[
          rollback_skill_toolset,
          inspect_fleet_and_skill_registries_tool,
          verify_model_armor_and_policy_tool,
          provided.SubAgentDispatchTool(change_mgmt_a2a_agent),
      ],
      sub_agents=[change_mgmt_a2a_agent],
  )

  return (
      sre_governance_coordinator,
      change_mgmt_a2a_agent,
      gw,
      s_reg,
      mem_bank,
  )


def run_lab4_governance_and_a2a(
    caller_persona: str = 'incident_commander',
    query: str = (
        'Audit the Agent Registry and Skill Registry, verify Model Armor & '
        'OBO Caller Identity, and execute the governed rollback of '
        'checkout@a3f9c21 by calling change_mgmt_a2a_agent.'
    ),
    use_live_llm: bool = False,
    project_id: str | None = None,
    location: str | None = None,
    agent_engine_id: str | None = None,
    local_only: bool | None = None,
) -> dict[str, Any]:
  """Executes Lab 4: Agent/Skill Registries, OBO Identity, Model Armor, SCC & A2A call."""
  coordinator, _, gw, s_reg, mem_bank = build_governance_and_a2a_agents(
      caller_persona=caller_persona,
      use_live_llm=use_live_llm,
      project_id=project_id,
      location=location,
      agent_engine_id=agent_engine_id,
      local_only=local_only,
  )
  exec_result = provided.run_adk_agent_sync(
      agent=coordinator,
      query=query,
      memory_bank=mem_bank,
  )
  state = exec_result['session_state']
  registries_audit = state.get('registries_audit', {})
  a2a_res = state.get('a2a_execution_result', {})

  return {
      'lab': (
          'Lab 4: Agent Registry, Skill Registry, Agent Identity, Model Armor, '
          'SCC & Cross-Agent A2A Execution'
      ),
      'query': query,
      'caller_persona': caller_persona,
      'final_response': exec_result['final_response'],
      'agent_registry': registries_audit.get('agent_registry', {}),
      'skill_registry': registries_audit.get(
          'skill_registry',
          {
              'registered_skill_count': len(s_reg.list_frontmatters()),
              'skills': s_reg.list_governance_records(),
          },
      ),
      'model_armor': state.get('model_armor_audit', {}),
      'agent_identity_obo': a2a_res.get('obo_caller_identity', {}),
      'a2a_cross_agent_call': {
          'caller_agent': 'sre_governance_coordinator',
          'callee_agent': 'change_mgmt_a2a_agent',
          'active_caller_decision': a2a_res.get(
              'active_caller_rollback_decision', {}
          ),
          'junior_oncall_obo_simulation': a2a_res.get(
              'junior_oncall_obo_simulation', {}
          ),
          'sgp_002_auth_protection_simulation': a2a_res.get(
              'sgp_002_auth_protection_simulation', {}
          ),
      },
      'scc_threat_findings': list(gw.scc_threat_alerts),
      'postmortem_memory_stored': a2a_res.get('stored_postmortem'),
      'adk_execution': exec_result,
  }


def main() -> None:
  parser = argparse.ArgumentParser(
      description=(
          'Run Lab 4: Agent Registry, Skill Registry, OBO Identity, Model '
          'Armor, SCC & Cross-Agent A2A Rollback.'
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
