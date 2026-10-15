# Lab 1: Immediate Incident Triage Agent (Cloud BigQuery, Multi-Agent, Skills, MCP & Vertex AI Memory Bank)

## Lab 1 Architecture

```mermaid
flowchart TB
    classDef pro fill:#E6F4EA,stroke:#1E8E3E,stroke-width:2px,color:#0D652D
    classDef flash fill:#FEF7E0,stroke:#F9AB00,stroke-width:2px,color:#B06000
    classDef gcp fill:#E8F0FE,stroke:#1A73E8,stroke-width:2px,color:#0D47A1
    classDef vertex fill:#FCE8E6,stroke:#D93025,stroke-width:2px,color:#A50E0E

    SRE["On-Call SRE Query\n'Why are checkout and auth alerting in Incident-2277?'"]

    subgraph Coordinator["Root Orchestrator (ADK LlmAgent)"]
        Coord["sre_triage_coordinator\n(Vertex AI Gemini 2.5 Pro)"]:::pro
        Skills["ADK SkillToolset (L1 -> L2)\nload_skill('incident-triage-runbook')"]:::vertex
        Coord <-->|"Progressive Disclosure"| Skills
    end

    subgraph SubAgents["Specialist Sub-Agents (SubAgentDispatchTool -> Gemini 2.5 Flash)"]
        direction LR
        A_Metrics["metrics_and_catalog_agent\n- query_metrics_Summary_tool\n- lookup_knowledge_catalog_tool\n- ADK BigQueryToolset (WriteMode.BLOCKED)"]:::flash
        A_Logs["logs_and_memory_agent\n- recall_similar_incidents_tool\n- query_app_logs_tool\n- ADK BigQueryToolset"]:::flash
        A_Deploys["deploy_and_diff_agent\n- list_recent_deployments_tool\n- fetch_commit_diff_tool\n- ADK BigQueryToolset"]:::flash
    end

    subgraph Backends["Google Cloud Data & Memory Plane"]
        direction LR
        BQ_Metrics["BigQuery: service_metrics\n+ Knowledge Catalog (Tier-0 SLO: 250ms)\n(checkout: 28m breach vs auth: 2m blip)"]:::gcp
        MemBank["Vertex AI Memory Bank\n(VertexAiMemoryBankService)\nRecalls Incident-1904 & Incident-2051"]:::vertex
        BQ_Logs["BigQuery: app_logs\n(PgBouncer PoolTimeout 100/100)"]:::gcp
        BQ_Deploys["BigQuery: deployments & commit_diffs\n(dep-9017 at 14:31:18Z -> sha a3f9c21 N+1 loop)"]:::gcp
    end

    SRE --> Coord
    Coord -->|"1. call_metrics_and_catalog_agent"| A_Metrics
    Coord -->|"2. call_logs_and_memory_agent"| A_Logs
    Coord -->|"3. call_deploy_and_diff_agent"| A_Deploys

    A_Metrics --> BQ_Metrics
    A_Logs --> MemBank & BQ_Logs
    A_Deploys --> BQ_Deploys
```

## Objective

Build a functional **Vertex AI & ADK Multi-Agent Triage System** that answers
real-time incident triage questions for **`Incident-2277`** by combining:

1.  **Bring Your Own Data (Google Cloud BigQuery + Knowledge Catalog)**: Queries
    `$GOOGLE_CLOUD_PROJECT.sre_workshop.service_metrics`, `app_logs`,
    `deployments`, and `commit_diffs` via parameterized `google.cloud.bigquery`
    SQL and ADK's native `BigQueryToolset` (`WriteMode.BLOCKED`), enriched with
    Tier-0 SLO metadata (`KNOWLEDGE_CATALOG_CONTEXT`).
2.  **Multiple Agents (`LlmAgent` hierarchy on Vertex AI Gemini)**:
    -   `sre_triage_coordinator` (`gemini-2.5-pro`): Root orchestrator that
        loads the triage runbook skill and delegates to 3 domain specialists.
    -   `metrics_and_catalog_agent` (`gemini-2.5-flash`): Compares SLO breaches
        across `checkout`, `auth`, `cart`, and `inventory`.
    -   `logs_and_memory_agent` (`gemini-2.5-flash`): Cross-checks Vertex AI
        Agent Engine Long-Term Memory (`Incident-1904` & `Incident-2051`) before
        inspecting `app_logs`.
    -   `deploy_and_diff_agent` (`gemini-2.5-flash`): Correlates recent
        deployments (`dep-9017`) and inspects git commit diffs (`a3f9c21`).
3.  **Skills (`SkillToolset`)**: Dynamically loads
    `skills/incident-triage-runbook/SKILL.md` via ADK's native `SkillToolset`
    (`list_skills`, `load_skill`).
4.  **MCP & BigQuery Toolset (`BigQueryMcpClient`)**: Executes parameterized,
    allow-listed queries against Cloud BigQuery tables.
5.  **Vertex AI Agent Engine Long-Term Memory (`VertexAiMemoryBankService` &
    `VertexAiSessionService`)**: Recalls from Vertex AI Agent Engine Memory Bank
    that the `14:15 UTC` `auth` spike matches `Incident-1904` (benign hourly
    `:15` partner IdP sync), preventing a catastrophic wrong-service rollback.

## Run Lab 1

```bash
# Run with default Incident-2277 triage query:
python3 lab1_triage_agent/agent_complete.py \
  --project_id="${GOOGLE_CLOUD_PROJECT}" \
  --location=us-central1

# Ask a custom natural-language triage question:
python3 lab1_triage_agent/agent_complete.py \
  --project_id="${GOOGLE_CLOUD_PROJECT}" \
  --location=us-central1 \
  --query="Why did auth spike at 14:15 UTC, and is checkout commit a3f9c21 the real culprit?"
```
