# Lab 3: Council Agent (Parallel Deliberation & Consensus Arbiter on Vertex AI)

## Lab 3 Architecture

```mermaid
flowchart TB
    classDef pro fill:#E6F4EA,stroke:#1E8E3E,stroke-width:2px,color:#0D652D
    classDef flash fill:#FEF7E0,stroke:#F9AB00,stroke-width:2px,color:#B06000
    classDef gcp fill:#E8F0FE,stroke:#1A73E8,stroke-width:2px,color:#0D47A1
    classDef vertex fill:#FCE8E6,stroke:#D93025,stroke-width:2px,color:#A50E0E

    Input["Candidate Action: Roll back checkout@a3f9c21 (dep-9017)\nvs. Counterfactual: Roll back auth"]

    subgraph CouncilPipeline["sre_council_of_sub_agents (ADK SequentialAgent)"]
        subgraph ParallelFanOut["Stage 1: parallel_council_deliberation (ADK ParallelAgent)"]
            direction LR
            C1["reliability_councilor\n(Gemini 2.5 Flash)\naudit_reliability_evidence_tool\n- 28m checkout breach vs 2m auth blip\n- 42s deploy-to-breach delta\nVote: APPROVE checkout@a3f9c21"]:::flash
            C2["database_performance_councilor\n(Gemini 2.5 Flash)\naudit_db_performance_evidence_tool\n- Incident-2051 (100-conn PgBouncer)\n- OrderItem.objects.get N+1 loop\nVote: APPROVE checkout@a3f9c21"]:::flash
            C3["red_team_devils_advocate_councilor\n(Gemini 2.5 Flash)\naudit_red_team_counterfactuals_tool\n- Rules out auth/cart/inventory\n- Flags auth rollback as injection trap\nVote: APPROVE checkout@a3f9c21"]:::flash
        end

        Arbiter["Stage 2: council_consensus_arbiter (Gemini 2.5 Pro)\ntally_council_consensus_tool\n- Tallies session state: reliability_vote + db_performance_vote + red_team_vote\n- Verdict: 3/3 Unanimous Approval (checkout@a3f9c21) | do_not_rollback: auth"]:::pro

        C1 & C2 & C3 -->|"ADK Session State (output_key)"| Arbiter
    end

    BQ["Cloud BigQuery\n(service_metrics, deployments, commit_diffs)"]:::gcp
    Mem["Vertex AI Memory Bank\n(Incident-1904 & Incident-2051)"]:::vertex

    Input --> ParallelFanOut
    BQ --> C1 & C2 & C3
    Mem --> C2 & C3
```

## Objective

Eliminate **Single-Agent Myopia** before executing a high-blast-radius
production rollback by orchestrating an ADK **`ParallelAgent`**
(`parallel_council_deliberation`) followed by a **`SequentialAgent`** Consensus
Arbiter (`council_consensus_arbiter`) backed by **Cloud BigQuery
(`$GOOGLE_CLOUD_PROJECT.sre_workshop`)** and **Vertex AI Agent Engine Memory Bank
(`VertexAiMemoryBankService`)**:

1.  **`reliability_councilor` (`LlmAgent`)**: Evaluates golden signals (`p99`
    latency, HTTP 500 rate, SLO breach duration) and deployment timestamp
    alignment (`dep-9017` at `14:31:18Z` -> sustained breach at `14:32:00Z`).
2.  **`database_performance_councilor` (`LlmAgent`)**: Audits the `checkout`
    PgBouncer 100-connection pool architecture (`Incident-2051`) from Vertex AI
    Agent Engine Memory Bank and verifies the N+1
    `OrderItem.objects.get(id=item_id)` loop in commit `a3f9c21`.
3.  **`red_team_devils_advocate_councilor` (`LlmAgent`)**: Actively challenges
    the primary hypothesis by testing counterfactual deployments
    (`auth@c91d440`, `cart@f08a112`, `inventory@7b2e804`) and proving that
    rolling back `auth` was an adversarial prompt-injection trap.
4.  **`council_consensus_arbiter` (`LlmAgent`)**: Aggregates all 3 independent
    councilor votes from ADK session state (`3/3` unanimous approval for
    `checkout@a3f9c21`, `do_not_rollback_service="auth"`).

## Run Lab 3

```bash
python3 lab3_council_agent/agent_complete.py \
  --project_id="${GOOGLE_CLOUD_PROJECT}" \
  --location=us-central1
```
