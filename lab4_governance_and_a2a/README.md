# Lab 4: Agent Identity, Skill Registry, Model Armor, A2A Card & Cross-Agent Execution

## Lab 4 Architecture

```mermaid
flowchart TB
    classDef pro fill:#E6F4EA,stroke:#1E8E3E,stroke-width:2px,color:#0D652D
    classDef flash fill:#FEF7E0,stroke:#F9AB00,stroke-width:2px,color:#B06000
    classDef security fill:#F3E8FD,stroke:#9334E6,stroke-width:2px,color:#4A148C
    classDef vertex fill:#FCE8E6,stroke:#D93025,stroke-width:2px,color:#A50E0E

    subgraph IdentityLayer["Identity & Registry Layer"]
        AgentID["Vertex AI First-Class Agent Identity\n(identityType: AGENT_IDENTITY)\nprincipal://agents.global.org-..."]:::vertex
        Caller["CallerIdentity Authorization\n- incident_commander (Authorized)\n- junior_oncall (Blocked)"]:::security
        Registries["AgentGatewayEnforcer (6 Agents, 6 Tools)\n+ EnterpriseSkillRegistry (SkillToolset:\ngoverned-rollback-playbook v1.4.0)"]:::vertex
    end

    Coord["sre_governance_coordinator\n(ADK LlmAgent — Gemini 2.5 Pro)\n1. audit_agent_and_skill_registries_tool\n2. verify_model_armor_and_block_auth_rollback_tool\n3. call_change_mgmt_a2a_agent"]:::pro

    subgraph Gateway["Governance & Security Enforcement Gate"]
        SGP2["Policy SGP-002 + Model Armor\nBlocks auth Red-Herring Rollback"]:::security
        SGP1["Policy SGP-001 + Caller Check\nRequires 3/3 Council Vote & IC Role"]:::security
        SCC["Security Command Center (SCC) Findings\n- HIGH: Blocked auth rollback attempt\n- MEDIUM: Unauthorized junior_oncall attempt"]:::security
    end

    subgraph A2ATarget["Remote Release Engineering A2A Agent"]
        A2A["change_mgmt_a2a_agent\n(A2A AgentCard — Gemini 2.5 Flash)\nexecute_governed_a2a_rollback_tool\nRolls back checkout dep-9017 (a3f9c21)"]:::flash
        MemBank["Vertex AI Agent Engine Memory Bank\n(VertexAiMemoryBankService)\nPersists Incident-2277 Postmortem (mem-postmortem-3)"]:::vertex
    end

    AgentID & Caller & Registries --> Coord
    Coord -->|"Attempt auth Rollback"| SGP2
    SGP2 -.->|"Emit HIGH Threat Alert"| SCC
    Coord -->|"Invoke A2A Rollback (checkout@a3f9c21)"| SGP1
    SGP1 -.->|"If junior_oncall -> Emit MEDIUM Alert"| SCC
    SGP1 -->|"If incident_commander + 3/3 Council"| A2A
    A2A ==>|"Persist Resolved Postmortem"| MemBank
```

## Objective

Govern the SRE Guardian fleet on **Vertex AI Agent Engine** and execute the
production rollback call **from one ADK agent (`sre_governance_coordinator`) to
another remote A2A agent (`change_mgmt_a2a_agent`)**:

1.  **Vertex AI First-Class Agent Identity (`identityType: AGENT_IDENTITY`) &
    Fleet Inventory (`AgentGatewayEnforcer.register_fleet`)**: Verifies the
    provisioned `principal://agents.global.org-...` identity on Vertex AI Agent
    Engine and inventories all 6 workshop agents (`sre_triage_coordinator`,
    `metrics_and_catalog_agent`, `logs_and_memory_agent`,
    `sre_council_of_sub_agents`, `sre_governance_coordinator`,
    `change_mgmt_a2a_agent`) and 6 authorized MCP/A2A tool endpoints.
2.  **Skill Registry
    (`EnterpriseSkillRegistry(google.adk.skills.SkillRegistry)`)**: Registers,
    validates, and version-pins `incident-triage-runbook` (`v2.1.0`) and
    `governed-rollback-playbook` (`v1.4.0`), exposing them to
    `sre_governance_coordinator` via ADK's `SkillToolset`.
3.  **Caller Identity & Policy Enforcement (`CallerIdentity`)**: Evaluates
    caller authorization before high-blast-radius mutations:
    -   `junior_oncall` (`roles/sre.juniorOncall`) is **blocked**
        (`BLOCKED_BY_OBO_IDENTITY`).
    -   `incident_commander` (`roles/sre.incidentCommander`) is **authorized**
        (`EXECUTED_VIA_A2A_CHANGE_MGMT_AGENT`).
4.  **Google Cloud Model Armor (`ModelArmorInspector` / `sre-guardian-armor-policy`)
    & Semantic Governance Policies**: Blocks indirect prompt injections
    attempting to roll back `auth` (`SGP-002-PROTECT-AUTH-RED-HERRING`) and
    redacts synthetic SDP PII tokens/emails.
5.  **Security Audit & Threat Detection (`scc_threat_findings`)**:
    Emits structured `HIGH` and `MEDIUM` severity security findings whenever a
    blocked `auth` rollback attempt or unauthorized rollback attempt is
    intercepted.
6.  **Execute Call from Another Agent & Persist to Vertex AI Memory Bank
    (`sre_governance_coordinator -> change_mgmt_a2a_agent`)**:
    `sre_governance_coordinator` invokes `call_change_mgmt_a2a_agent`
    (`SubAgentDispatchTool`) to execute the rollback in `change_mgmt_a2a_agent`
    and persist the resolved `Incident-2277` postmortem into **Vertex AI Agent
    Engine Memory Bank (`VertexAiMemoryBankService`)**.

## Run Lab 4

```bash
# Run as Incident Commander (authorized rollback via A2A):
python3 lab4_governance_and_a2a/agent_complete.py \
  --project_id="${GOOGLE_CLOUD_PROJECT}" \
  --location=us-central1 \
  --persona=incident_commander

# Run as Junior On-Call (blocked at the Agent Gateway):
python3 lab4_governance_and_a2a/agent_complete.py \
  --project_id="${GOOGLE_CLOUD_PROJECT}" \
  --location=us-central1 \
  --persona=junior_oncall
```
