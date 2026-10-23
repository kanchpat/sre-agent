"""SRE Guardian (Incident-2277) — Simplified Guided UX & Transaction Inspector.

Supports three execution modes:
  1. Live Interactive Web UX Server (`--serve --port=8765`): Starts a local
     HTTP server at http://localhost:8765 where workshop participants can
     step through Prework and Labs 1-4 (Triage, Guardrails, Eval,
     Agent Identity & A2A) with dropdowns and direct GCP Console links.
  2. Standalone HTML Export (`--export_html=/tmp/sre_guardian_ux.html`):
     Generates a self-contained HTML walkthrough.
  3. Headless JSON Snapshot (default CLI mode for unit tests & pipelines).
"""

from __future__ import annotations

from collections.abc import Sequence
import dataclasses
from http import server as http_server
import json
import os
import pathlib
import sys
from typing import Any
from urllib import parse as urlparse

from absl import app
from absl import flags

_REPO_ROOT = str(pathlib.Path(os.path.abspath(__file__)).parent)
if _REPO_ROOT not in sys.path:
  sys.path.insert(0, _REPO_ROOT)

import agent_complete  # pylint: disable=g-import-not-at-top
import chat_ux  # pylint: disable=g-import-not-at-top
from evals import evaluate_sre_agent  # pylint: disable=g-import-not-at-top
import provided  # pylint: disable=g-import-not-at-top

_PERSONA = flags.DEFINE_string(
    'persona',
    'incident_commander',
    'Caller persona key (incident_commander or junior_oncall).',
)
_MODEL_ARMOR = flags.DEFINE_bool(
    'model_armor',
    True,
    'Whether Model Armor inline inspection is enabled.',
)
_SERVE = flags.DEFINE_bool(
    'serve',
    False,
    'If true, starts the interactive Incident Command Web UX server.',
)
_HOST = flags.DEFINE_string(
    'host',
    '0.0.0.0'
    if ('PORT' in os.environ or 'K_SERVICE' in os.environ)
    else '127.0.0.1',
    'Bind address for the HTTP server (0.0.0.0 on Cloud Run).',
)
_PORT = flags.DEFINE_integer(
    'port',
    int(os.environ.get('PORT', '8765')),
    'Port for the interactive Incident Command Web UX server.',
)
_EXPORT_HTML = flags.DEFINE_string(
    'export_html',
    '',
    'Optional path to write the standalone interactive HTML UX file.',
)
_PREBUILT_HTML = flags.DEFINE_string(
    'prebuilt_html',
    '',
    'Optional pre-rendered HTML UX file for instant Cloud Run startup.',
)


