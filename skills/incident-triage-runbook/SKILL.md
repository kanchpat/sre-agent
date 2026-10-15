---
name: incident-triage-runbook
description: >-
  Standard 5-step SRE incident triage methodology for diagnosing production
  latency spikes and HTTP 500 outages across BigQuery telemetry, deployment
  histories, and code diffs. Load this skill whenever triaging an active
  incident or before recommending a deployment rollback.
---

# SRE Guardian: Production Incident Triage Runbook (L2 Instructions)

Follow these 5 steps in strict order. Never recommend a production rollback
until all three required evidence artifacts are verified.

## Step 1: Consult Long-Term Memory Bank First (`Q#9`)

-   Query **Agent Platform Memory Bank** for prior postmortems matching the
    alerting services (`checkout`, `auth`, `cart`, `inventory`).
-   Known recurring transient spikes (such as `auth` `idp.internal` partner sync
    timeouts at `:15` past the hour that self-heal within 90 seconds) must be
    filtered out as **Red Herrings**.

## Step 2: Pinpoint the Exact Anomaly Onset in `service_metrics` (`Q#5`)

-   Query `sre_workshop.service_metrics` via the **BigQuery MCP Server**.
-   Identify which service experienced a sustained step-function increase in
    `p99_latency_ms`, `error_rate`, and `db_pool_utilization`, and record the
    **exact minute of onset (`YYYY-MM-DDTHH:MM:00Z`)**.

## Step 3: Correlate with `deployments` & `app_logs` in Agent Sandbox (`Q#10`)

-   Query `sre_workshop.deployments` for any deployment that occurred within **5
    minutes prior** to the anomaly onset timestamp.
-   Use the **Code Execution Agent (Agent Sandbox)** to correlate log error
    signatures in `sre_workshop.app_logs` (e.g., `PoolTimeout`, per-request SQL
    query counts) before vs. after the suspect deployment timestamp.

## Step 4: Inspect Code Diffs & Verify the 3-Part Evidence Rubric (`Q#11, Q#12`)

-   Fetch the unified diff from `sre_workshop.commit_diffs` for the suspect
    commit SHA.
-   Before proposing any remediation, the **Self Reflection Agent**,
    **LLM-as-a-Judge**, and **Council Agent** require all 3 proofs:
    1.  **Metric & Log Onset Timestamp**: Exact UTC minute and error signature.
    2.  **Correlating Deployment SHA**: Commit SHA, author, and deploy
        timestamp.
    3.  **Code-Level Root Cause**: Exact file, function, and defective code
        pattern (e.g., N+1 SQL query loop replacing batched
        `filter(order_id=...)`).

## Step 5: Governed Rollback Execution (`Q#14–Q#19`)

-   Never execute a rollback directly if the caller identity lacks
    `incident-commander` authority (**Delegated Authority / OBO**).
-   Route the rollback request through **Agent Gateway** to the Release
    Engineering team's **Change Mgmt Agent (`A2A`)** only after **Model Armor**
    and **Semantic Governance Policies** pass.
