"""Unit and integration tests for Prework and Labs 1-4 Vertex AI & ADK Agents."""

import os
import pathlib
import sys

from absl.testing import absltest

_REPO_ROOT = str(pathlib.Path(os.path.abspath(__file__)).parent)
if _REPO_ROOT not in sys.path:
  sys.path.insert(0, _REPO_ROOT)

import agent_complete  # pylint: disable=g-import-not-at-top
import app  # pylint: disable=g-import-not-at-top
from evals import evaluate_sre_agent  # pylint: disable=g-import-not-at-top
from lab1_triage_agent import agent_complete as lab1_complete  # pylint: disable=g-import-not-at-top
from lab2_guardrails_reflection_sandbox import agent_complete as lab2_complete  # pylint: disable=g-import-not-at-top
from lab3_council_agent import agent_complete as lab3_complete  # pylint: disable=g-import-not-at-top
from lab4_governance_and_a2a import agent_complete as lab4_complete  # pylint: disable=g-import-not-at-top
from prework import seed_bigquery_and_memory  # pylint: disable=g-import-not-at-top
import provided  # pylint: disable=g-import-not-at-top


class SreAgentWorkshopTest(absltest.TestCase):

  def test_vertex_ai_and_bigquery_primitives_configuration(self):
    cfg = provided.get_vertex_ai_config(
        project_id="demo-sre-project",
        location="us-central1",
        agent_engine_id="1234567890",
        use_vertex_ai=True,
    )
    self.assertEqual(cfg.project_id, "demo-sre-project")
    self.assertEqual(cfg.location, "us-central1")
    self.assertEqual(cfg.agent_engine_id, "1234567890")
    self.assertTrue(cfg.use_vertex_ai)

    bq_client = provided.BigQueryMcpClient(
        project_id="demo-sre-project",
        use_vertex_ai=False,
    )
    bq_toolset = bq_client.create_adk_bigquery_toolset()
    self.assertEqual(type(bq_toolset).__name__, "BigQueryToolset")

    mem_bank = provided.AgentMemoryBank(
        project_id="demo-sre-project",
        location="us-central1",
        agent_engine_id="1234567890",
        use_vertex_ai=True,
    )
    mem_service = mem_bank.create_memory_service()
    sess_service = mem_bank.create_session_service()
    self.assertEqual(type(mem_service).__name__, "VertexAiMemoryBankService")
    self.assertEqual(type(sess_service).__name__, "VertexAiSessionService")

  def test_prework_seeds_bigquery_and_long_term_memory(self):
    prework_report = seed_bigquery_and_memory.run_prework(log_rows=1200)
    self.assertEqual(prework_report["status"], "PREWORK_COMPLETE")
    self.assertEqual(
        prework_report["bigquery_tables"]["sre_workshop.service_metrics"], 240
    )
    self.assertEqual(
        prework_report["bigquery_tables"]["sre_workshop.app_logs"], 1200
    )
    self.assertEqual(
        prework_report["bigquery_tables"]["sre_workshop.deployments"], 4
    )
    self.assertEqual(
        prework_report["bigquery_tables"]["sre_workshop.commit_diffs"], 4
    )
    ltm = prework_report["long_term_memory"]
    self.assertEqual(ltm["seeded_postmortems_count"], 2)
    self.assertTrue(ltm["auth_memory_verified"])
    self.assertTrue(ltm["checkout_memory_verified"])

  def test_modular_lab1_triage_multi_agent_system(self):
    res = lab1_complete.answer_triage_query(
        query=(
            "Why did auth spike at 14:15 UTC, and is checkout commit a3f9c21 "
            "the real root cause of Incident-2277?"
        )
    )
    self.assertIn("checkout", res["answer"])
    self.assertIn("a3f9c21", res["answer"])
    self.assertIn("Incident-1904", res["answer"])
    findings = res["triage_findings"]
    self.assertEqual(findings["root_cause_service"], "checkout")
    self.assertEqual(findings["red_herring_service"], "auth")
    self.assertEqual(findings["culprit_commit_sha"], "a3f9c21")
    called_tool_names = [
        tc["tool_name"] for tc in res["adk_execution"]["tool_calls"]
    ]
    self.assertIn("load_skill", called_tool_names)
    self.assertIn("call_metrics_and_catalog_agent", called_tool_names)
    self.assertIn("call_logs_and_memory_agent", called_tool_names)
    self.assertIn("call_deploy_and_diff_agent", called_tool_names)

  def test_modular_lab2_guardrails_reflection_judge_observability_sandbox(self):
    res = lab2_complete.run_lab2_verification()
    sandbox = res["sandbox_correlation"]
    self.assertEqual(sandbox["target_service"], "checkout")
    self.assertGreater(sandbox["z_score"], 40.0)
    self.assertTrue(sandbox["ast_diff_verified_n_plus_1"])

    guardrails = res["guardrails_report"]
    self.assertGreater(guardrails["model_armor_injections_blocked"], 0)
    self.assertGreater(guardrails["model_armor_pii_redacted"], 0)
    self.assertFalse(guardrails["pii_leaked_in_output"])
    self.assertTrue(guardrails["direct_prompt_injection_blocked_in_callback"])

    reflection = res["self_reflection"]
    self.assertTrue(reflection["self_reflection_passed"])
    self.assertEqual(
        reflection["iteration_1_naive_critique"]["reflection_verdict"],
        "REJECTED_BY_SELF_REFLECTION",
    )

    judge = res["llm_judge_evaluation"]
    self.assertEqual(judge["verdict"], "PASS")
    self.assertGreaterEqual(judge["quality_score"], 0.95)
    self.assertIn("VERTEX_AI", judge["judge_backend"])

    obs = res["observability"]
    self.assertGreater(obs["total_otel_spans"], 10)
    self.assertIn("AGENT_START", obs["span_types"])
    self.assertIn("TOOL_START", obs["span_types"])

  def test_modular_lab3_council_agent(self):
    res = lab3_complete.run_council_deliberation()
    decision = res["council_decision"]
    self.assertTrue(decision["consensus_reached"])
    self.assertEqual(decision["approval_tally"], "3/3")
    self.assertEqual(decision["approved_service"], "checkout")
    self.assertEqual(decision["approved_commit_sha"], "a3f9c21")
    self.assertEqual(decision["do_not_rollback_service"], "auth")
    self.assertLen(decision["council_members"], 3)

  def test_modular_lab4_governance_registries_obo_and_a2a(self):
    # 1. Incident Commander succeeds via cross-agent A2A call
    ic_res = lab4_complete.run_lab4_governance_and_a2a(
        caller_persona="incident_commander"
    )
    self.assertEqual(ic_res["agent_registry"]["agent_count"], 6)
    self.assertEqual(ic_res["skill_registry"]["registered_skill_count"], 2)
    a2a = ic_res["a2a_cross_agent_call"]
    self.assertEqual(a2a["caller_agent"], "sre_governance_coordinator")
    self.assertEqual(a2a["callee_agent"], "change_mgmt_a2a_agent")
    self.assertTrue(a2a["active_caller_decision"]["allowed"])
    self.assertEqual(
        a2a["active_caller_decision"]["status"],
        "EXECUTED_VIA_A2A_CHANGE_MGMT_AGENT",
    )
    self.assertIsNotNone(ic_res["postmortem_memory_stored"])
    self.assertGreaterEqual(len(ic_res["scc_threat_findings"]), 2)

    # 2. Junior On-Call is blocked by OBO identity at the Agent Gateway
    jr_res = lab4_complete.run_lab4_governance_and_a2a(
        caller_persona="junior_oncall"
    )
    jr_decision = jr_res["a2a_cross_agent_call"]["active_caller_decision"]
    self.assertFalse(jr_decision["allowed"])
    self.assertEqual(jr_decision["status"], "BLOCKED_BY_OBO_IDENTITY")
    self.assertIsNone(jr_res["postmortem_memory_stored"])

  def test_end_to_end_orchestrator_and_eval_runner(self):
    labs = agent_complete.run_all_labs()
    self.assertIn("modular_adk_labs", labs)
    eval_report = evaluate_sre_agent.evaluate_agent_run()
    self.assertTrue(eval_report["all_criteria_passed"])
    self.assertEqual(eval_report["overall_score"], 1.0)

    snapshot = app.build_incident_command_snapshot()
    self.assertEqual(
        snapshot["incident_banner"]["incident_id"], "Incident-2277"
    )
    self.assertGreaterEqual(len(snapshot["transaction_timeline"]), 8)
    html_ux = app.render_incident_command_html(
        ic_snapshot=snapshot, jr_snapshot=snapshot
    )
    self.assertIn("SRE Guardian (Incident-2277)", html_ux)
    self.assertIn("VERTEX_GENAI_EVAL", html_ux)
    self.assertIn("3. Lab 3: Eval", app.chat_ux.CHAT_UX_HTML)
    self.assertIn(
        "https://github.com/kanchpat/sre-agent/blob/main/",
        app.chat_ux.CHAT_UX_HTML,
    )
    self.assertIn("code_snippet", app.chat_ux.CHAT_UX_HTML)
    self.assertIn("tpl-incident-1904-diagram", app.chat_ux.CHAT_UX_HTML)
    self.assertIn("Incident-1904 → 2277 Diagram", app.chat_ux.CHAT_UX_HTML)
    lab1_turn = app.chat_ux.handle_chat_turn(
        lab_id="lab1",
        user_message="how is incident - 1904 connected with inccident-2277",
    )
    step3 = [e for e in lab1_turn["live_events"] if e["step"] == 3][0]
    self.assertTrue(step3.get("has_memory_diagram"))
    self.assertTrue(step3.get("auto_open"))
    eval_turn = app.chat_ux.handle_chat_turn(
        lab_id="lab3",
        user_message="Run the 5-pillar Gen AI Evaluation rubric",
    )
    self.assertEqual(eval_turn["eval_scorecard"]["passed_count"], 5)
    self.assertEqual(eval_turn["eval_scorecard"]["overall_score"], 1.0)


if __name__ == "__main__":
  absltest.main()
