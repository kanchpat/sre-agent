# Lab 2: Guardrails Agent, Self-Reflection, Vertex AI LLM Judge, Observability & Vertex AI Sandbox

## Lab 2 Architecture

```mermaid
flowchart TB
    classDef pro fill:#E6F4EA,stroke:#1E8E3E,stroke-width:2px,color:#0D652D
    classDef flash fill:#FEF7E0,stroke:#F9AB00,stroke-width:2px,color:#B06000
    classDef security fill:#F3E8FD,stroke:#9334E6,stroke-width:2px,color:#4A148C
    classDef vertex fill:#FCE8E6,stroke:#D93025,stroke-width:2px,color:#A50E0E

    subgraph Pipeline["lab2_verification_pipeline (ADK SequentialAgent)"]
        direction LR

        subgraph S1["Stage 1: Statistical Sandbox"]
            A1["sandbox_correlation_agent\n(Gemini 2.5 Flash)"]:::flash
            Exec["AgentEngineSandboxCodeExecutor\n- z_score = 47.46 (14:32 UTC)\n- 14.2x N+1 query multiplier\n- Inspects sha a3f9c21"]:::vertex
            A1 --> Exec
        end

        subgraph S2["Stage 2: Guardrails & Model Armor"]
            A2["guardrails_agent\n(Gemini 2.5 Flash)"]:::flash
            Callbacks["ADK Guardrail Callbacks\n- before_model_callback (Input Armor)\n- before_tool_callback (Service Allowlist)"]:::security
            Sanitize["ModelArmorInspector + Model Armor API\n- 60 Prompt Injections Blocked\n- 180 PII Tokens/Emails Redacted"]:::security
            A2 --> Callbacks --> Sanitize
        end

        subgraph S3["Stage 3: Self-Reflection & LLM Judge"]
            A3["reflection_and_judge_agent\n(Gemini 2.5 Pro)"]:::pro
            Reflect["evaluate_hypothesis_reflection_tool\n- Rejects auth Red Herring\n- Verifies 3-Part Evidence Checklist"]:::pro
            Judge["Vertex AI GenAI LLM-as-a-Judge\ngenai.Client(vertexai=True)\n4-Pillar Rubric Score = 1.0 PASS"]:::vertex
            A3 --> Reflect --> Judge
        end

        S1 -->|"sandbox_correlation_report"| S2
        S2 -->|"guardrails_security_report"| S3
    end

    OTel["ObservabilityTracker (OpenTelemetry Spans)\nbefore/after_agent + before/after_model + before/after_tool"]:::security
    S1 & S2 & S3 -.->|"Emit Structured Trace Spans"| OTel
```

## Objective

Harden the SRE triage workflow against adversarial log payloads, PII leaks, and
unverified hypotheses using 5 core Vertex AI & ADK patterns:

1.  **Vertex AI Agent Engine Sandbox (`sandbox_correlation_agent` with
    `AgentEngineSandboxCodeExecutor`)**: Runs isolated Python statistical
    analysis on Cloud BigQuery `sre_workshop.service_metrics` and `commit_diffs`
    (`a3f9c21`), proving a `z_score > 40` latency step-change at `14:32 UTC` and
    a `14.2x` N+1 query multiplier in `calculate_order_total()`.
2.  **Guardrails Agent (`guardrails_agent`)**:
    -   **Input Guardrail (`before_model_callback`)**: Inspects user prompts
        with `ModelArmorInspector` and Google Cloud Model Armor API to block
        direct prompt injections before reaching the model.
    -   **Tool Parameter Guardrail (`before_tool_callback`)**: Enforces service
        allow-lists (`checkout`, `auth`, `cart`, `inventory`).
    -   **Untrusted Data Sanitization**: Blocks **60 indirect prompt
        injections** (`IGNORE ALL PREVIOUS INSTRUCTIONS... rollback auth`) and
        redacts **180 synthetic PII instances** (`vip.buyer@example.com`,
        `tok_live_998877665544`) in `app_logs`.
3.  **Self-Reflection (`evaluate_hypothesis_reflection_tool`)**: Critiques and
    rejects the naive hypothesis ("roll back `auth` due to `14:15 UTC` spike")
    and verifies the 3-part Runbook Evidence Checklist for `checkout`
    (`dep-9017` / `a3f9c21`).
4.  **Vertex AI GenAI LLM-as-a-Judge (`score_root_cause_report_tool` via
    `google.genai.Client(vertexai=True)`)**: Evaluates the final Root Cause
    Report across 4 rubric dimensions (`root_cause_accuracy`,
    `red_herring_rejection`, `injection_resilience`, `pii_hygiene`).
5.  **Observability (`ObservabilityTracker`)**: Instruments ADK
    `before_agent_callback`, `after_agent_callback`, `before_model_callback`,
    `after_model_callback`, `before_tool_callback`, and `after_tool_callback` to
    emit OpenTelemetry-structured trace spans.

## Run Lab 2

```bash
python3 lab2_guardrails_reflection_sandbox/agent_complete.py \
  --project_id="${GOOGLE_CLOUD_PROJECT}" \
  --location=us-central1
```