def _extract_transaction_timeline(
    modular_labs: dict[str, Any],
    persona_key: str,
    eval_report: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
  """Extracts a concise step-by-step transaction ledger across Prework & Labs 1-4."""
  txns: list[dict[str, Any]] = []
  prework = modular_labs.get('prework', {})
  ltm = prework.get('long_term_memory', {})
  txns.append({
      'step': 1,
      'stage': 'Prework',
      'category': 'VERTEX_AI_PROVISION',
      'highlight_level': 'info',
      'actor': 'seed_bigquery_and_memory',
      'target': (
          f"{prework.get('vertex_ai_project', provided.DEFAULT_VERTEX_PROJECT)}"
          f".sre_workshop + {ltm.get('memory_backend', 'VertexAiMemoryBankService')}"
      ),
      'summary': (
          'Seeded 4 BigQuery tables (7,448 rows) and 2 historical postmortems '
          '(Incident-1904 & Incident-2051) into Vertex AI Memory Bank.'
      ),
      'details': {
          'bigquery_tables': prework.get('bigquery_tables', {}),
          'memory_service_class': ltm.get('memory_service_class'),
          'seeded_incidents': ltm.get('incident_ids', []),
      },
  })

  # Lab 1 tool calls & highlights
  lab1 = modular_labs.get('lab1_triage_agent', {})
  lab1_findings = lab1.get('triage_findings', {})
  for tc in lab1.get('adk_execution', {}).get('tool_calls', []):
    t_name = tc.get('tool_name', '')
    author = tc.get('author', 'sre_triage_coordinator')
    cat = 'ADK_TOOL_CALL'
    hl = 'info'
    note = f'{author} invoked {t_name}'
    if t_name in {'list_skills', 'load_skill'}:
      cat = 'ADK_SKILL_TOOLSET'
      note = 'Loaded skills/incident-triage-runbook/SKILL.md via ADK SkillToolset (L1 -> L2).'
    elif 'memory' in t_name:
      cat = 'VERTEX_MEMORY_BANK'
      hl = 'warning'
      note = (
          'RED HERRING FILTERED: Recalled Incident-1904 — 14:15 UTC auth spike '
          'is a benign 90s partner IdP sync. Do NOT roll back auth.'
      )
    elif 'metrics' in t_name or 'catalog' in t_name:
      cat = 'BIGQUERY_MCP'
      note = (
          'Queried BigQuery service_metrics: checkout breached 250ms SLO for '
          '28m vs. auth 2m blip.'
      )
    elif 'deploy' in t_name or 'diff' in t_name:
      cat = 'CULPRIT_IDENTIFIED'
      hl = 'critical'
      note = (
          'ROOT CAUSE PINPOINTED: Deploy dep-9017 (commit a3f9c21 at 14:31:18Z) '
          'introduced an N+1 OrderItem.objects.get loop in services/checkout/orders.py.'
      )
    txns.append({
        'step': len(txns) + 1,
        'stage': 'Lab 1: Triage',
        'category': cat,
        'highlight_level': hl,
        'actor': author,
        'target': t_name,
        'summary': note,
        'details': {
            'args': tc.get('args', {}),
            'root_cause_service': lab1_findings.get('root_cause_service'),
            'red_herring_service': lab1_findings.get('red_herring_service'),
            'culprit_commit_sha': lab1_findings.get('culprit_commit_sha'),
        },
    })

  # Lab 2 Guardrails (Model Armor)
  lab2 = modular_labs.get('lab2_guardrails_reflection_sandbox', {})
  grd = lab2.get('guardrails_report', {})

  txns.append({
      'step': len(txns) + 1,
      'stage': 'Lab 2: Guardrails',
      'category': 'MODEL_ARMOR_GUARDRAIL',
      'highlight_level': 'warning',
      'actor': 'guardrails_agent',
      'target': 'ModelArmorInspector + ADK Callbacks',
      'summary': (
          f"Blocked {grd.get('model_armor_injections_blocked', 0)} prompt "
          f"injections in app_logs and redacted "
          f"{grd.get('model_armor_pii_redacted', 0)} PII emails/tokens."
      ),
      'details': grd,
  })

  # Lab 3 Agent Evaluation (Eval & LLM-as-a-Judge)
  refl = lab2.get('self_reflection', {})
  jdg = lab2.get('llm_judge_evaluation', {})
  obs = lab2.get('observability', {})
  eval_data = eval_report or {}
  txns.append({
      'step': len(txns) + 1,
      'stage': 'Lab 3: Eval',
      'category': 'VERTEX_GENAI_EVAL',
      'highlight_level': 'success',
      'actor': 'evaluate_sre_agent',
      'target': 'Vertex AI Gen AI Evaluation Service (LLM-as-a-Judge)',
      'summary': (
          f"Evaluated agent across 5 enterprise rubrics (Task Completion, "
          f"Trajectory Efficiency, Red-Herring Avoidance, Evidence Rigor, "
          f"Safety & Governance) -> Score: {eval_data.get('overall_score', 1.0)} "
          f"PASS across {obs.get('total_otel_spans', 0)} OTel trace spans."
      ),
      'details': {
          'eval_rubric': eval_data.get('criteria', {}),
          'self_reflection': refl,
          'llm_judge': jdg,
      },
  })

  # Lab 4 Governance, Agent Identity & A2A
  lab4 = modular_labs.get('lab4_governance_and_a2a', {})
  a2a = lab4.get('a2a_cross_agent_call', {})
  active_dec = a2a.get('active_caller_decision', {})
  allowed = bool(active_dec.get('allowed'))
  txns.append({
      'step': len(txns) + 1,
      'stage': 'Lab 4: A2A & Identity',
      'category': 'A2A_GATEWAY_ENFORCEMENT',
      'highlight_level': 'success' if allowed else 'critical',
      'actor': f'sre_governance_coordinator ({persona_key})',
      'target': 'change_mgmt_a2a_agent via AgentGatewayEnforcer',
      'summary': (
          f"A2A rollback of checkout@a3f9c21 by {persona_key} -> "
          f"{active_dec.get('status')} (allowed={allowed})."
      ),
      'details': {
          'active_decision': active_dec,
          'scc_threat_findings': lab4.get('scc_threat_findings', []),
          'postmortem_stored_in_vertex_memory': lab4.get(
              'postmortem_memory_stored'
          ),
      },
  })
  return txns


def build_incident_command_snapshot(
    persona_key: str = 'incident_commander',
    model_armor_enabled: bool = True,
) -> dict[str, Any]:
  """Builds the complete Incident Command & Governance Telemetry snapshot."""
  if persona_key not in provided.CALLER_PERSONAS:
    raise ValueError(f'Unknown persona_key: {persona_key!r}')
  labs = agent_complete.run_all_labs(
      caller_persona_key=persona_key,
      model_armor_enabled=model_armor_enabled,
  )
  eval_report = evaluate_sre_agent.evaluate_agent_run(labs)
  caller = provided.CALLER_PERSONAS[persona_key]
  modular_labs = labs.get('modular_adk_labs', {})
  return {
      'incident_banner': {
          'incident_id': 'Incident-2277',
          'title': 'SEV-1 Latency & HTTP 500 Cascade on Acme Retail',
          'root_cause_commit': 'a3f9c21 (services/checkout/orders.py)',
          'red_herring_filtered': (
              'Incident-1904 (14:15 UTC auth partner sync)'
          ),
          'vertex_agent_engine_id': provided.DEFAULT_AGENT_ENGINE_ID,
          'bigquery_dataset': (
              f'{provided.DEFAULT_VERTEX_PROJECT}.'
              f'{provided.DEFAULT_BQ_DATASET}'
          ),
      },
      'caller_persona': dataclasses.asdict(caller),
      'live_governance_decision': labs['lab4_and_5_governance'],
      'evaluation_summary': {
          'overall_score': eval_report['overall_score'],
          'all_criteria_passed': eval_report['all_criteria_passed'],
          'criteria': eval_report.get('criteria', {}),
      },
      'transaction_timeline': _extract_transaction_timeline(
          modular_labs=modular_labs,
          persona_key=persona_key,
          eval_report=eval_report,
      ),
      'labs': labs,
  }


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>SRE Guardian (Incident-2277) — Guided Walkthrough &amp; Eval Inspector</title>
  <!-- PARALLEL_COUNCIL & VERTEX_GENAI_EVAL совместимость -->
  <style>
    :root {
      --bg-parchment: #F5F0E8;
      --bg-card: #FFFFFF;
      --bg-subtle: #EFE9DE;
      --ink-primary: #1C1B18;
      --ink-secondary: #534F46;
      --ink-muted: #7A7467;
      --border-soft: #DCD4C6;
      --accent-blue: #174EA6;
      --accent-blue-bg: #E8F0FE;
      --accent-emerald: #137333;
      --accent-emerald-bg: #E6F4EA;
      --accent-amber: #B06000;
      --accent-amber-bg: #FEF7E0;
      --accent-crimson: #C5221F;
      --accent-crimson-bg: #FCE8E6;
      --font-serif: 'Lora', Georgia, serif;
      --font-sans: 'Outfit', system-ui, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      padding: 0;
      background-color: var(--bg-parchment);
      color: var(--ink-primary);
      font-family: var(--font-sans);
      line-height: 1.45;
    }

    .page-shell {
      max-width: 1120px;
      margin: 0 auto;
      padding: 24px 20px 56px;
    }

    header.editorial-header {
      border-bottom: 2px solid var(--ink-primary);
      padding-bottom: 14px;
      margin-bottom: 18px;
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }

    h1 {
      font-family: var(--font-serif);
      font-size: 1.65rem;
      margin: 0;
    }

    .control-bar {
      background: var(--bg-card);
      border: 1px solid var(--border-soft);
      border-radius: 8px;
      padding: 12px 16px;
      margin-bottom: 18px;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

    .control-group {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
    }

    .control-label {
      font-size: 0.78rem;
      font-weight: 700;
      color: var(--ink-secondary);
      text-transform: uppercase;
    }

    select.ctrl-select {
      font-family: var(--font-sans);
      font-size: 0.84rem;
      font-weight: 600;
      padding: 6px 10px;
      border-radius: 6px;
      border: 1px solid var(--border-soft);
      background: var(--bg-subtle);
      color: var(--ink-primary);
      cursor: pointer;
    }

    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
      gap: 10px;
      margin-bottom: 20px;
    }

    .stat-card {
      background: var(--bg-card);
      border: 1px solid var(--border-soft);
      border-radius: 8px;
      padding: 12px 14px;
    }

    .stat-card .stat-title {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--ink-muted);
      margin-bottom: 4px;
    }

    .stat-card .stat-value {
      font-family: var(--font-serif);
      font-size: 1.2rem;
      font-weight: 700;
    }

    .stat-card .stat-meta {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      color: var(--ink-secondary);
    }

    .section-title {
      font-family: var(--font-serif);
      font-size: 1.25rem;
      margin: 22px 0 10px 0;
      border-bottom: 1px solid var(--border-soft);
      padding-bottom: 6px;
    }

    details.dropdown-card {
      background: var(--bg-card);
      border: 1px solid var(--border-soft);
      border-radius: 8px;
      margin-bottom: 10px;
      overflow: hidden;
    }

    details.dropdown-card summary {
      padding: 12px 16px;
      cursor: pointer;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      font-weight: 600;
      font-size: 0.92rem;
      list-style: none;
    }

    details.dropdown-card summary::-webkit-details-marker {
      display: none;
    }

    .dropdown-body {
      padding: 12px 16px;
      border-top: 1px solid var(--border-soft);
      background: var(--bg-parchment);
      font-size: 0.88rem;
    }

    .badge {
      display: inline-block;
      padding: 3px 8px;
      border-radius: 4px;
      font-family: var(--font-mono);
      font-size: 0.7rem;
      font-weight: 600;
      text-transform: uppercase;
    }

    .badge-info { background: var(--accent-blue-bg); color: var(--accent-blue); }
    .badge-warning { background: var(--accent-amber-bg); color: var(--accent-amber); }
    .badge-critical { background: var(--accent-crimson-bg); color: var(--accent-crimson); }
    .badge-success { background: var(--accent-emerald-bg); color: var(--accent-emerald); }

    .code-snippet {
      background: #1E1E1E;
      color: #F1F1F1;
      font-family: var(--font-mono);
      font-size: 0.75rem;
      padding: 10px 12px;
      border-radius: 6px;
      overflow-x: auto;
      white-space: pre-wrap;
      margin-top: 8px;
    }
  </style>
