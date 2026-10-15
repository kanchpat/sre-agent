"""SRE Guardian (Incident-2277) — Learner Starter File (Labs 1-4).

Complete the progressive functions below as you work through the 20 Questions
for the Agentic Enterprise workshop, or work directly inside the individual lab
folders (`prework/`, `lab1_triage_agent/`,
`lab2_guardrails_reflection_sandbox/`, `lab3_council_agent/`,
`lab4_governance_and_a2a/`). Compare with `agent_complete.py` at any time.
"""

from collections.abc import Sequence
import os
import pathlib
import sys
from typing import Any

_REPO_ROOT = str(pathlib.Path(os.path.abspath(__file__)).parent)
if _REPO_ROOT not in sys.path:
  sys.path.insert(0, _REPO_ROOT)

import provided  # pylint: disable=g-import-not-at-top

# ==============================================================================
# LAB 1 [BUILD]: Managed Agents API, Agent Skills & Sandbox (Q#1, 3, 7, 10)
# ==============================================================================


def upload_triage_skill() -> dict[str, Any]:
  """Func 1 (Q#7 / Slides 29-30): Loads incident-triage-runbook/SKILL.md.

  Demonstrates L1/L2/L3 progressive disclosure so agents only load ~50 tokens
  of metadata upfront and pull the full 5-step runbook on demand.

  Returns:
    Skill registration metadata dictionary.
  """
  # Exercise [Lab 1 - Step 1]: Load `skills/incident-triage-runbook/SKILL.md`
  # using `provided.resolve_confined_file` and return the L1/L2 skill metadata.
  raise NotImplementedError("Complete upload_triage_skill in Lab 1.")


def create_code_execution_agent(
    skill_metadata: dict[str, Any],
) -> dict[str, Any]:
  """Func 2 (Q#3, Q#10 / Slides 18-19, 38): Creates Rung 2 Managed Agent.

  Args:
    skill_metadata: Skill registration dictionary from upload_triage_skill().

  Returns:
    Managed Agent resource descriptor and sandbox correlation findings.
  """
  del skill_metadata
  # Exercise [Lab 1 - Step 2]: Provision the Rung 2 Code Execution Agent with
  # the GA gVisor Agent Sandbox and compute pre/post-deploy p99 latency on
  # checkout.
  raise NotImplementedError("Complete create_code_execution_agent in Lab 1.")


# ==============================================================================
# LAB 2 [SCALE]: BigQuery MCP, Context, A2A & ADK Multi-Agent (Q#2, 4, 5, 6, 8)
# ==============================================================================


def connect_bigquery_mcp_and_context(
    bq_client: provided.BigQueryMcpClient,
) -> dict[str, Any]:
  """Func 3 (Q#5 / Slides 22-26): Queries BigQuery via MCP + Knowledge Catalog.

  Args:
    bq_client: Initialized BigQueryMcpClient instance.

  Returns:
    Structured investigation evidence from BigQuery and Knowledge Catalog.
  """
  del bq_client
  # Exercise [Lab 2 - Step 1]: Query `sre_workshop` tables (`app_logs`,
  # `deployments`, `commit_diffs`) via `bq_client` and attach Knowledge Catalog.
  raise NotImplementedError(
      "Complete connect_bigquery_mcp_and_context in Lab 2."
  )


def build_sre_guardian_multi_agent(
    skill_metadata: dict[str, Any],
    code_exec_agent: dict[str, Any],
    bq_evidence: dict[str, Any],
) -> dict[str, Any]:
  """Func 4 (Q#4, Q#6, Q#8 / Slides 20-28, 33-34): Builds ADK Multi-Agent Mesh.

  Args:
    skill_metadata: Loaded runbook skill descriptor.
    code_exec_agent: Rung 2 Managed Agent descriptor from Lab 1.
    bq_evidence: BigQuery MCP investigation results from Func 3.

  Returns:
    ADK multi-agent system topology and correlated root-cause diagnosis.
  """
  del skill_metadata, code_exec_agent, bq_evidence
  # Exercise [Lab 2 - Step 2]: Assemble the Rung 4 ADK Multi-Agent hierarchy
  # (`Routing Agent`, `Investigation Agent`, `Code Execution Agent`,
  # `Policy Agent`, and remote A2A `Change Mgmt Agent`) and synthesize the RCA.
  raise NotImplementedError("Complete build_sre_guardian_multi_agent in Lab 2.")


