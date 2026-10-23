# SRE Guardian (`Incident-2277`) — Architecture Overview

Concise system flow and resource mapping for the 5-step workshop.
([← Back to Workshop README](README.md))

---

## 1. 5-Step Workshop Flow

```mermaid
flowchart LR
    Pre["0. Prework\nBigQuery (4 tables)\n+ Memory Bank"] --> L1["1. Lab 1: Triage\nsre_triage_coordinator\n+ 3 Specialist Sub-Agents"]
    L1 --> L2["2. Lab 2: Guardrails\nGoogle Cloud Model Armor\n(Input & Output Sanitization)"]
    L2 --> L3["3. Lab 3: Eval\n5-Pillar Gen AI Eval\n& LLM-as-a-Judge (5/5 PASS)"]
    L3 --> L4["4. Lab 4: Identity & A2A\nAGENT_IDENTITY + A2A Rollback\n-> Save Postmortem"]
```

<details>
<summary><b>🔄 Expand Full Sequence Diagram (Steps 0–4)</b></summary>

```mermaid
sequenceDiagram
    autonumber
    actor SRE as On-Call SRE
    participant BQ as Cloud BigQuery (sre_workshop)
    participant Mem as Vertex AI Agent Engine (Memory Bank)
    participant L1 as Lab 1: Triage Agent
    participant L2 as Lab 2: Model Armor Guardrails
    participant L3 as Lab 3: Agent Eval (LLM Judge)
    participant L4 as Lab 4: Identity & A2A Rollback

    SRE->>BQ: 0. Prework: Seed 4 tables (7,448 rows)
    SRE->>Mem: 0. Prework: Seed Incident-1904 (auth) & Incident-2051 (checkout)
    SRE->>L1: 1. Triage Incident-2277
    L1->>Mem: Recall Incident-1904 -> Skip auth red herring
    L1->>BQ: Pinpoint checkout@a3f9c21 (dep-9017 N+1 loop)
    L1->>L2: 2. Enforce Model Armor & ADK Guardrails
    L2->>BQ: Block 60 log prompt injections & mask 180 PII emails/tokens via Model Armor
    L2->>L3: 3. Run 5-Pillar Agent Evaluation (evaluate_sre_agent.py)
    L3-->>L4: 5/5 Rubrics PASS (Score = 1.00)
    L4->>Mem: 4. Verify AGENT_IDENTITY, roll back checkout@a3f9c21 via A2A & save postmortem
```
</details>

<details>
<summary><b>☁️ Expand Google Cloud & Vertex AI Resource Mapping</b></summary>

| Component | GCP / Vertex AI Resource | Code Reference |
| :--- | :--- | :--- |
| **Data Warehouse** | Cloud BigQuery (`$GOOGLE_CLOUD_PROJECT.sre_workshop`) | [`provided.py`](provided.py) (`BigQueryMcpClient`, `BigQueryToolset`) |
| **Agent Runtime & Identity** | Vertex AI Agent Engine (`identityType: AGENT_IDENTITY`) | [`provided.py`](provided.py) (`ensure_vertex_agent_engine`) |
| **Long-Term Memory** | Vertex AI Memory Bank (`VertexAiMemoryBankService`) | [`prework/seed_bigquery_and_memory.py`](prework/seed_bigquery_and_memory.py) |
| **Prompt & PII Guardrails** | Google Cloud Model Armor (`sre-guardian-armor-policy`) | [`lab2_guardrails_reflection_sandbox/agent.py`](lab2_guardrails_reflection_sandbox/agent.py), [`chat_ux.py`](chat_ux.py) & [`provided.py`](provided.py) |
| **Agent Evaluation (`Eval`)** | Vertex AI Gen AI Eval & LLM-as-a-Judge (`5/5` Rubrics) | [`evals/evaluate_sre_agent.py`](evals/evaluate_sre_agent.py) |
| **A2A & Governance** | `ReasoningEngine.spec.agentCard` & `AgentGatewayEnforcer` | [`lab4_governance_and_a2a/agent.py`](lab4_governance_and_a2a/agent.py) |
</details>