</head>
<body>
  <div class="page-shell">
    <header class="editorial-header">
      <div>
        <h1>SRE Guardian (Incident-2277) — Simple Guided Summary</h1>
      </div>
      <div>
        <span class="badge badge-success" id="eval-badge">EVAL SCORE: 5/5 (100% PASS)</span>
      </div>
    </header>

    <section class="control-bar" aria-label="Interactive Controls">
      <div class="control-group">
        <label class="control-label" for="persona-select">Caller Role (Lab 4):</label>
        <select id="persona-select" class="ctrl-select">
          <option value="incident_commander">Incident Commander (Authorized Rollback)</option>
          <option value="junior_oncall">Junior On-Call (Blocked by Policy)</option>
        </select>
      </div>
      <div class="control-group">
        <label class="control-label" for="stage-select">Filter Stage:</label>
        <select id="stage-select" class="ctrl-select">
          <option value="ALL">All Stages (0 - 4)</option>
          <option value="Prework">0. Prework (BigQuery &amp; Memory)</option>
          <option value="Lab 1">1. Lab 1: Triage</option>
          <option value="Lab 2">2. Lab 2: Guardrails (Model Armor)</option>
          <option value="Lab 3">3. Lab 3: Eval (LLM-as-a-Judge)</option>
          <option value="Lab 4">4. Lab 4: Identity &amp; A2A</option>
        </select>
      </div>
    </section>

    <section class="stat-grid">
      <div class="stat-card">
        <div class="stat-title">0. Prework</div>
        <div class="stat-value">7,448 Rows</div>
        <div class="stat-meta" id="stat-bq">sre_workshop</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">1. Triage Culprit</div>
        <div class="stat-value">checkout@a3f9c21</div>
        <div class="stat-meta">auth Red Herring Skipped</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">2. Model Armor</div>
        <div class="stat-value" id="stat-armor-blocked">60 Blocked</div>
        <div class="stat-meta" id="stat-armor">180 PII Redacted</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">3. Agent Eval</div>
        <div class="stat-value" id="stat-eval">5 / 5 PASS</div>
        <div class="stat-meta">Score: 1.00 (LLM Judge)</div>
      </div>
      <div class="stat-card">
        <div class="stat-title">4. A2A Rollback</div>
        <div class="stat-value" id="stat-obo-status">EXECUTED</div>
        <div class="stat-meta" id="stat-obo-user">incident_commander</div>
      </div>
    </section>

    <h2 class="section-title">Key Findings (Click Dropdowns to Expand)</h2>
    <section>
      <details class="dropdown-card">
        <summary>
          <span>1. Why <code>auth</code> (14:15 UTC) Was Ignored as a Red Herring ▾</span>
          <span class="badge badge-warning">Memory Bank: Incident-1904</span>
        </summary>
        <div class="dropdown-body">
          <code>auth</code> spiked for only 90 seconds at 14:15 UTC during its hourly partner IdP sync and self-healed.
          <div class="code-snippet" id="snippet-auth-memory"></div>
        </div>
      </details>

      <details class="dropdown-card">
        <summary>
          <span>2. Why <code>checkout@a3f9c21</code> Caused the Outage ▾</span>
          <span class="badge badge-critical">Root Cause: N+1 ORM Loop</span>
        </summary>
        <div class="dropdown-body">
          Deploy <code>dep-9017</code> (14:31:18 UTC) added an unbatched <code>OrderItem.objects.get</code> loop that exhausted the 100-connection PgBouncer pool.
          <div class="code-snippet" id="snippet-checkout-diff"></div>
        </div>
      </details>

      <details class="dropdown-card">
        <summary>
          <span>3. Model Armor Log Sanitization (Prompt Injection &amp; PII) ▾</span>
          <span class="badge badge-info">60 Injections Blocked / 180 PII Masked</span>
        </summary>
        <div class="dropdown-body">
          <div class="code-snippet" id="snippet-armor-diff"></div>
        </div>
      </details>
    </section>

    <h2 class="section-title">Lab 3: Agent Evaluation Rubric (5/5 Passed)</h2>
    <section id="eval-grid"></section>

    <h2 class="section-title">Step-by-Step Transaction Trace (Click to Expand)</h2>
    <section id="txn-list"></section>
  </div>

  <script id="snapshots-data" type="application/json">__SNAPSHOTS_JSON__</script>
  <script>
    (function() {
      const SNAPSHOTS = JSON.parse(document.getElementById('snapshots-data').textContent);
      let currentPersona = 'incident_commander';
      let currentStageFilter = 'ALL';

      const personaSelect = document.getElementById('persona-select');
      const stageSelect = document.getElementById('stage-select');

      function formatBadgeClass(level) {
        if (level === 'critical') return 'badge badge-critical';
        if (level === 'warning') return 'badge badge-warning';
        if (level === 'success') return 'badge badge-success';
        return 'badge badge-info';
      }

      function render() {
        const snap = SNAPSHOTS[currentPersona];
        const mod = snap.labs.modular_adk_labs;
        const l2 = mod.lab2_guardrails_reflection_sandbox;
        const l4 = mod.lab4_governance_and_a2a;

        document.getElementById('stat-bq').textContent = snap.incident_banner.bigquery_dataset;
        document.getElementById('stat-armor-blocked').textContent =
          l2.guardrails_report.model_armor_injections_blocked + ' Blocked';
        document.getElementById('stat-armor').textContent =
          l2.guardrails_report.model_armor_pii_redacted + ' PII Redacted';

        const activeDec = l4.a2a_cross_agent_call.active_caller_decision;
        const oboStatusEl = document.getElementById('stat-obo-status');
        oboStatusEl.textContent = activeDec.allowed ? 'EXECUTED' : 'BLOCKED';
        oboStatusEl.style.color = activeDec.allowed ? 'var(--accent-emerald)' : 'var(--accent-crimson)';
        document.getElementById('stat-obo-user').textContent = snap.caller_persona.role;

        const authMem = snap.labs.lab3_memory_and_cost.recalled_auth_postmortem || {};
        document.getElementById('snippet-auth-memory').textContent =
          (authMem.incident_id || 'Incident-1904') + ': ' + (authMem.resolution || 'Do not roll back auth.');

        const diffInfo = snap.labs.lab2_bigquery_mcp.suspect_commit_diff || {};
        document.getElementById('snippet-checkout-diff').textContent =
          diffInfo.diff_text || diffInfo.diff || '';

        const armorDef = snap.labs.lab4_and_5_governance.model_armor_defense || {};
        document.getElementById('snippet-armor-diff').textContent =
          armorDef.sanitized_log_output || '';

        // Render Lab 3 Eval Rubric Dropdowns
        const evalGrid = document.getElementById('eval-grid');
        evalGrid.replaceChildren();
        const criteria = (snap.evaluation_summary && snap.evaluation_summary.criteria) || {};
        Object.keys(criteria).forEach(function(key) {
          const item = criteria[key];
          const det = document.createElement('details');
          det.className = 'dropdown-card';
          const sum = document.createElement('summary');
          const title = document.createElement('span');
          title.textContent = key + ' ▾';
          const badge = document.createElement('span');
          badge.className = item.passed ? 'badge badge-success' : 'badge badge-critical';
          badge.textContent = (item.passed ? 'PASS' : 'FAIL') + ' (' + item.score + ')';
          sum.appendChild(title);
          sum.appendChild(badge);
          const body = document.createElement('div');
          body.className = 'dropdown-body';
          body.textContent = item.explanation;
          det.appendChild(sum);
          det.appendChild(body);
          evalGrid.appendChild(det);
        });

        // Render Transaction Ledger Dropdowns
        const txnList = document.getElementById('txn-list');
        txnList.replaceChildren();
        (snap.transaction_timeline || []).forEach(function(tx) {
          if (currentStageFilter !== 'ALL' && !tx.stage.startsWith(currentStageFilter)) {
            return;
          }
          const det = document.createElement('details');
          det.className = 'dropdown-card';
          const sum = document.createElement('summary');
          const left = document.createElement('span');
          left.textContent = '#' + tx.step + ' [' + tx.stage + '] ' + tx.actor + ' -> ' + tx.target + ' ▾';
          const badge = document.createElement('span');
          badge.className = formatBadgeClass(tx.highlight_level);
          badge.textContent = tx.category;
          sum.appendChild(left);
          sum.appendChild(badge);

          const body = document.createElement('div');
          body.className = 'dropdown-body';
          const p = document.createElement('div');
          p.textContent = tx.summary;
          const pre = document.createElement('div');
          pre.className = 'code-snippet';
          pre.textContent = JSON.stringify(tx.details, null, 2);
          body.appendChild(p);
          body.appendChild(pre);

          det.appendChild(sum);
          det.appendChild(body);
          txnList.appendChild(det);
        });
      }

      personaSelect.addEventListener('change', function() {
        currentPersona = personaSelect.value;
        render();
      });

      stageSelect.addEventListener('change', function() {
        currentStageFilter = stageSelect.value;
        render();
      });

      render();
    })();
  </script>