# ==============================================================================
# LAB 3 [OPTIMIZE]: Memory Bank, Flash Cost Tiering & Council/Judge (Q#9, 11-13)
# ==============================================================================


def configure_memory_and_cost_tiering(
    memory_bank: provided.AgentMemoryBank,
    sre_guardian: dict[str, Any],
) -> dict[str, Any]:
  """Func 5 (Q#9, Q#13 / Slides 31-32, 40): Memory Bank & Gemini Flash Tiering.

  Args:
    memory_bank: Initialized AgentMemoryBank instance.
    sre_guardian: Multi-agent descriptor from build_sre_guardian_multi_agent().

  Returns:
    Memory recall trace, new postmortem record, and cost-tiering telemetry.
  """
  del memory_bank, sre_guardian
  # Exercise [Lab 3 - Step 1]: Query `memory_bank.search_memories` for `auth`
  # and `checkout` to skip the 14:15 UTC `auth` red herring (Incident-1904),
  # and switch `Routing Agent` to `gemini-3.1-flash`.
  raise NotImplementedError(
      "Complete configure_memory_and_cost_tiering in Lab 3."
  )


def verify_with_council_and_judge(
    sre_guardian: dict[str, Any],
    memory_trace: dict[str, Any],
) -> dict[str, Any]:
  """Func 6 (Q#11, Q#12 / Slides 35-37, 39): Guardrails, Reflection & Council.

  Args:
    sre_guardian: Multi-agent descriptor containing the root-cause diagnosis.
    memory_trace: Memory Bank recall output from Func 5.

  Returns:
    Verification verdict across Guardrails, Self-Reflection, Judge, and Council.
  """
  del sre_guardian, memory_trace
  # Exercise [Lab 3 - Step 2]: Verify the 3-part evidence rubric and run the
  # Guardrails, Self Reflection + LLM-as-a-Judge, and Council Agent checks.
  raise NotImplementedError("Complete verify_with_council_and_judge in Lab 3.")


# ==============================================================================
# LAB 4 [GOVERN]: Identity, Registry, Gateway, Model Armor & SCC (Q#14-20)
# ==============================================================================


def execute_governed_remediation(
    gateway: provided.AgentGatewayEnforcer,
    model_armor: provided.ModelArmorInspector,
    sre_guardian: dict[str, Any],
    council_verdict: dict[str, Any],
    caller_persona_key: str = "incident_commander",
) -> dict[str, Any]:
  """Func 7 (Q#14-Q#20 / Slides 41-47): Full Governed Rollback & Red-Team Test.

  Args:
    gateway: Initialized AgentGatewayEnforcer instance.
    model_armor: Initialized ModelArmorInspector instance.
    sre_guardian: Multi-agent descriptor from Lab 2/3.
    council_verdict: Verification output from verify_with_council_and_judge().
    caller_persona_key: Key in CALLER_PERSONAS ('junior_oncall' or
      'incident_commander').

  Returns:
    End-to-end governance audit record, Model Armor telemetry, and rollback
    result.
  """
  del gateway, model_armor, sre_guardian, council_verdict, caller_persona_key
  # Exercise [Lab 4]: Register the agent fleet in Agent Registry, inspect logs
  # with Model Armor, and authorize the rollback through Agent Gateway.
  raise NotImplementedError("Complete execute_governed_remediation in Lab 4.")


def show_usage(unused_argv: Sequence[str]) -> None:
  """Prints starter instructions."""
  print(
      "Complete the exercises in agent.py or individual lab folders, or run "
      "agent_complete.py to see the reference solution in action."
  )