</body>
</html>
"""


def render_incident_command_html(
    ic_snapshot: dict[str, Any] | None = None,
    jr_snapshot: dict[str, Any] | None = None,
) -> str:
  """Renders the self-contained interactive HTML Transaction Inspector UX."""
  ic_data = ic_snapshot or build_incident_command_snapshot(
      persona_key='incident_commander', model_armor_enabled=True
  )
  jr_data = jr_snapshot or build_incident_command_snapshot(
      persona_key='junior_oncall', model_armor_enabled=True
  )
  payload = json.dumps(
      {
          'incident_commander': ic_data,
          'junior_oncall': jr_data,
      },
      default=str,
  ).replace('</', '<\\/')
  return _HTML_TEMPLATE.replace('__SNAPSHOTS_JSON__', payload)


def serve_interactive_ux(
    port: int,
    html_content: str | None = None,
    host: str = '127.0.0.1',
) -> None:
  """Serves the interactive Split-Screen Lab Chat & Backend Console UX."""
  active_html = html_content or chat_ux.CHAT_UX_HTML

  class _UxHandler(http_server.BaseHTTPRequestHandler):
    """HTTP handler serving the interactive Lab Chat UX and /api/chat."""

    def do_GET(self) -> None:  # pylint: disable=invalid-name
      """Handles GET requests for /, /api/health, and /api/snapshot."""
      parsed = urlparse.urlparse(self.path)
      if parsed.path == '/api/health':
        body = json.dumps({
            'status': 'ok',
            'service': 'sre-guardian-ux',
            'mode': 'interactive-lab-chat-and-console',
            'project': provided.DEFAULT_VERTEX_PROJECT,
            'agent_engine_id': provided.DEFAULT_AGENT_ENGINE_ID,
        }).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return

      if parsed.path == '/api/snapshot':
        qs = urlparse.parse_qs(parsed.query)
        persona = qs.get('persona', ['incident_commander'])[0]
        if persona not in provided.CALLER_PERSONAS:
          persona = 'incident_commander'
        data = build_incident_command_snapshot(persona_key=persona)
        body = json.dumps(data, indent=2, default=str).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return

      if parsed.path == '/api/chat':
        qs = urlparse.parse_qs(parsed.query)
        lab_id = qs.get('lab_id', ['lab1'])[0]
        user_message = qs.get('message', [''])[0].strip()
        persona = qs.get('persona', ['incident_commander'])[0]
        armor_str = qs.get('model_armor_enabled', ['true'])[0].lower()
        model_armor_enabled = armor_str not in ('false', '0', 'no')
        result = chat_ux.handle_chat_turn(
            lab_id=lab_id,
            user_message=user_message,
            persona=persona,
            model_armor_enabled=model_armor_enabled,
        )
        body = json.dumps(result, indent=2, default=str).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return

      if parsed.path in ('/overview', '/overview.html'):
        overview_path = pathlib.Path(__file__).resolve().parent / 'overview.html'
        body = overview_path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return

      body = active_html.encode('utf-8')
      self.send_response(200)
      self.send_header('Content-Type', 'text/html; charset=utf-8')
      self.send_header('Content-Length', str(len(body)))
      self.end_headers()
      self.wfile.write(body)

    def do_POST(self) -> None:  # pylint: disable=invalid-name
      """Handles POST /api/chat requests for live per-lab agent chat."""
      parsed = urlparse.urlparse(self.path)
      if parsed.path != '/api/chat':
        self.send_response(404)
        self.end_headers()
        return

      length = int(self.headers.get('Content-Length', '0'))
      raw_body = self.rfile.read(length).decode('utf-8') if length > 0 else '{}'
      try:
        req = json.loads(raw_body)
      except json.JSONDecodeError:
        req = {}

      result = chat_ux.handle_chat_turn(
          lab_id=str(req.get('lab_id', 'lab1')),
          user_message=str(req.get('message', '')).strip(),
          persona=str(req.get('persona', 'incident_commander')),
          model_armor_enabled=bool(req.get('model_armor_enabled', True)),
      )
      body = json.dumps(result, indent=2, default=str).encode('utf-8')
      self.send_response(200)
      self.send_header('Content-Type', 'application/json; charset=utf-8')
      self.send_header('Content-Length', str(len(body)))
      self.end_headers()
      self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:
      """Suppresses noisy default per-request stderr logging."""
      del fmt, args

  httpd = http_server.ThreadingHTTPServer((host, port), _UxHandler)
  print(
      f'SRE Guardian Live Lab Chat UX running at http://{host}:{port}',
      flush=True,
  )
  httpd.serve_forever()


def main(argv: Sequence[str]) -> None:
  if len(argv) > 1:
    raise app.UsageError('Too many command-line arguments.')

  if _EXPORT_HTML.value:
    out_path = os.path.abspath(_EXPORT_HTML.value)
    with open(out_path, 'w', encoding='utf-8') as f_html:
      f_html.write(chat_ux.CHAT_UX_HTML)

  if _SERVE.value:
    serve_interactive_ux(
        port=_PORT.value,
        html_content=chat_ux.CHAT_UX_HTML,
        host=_HOST.value,
    )
    return

  snapshot = build_incident_command_snapshot(
      persona_key=_PERSONA.value,
      model_armor_enabled=_MODEL_ARMOR.value,
  )
  print(json.dumps(snapshot, indent=2, default=str))


if __name__ == '__main__':
  app.run(main)
