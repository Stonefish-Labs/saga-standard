# 7. Autonomy Tiers

This standard defines four autonomy tiers that represent progressively greater levels of trust delegated to the agent and its tools. Selecting the appropriate tier is a risk management decision that balances operational efficiency against security posture.

Autonomy tiers are selected **per-profile**. A profile's tier determines the approval policy, session caching behavior, and compensating control requirements that **MUST** be applied to that profile. A deployment **MAY** operate different profiles at different tiers (see §7.5, Mixed-Tier Deployments).

The approval modes referenced in each tier (`auto`, `prompt_once`, `prompt_always`) are defined in [§4.4 Approval Policy](../01-foundations/04-core-concepts.md#44-approval-terms) and governed by the normative requirements in [§10 Approval Policies](../03-architecture/10-approval-policies.md). The write modes (`same`, `auto`, `deny`, `prompt_always`) are defined in [§4.5 Write Mode](../01-foundations/04-core-concepts.md#45-lifecycle-terms).

## 7.1 Tier 0: Supervised

**Principle:** Human approves every secret access.

| ID | Level | Requirement |
|----|-------|-------------|
| TIER-0-1 | MUST | Read approval policy MUST be `prompt_always` |
| TIER-0-2 | MUST | Write approval policy MUST be `prompt_always` |
| TIER-0-3 | MUST | Session caching MUST NOT be enabled |
| TIER-0-4 | MUST | **Headless** (unattended) operation **MUST NOT** be used. *Definition:* **Headless operation** means the Guardian is running in an environment where no human principal is available to respond to interactive approval prompts in real time — for example, a CI/CD pipeline, a container orchestrator, a scheduled batch job, or a background daemon. The headless vs. interactive distinction determines whether interactive approval modes (`prompt_once`, `prompt_always`) can be used; it is orthogonal to whether the deployment is local or remote, single-machine or distributed. Where this standard requires headless mode to be "explicitly opted into," the mechanism is implementation-defined (environment variable, startup flag, or configuration setting) |

### Use Cases

- Initial deployment of agentic systems
- Compliance-heavy environments (financial, healthcare, government)
- Production systems with direct financial or safety impact
- High-value secrets (root credentials, production database access)

### User Visibility

**Maximum.** The user sees every access request, approves or denies each one individually, and receives immediate notification of any secret use.

> **Note:** Profiles operating at Tier 0 generate the highest volume of approval prompts and are subject to approval fatigue risk ([TS-17](../01-foundations/03-threat-model.md#353-approval-fatigue-exploitation-ts-17)). Implementations **SHOULD** apply the rate limiting and escalating confirmation controls specified in [§3.5.3](../01-foundations/03-threat-model.md#353-approval-fatigue-exploitation-ts-17) for profiles at Tier 0.

### Trade-offs

| Pro | Con |
|-----|-----|
| Complete visibility | High friction for frequent operations |
| No unauthorized access possible | Requires human availability |
| Strong audit trail | May slow down time-sensitive operations |

---

## 7.2 Tier 1: Session-Trusted

**Principle:** Human approves once per session, then tools operate freely within the session window.

| ID | Level | Requirement |
|----|-------|-------------|
| TIER-1-1 | MUST | Read approval policy MUST be `prompt_once` |
| TIER-1-2 | MUST | Write approval policy MUST be `same` |
| TIER-1-3 | MUST | Session caching MUST be enabled with a configured TTL |
| TIER-1-4 | MUST | Session TTL MUST NOT exceed 3600 seconds (1 hour). TTLs exceeding 3600 seconds reduce the security benefit of session-scoped approval to near zero; a session that can last indefinitely provides no meaningful time-bound on the human's approval. The RECOMMENDED TTL range is 1800 to 3600 seconds (30–60 minutes). TTLs below 300 seconds (5 minutes) impose excessive approval friction without proportionate security gain and SHOULD be avoided. If operational requirements necessitate TTLs exceeding 3600 seconds, the profile SHOULD be operated at Tier 0 (prompt_always) rather than extending Tier 1 session windows |
| TIER-1-5 | MUST | Headless (unattended) operation MUST NOT be used |

### Use Cases

- Development workflows
- Interactive agent sessions
- Pair-programming with AI assistants
- Day-to-day engineering work

> **This is the RECOMMENDED default tier for most deployments.** Tier 1 preserves explicit human consent at session boundaries (addressing approval social engineering, [TS-16](../01-foundations/03-threat-model.md#352-approval-social-engineering-ts-16)) while reducing friction for interactive workflows. Tier 0 imposes per-operation approval overhead that degrades usability for routine development. Tier 2 removes the human approval gate entirely, which is inappropriate as a default given the risks identified in [§3.5.2](../01-foundations/03-threat-model.md#352-approval-social-engineering-ts-16).

> **Note:** Approval fatigue risk ([TS-17](../01-foundations/03-threat-model.md#353-approval-fatigue-exploitation-ts-17)) applies during session establishment, particularly when the user operates multiple Tier 1 profiles. Implementations **SHOULD** apply the rate limiting and escalating confirmation controls specified in [§3.5.3](../01-foundations/03-threat-model.md#353-approval-fatigue-exploitation-ts-17) during session establishment.

### User Visibility

**Moderate.** The user approves access at the start of a work session. The audit log records all subsequent accesses within the session. The user can revoke the session at any time.

### Trade-offs

| Pro | Con |
|-----|-----|
| Low friction for interactive work | Session cache is a limited credential |
| Still requires explicit approval | Less visibility than Tier 0 |
| Easy revocation | TTL management required |

---

## 7.3 Tier 2: Tool-Autonomous

**Principle:** Tools operate freely within their token scope. Reads are automatic; writes are automatic or denied per-profile.

| ID | Level | Requirement |
|----|-------|-------------|
| TIER-2-1 | MUST | Read approval policy MUST be `auto` |
| TIER-2-2 | MUST | Write approval policy MUST be `auto` or `deny`, configured per-profile. Profiles with any entries marked `sensitive=true` **MUST** use `deny` unless all four of the following conditions are met: (a) **Trigger** — write-back is operationally required for that profile (e.g., OAuth token refresh where the tool must write the refreshed token) and no alternative exists (i.e., Guardian-managed refresh per §11.4 is not feasible for this credential type); (b) **Scope** — the profile definition explicitly enumerates by key name each `sensitive=true` entry that is permitted for auto-write; wildcard or category-level authorization is **NOT** conformant; (c) **Minimal privilege** — the enumerated set of `sensitive=true` entries permitted for auto-write is the minimum set required for the operational use case; access to additional `sensitive=true` entries beyond the minimum MUST require a separate, independently-justified exception documented in the same conformance statement; (d) **Documentation** — the exception is **documented as a named risk acceptance in the conformance statement**, including the profile name, each enumerated entry key, the operational justification, and the identity of the security principal accepting the risk. The conformance statement risk acceptance entry is a hard gate — `auto` write on a `sensitive=true` Tier 2 profile without a conformance statement entry covering all four conditions is a configuration non-conformance regardless of operational justification |
| TIER-2-3 | SHOULD | Token TTLs SHOULD be shorter than those used at Tier 0 (Supervised) and Tier 1 (Session-Trusted) to limit the exposure window in the absence of interactive approval |
| TIER-2-4 | MUST | Headless (unattended) operation is permitted |

### Use Cases

- CI/CD pipelines
- Production services
- Batch processing
- Server-side agents
- Automated workflows

### User Visibility

**Low at runtime.** The user relies on audit logs, dashboards, and alerting for post-hoc visibility. The user retains the ability to revoke access at any time.

### Trade-offs

| Pro | Con |
|-----|-----|
| No human in the loop | Reduced real-time visibility |
| Suitable for automation | Requires robust audit/alerting |
| Works in headless environments | Compromise has wider blast radius |

### Compensating Controls

When operating at Tier 2, implementations **MUST** apply the following minimum controls to offset the absence of interactive human approval. Without these controls, a Tier 2 deployment provides less security assurance than a monitored API key in a conventional system.

| ID | Level | Control | Requirement | Cross-Reference |
|----|-------|---------|-------------|-----------------|
| TIER-2-MUST-1 | MUST | Rate limiting | The Guardian **MUST** enforce a configurable maximum rate of secret access requests per token per time window. Exceeding the configured limit **MUST** result in denial of subsequent requests for the remainder of the time window and **MUST** generate a WARN-level audit event | [§4.3 Agent Token](../01-foundations/04-core-concepts.md#43-access-control-terms) |
| TIER-2-MUST-2 | MUST | Anomaly alerting | The Guardian **MUST** emit an alert when access frequency exceeds the configured rate limit or when access originates from a previously unseen transport endpoint. Alerts **MUST** be delivered through a channel accessible to the human principal | [§15 Audit & Observability](../05-reference/15-audit-observability.md) |
| TIER-2-SHOULD-1 | SHOULD | Regular audit log review | Audit logs SHOULD be reviewed at least weekly for Tier 2 profiles | [§15 Audit & Observability](../05-reference/15-audit-observability.md) |
| TIER-2-SHOULD-2 | SHOULD | Short token TTLs | Token TTLs SHOULD be shorter than at Tier 0/1 to limit the exposure window in the absence of interactive approval | [§4.3 Agent Token](../01-foundations/04-core-concepts.md#43-access-control-terms) |
| TIER-2-SHOULD-3 | SHOULD | Network segmentation | Guardian SHOULD be network-isolated to restrict access to authorized agent hosts only | [§3.6 Guardian Deployment Topology](../01-foundations/03-threat-model.md#36-guardian-deployment-topology) |

---

## 7.4 Tier 3: Full Delegation

**Principle:** Agent and tools operate with maximal autonomy. Human oversight is post-hoc via audit logs and anomaly detection.

| ID | Level | Requirement |
|----|-------|-------------|
| TIER-3-1 | MUST | Read approval policy MUST be `auto` |
| TIER-3-2 | MUST | Write approval policy MUST be `auto` |
| TIER-3-3 | MUST | Headless (unattended) operation is permitted |

### Use Cases

- Fully autonomous agents managing infrastructure
- Long-running background services
- Trusted internal tooling
- Systems with strong compensating controls

> **Warning:** Tier 3 **SHOULD** only be adopted after the deployment has operated at Tier 2 with the compensating controls below verified as operational. Adopting Tier 3 without verified compensating controls creates an unmonitored automation environment: the highest-risk configuration this standard addresses.

### User Visibility

**Minimal at runtime.** Requires robust audit logging, alerting on anomalous patterns, and periodic human review.

### Trade-offs

| Pro | Con |
|-----|-----|
| Maximum automation | Minimal real-time control |
| Lowest friction | Highest risk without compensating controls |
| Suitable for trusted environments | Breach may go undetected longer |

### Required Compensating Controls

Tier 3 deployments **MUST** implement the following compensating controls. Each control addresses specific risks introduced by the absence of interactive human oversight:

| ID | Level | Control | Acceptance Criteria | Cross-Reference |
|----|-------|---------|---------------------|-----------------|
| TIER-3-C1 | MUST | Network segmentation | Guardian is network-isolated from untrusted hosts; only authorized agent hosts can reach the Guardian's listening port | [§3.6 TOPO-7](../01-foundations/03-threat-model.md#364-normative-requirements-for-remote-deployment) |
| TIER-3-C2 | MUST | Rate limiting | Maximum secret access requests per token per time window is configured and enforced | [Appendix B Compensating Controls](../06-appendices/appendix-b-compensating-controls.md) |
| TIER-3-C3 | MUST | Credential rotation | Token TTLs and secret rotation schedules are configured per-profile | [§11 Secret Lifecycle](../03-architecture/11-secret-lifecycle.md) |
| TIER-3-C4 | MUST | Anomaly detection | Access patterns are monitored against an established baseline; deviations trigger alerts | [Appendix B Compensating Controls](../06-appendices/appendix-b-compensating-controls.md) |
| TIER-3-C5 | MUST | Access reviews | Periodic human review of access logs and token assignments at a cadence not exceeding 30 days | [§15 Audit & Observability](../05-reference/15-audit-observability.md) |
| TIER-3-C6 | MUST | Alerting | Alerts configured for: token creation/revocation, access outside baseline patterns, failed authentication attempts, and write operations | [§15 Audit & Observability](../05-reference/15-audit-observability.md) |

---

## 7.5 Tier Selection Decision Guide

```
                        Human Involvement
                        High --|-- Low
                               |
  Tier 0: Supervised           |
    Every access approved       |
                               |
  Tier 1: Session-Trusted      |   <-- RECOMMENDED DEFAULT
    Approve once per            |
    session                     |
                               |
  Tier 2: Tool-Autonomous      |
    Auto-approve reads,        |
    per-profile writes          |
                               |
  Tier 3: Full Delegation      |
    Full autonomy with         |
    post-hoc audit              |
                               |
                        Risk Tolerance
                        Low ---|--- High
```

### Selection Questions

| Question | If Yes | If No |
|----------|--------|-------|
| Is the secret for production systems? | Consider Tier 0 or 1 | Tier 2-3 may be appropriate |
| Must a human approve every access (compliance)? | Tier 0 | Lower tiers possible |
| Will the agent run unattended? | Tier 2 or 3 | Tier 0 or 1 |
| Do you have robust audit and alerting? | Tier 2-3 viable | Stay at Tier 0-1 |
| Is this for development/testing? | Tier 1 is standard | N/A |
| Can you tolerate access without real-time visibility? | Tier 2-3 viable | Tier 0-1 |

### Mixed-Tier Deployments

Organizations commonly run different profiles at different tiers:

| Profile | Tier | Rationale |
|---------|------|-----------|
| `aws-production` | 0 | Production infrastructure, high blast radius |
| `github-readonly` | 1 | Development work, acceptable risk |
| `monitoring-api` | 2 | Automated monitoring, low-value secrets |
| `internal-service-token` | 3 | Trusted internal, with compensating controls |

---

## 7.6 Escalation and De-escalation

### Escalating (Moving to Lower Tier Number)

When increasing human oversight:
1. Update profile approval policy to the target tier's requirements
2. Invalidate existing session caches for the affected profile
3. Notify affected users/tools
4. Update audit alerting thresholds

In-flight operations that were authorized under the previous tier's policy **MAY** complete, but new requests **MUST** be evaluated under the escalated tier's policy. The Guardian **MUST** apply the new tier policy atomically: from the moment the escalation is committed in the Guardian's configuration, all subsequent requests **MUST** be evaluated under the new policy. There is no grace period or transition window during which the previous tier's policy applies to new requests. If the Guardian cannot atomically apply the new tier policy (e.g., due to a distributed multi-instance deployment), it **MUST** fail closed: all new requests **MUST** be denied until the new policy is confirmed active. The escalation event **MUST** be recorded in the audit log with the timestamp at which the new policy took effect. Secrets already delivered to tool memory are subject to the retention rules of [§5.2 Minimal Disclosure](05-design-principles.md#52-principle-of-minimal-disclosure).

### De-escalating (Moving to Higher Tier Number)

When reducing human oversight:
1. Verify compensating controls required by the target tier are in place and operational
2. Reduce token TTLs to the target tier's recommended range
3. Increase audit review frequency
4. Set up additional alerting as required by the target tier
5. **MUST** operate at the target tier for a trial period of at least 7 days with enhanced monitoring before finalizing the transition. During the trial period, the previous tier's compensating controls **MUST** remain active in addition to the target tier's requirements

---

## 7.7 Relationship to Conformance Levels

Autonomy tiers and conformance levels ([§13](../04-conformance/13-conformance.md)) are orthogonal concepts. **Conformance levels** define the implementation's architectural capabilities (what the system *can* do). **Autonomy tiers** define the operational posture for a specific profile (how much human oversight is *applied*).

Any conformance level can operate at any tier, but certain combinations have implications:

| Tier | Level 1 | Level 2 | Level 3 |
|------|---------|---------|---------|
| Tier 0 | Viable. Terminal-based approval is permitted | Full agent-independent approval channel support | Full controls |
| Tier 1 | Viable. Session caching may be limited (not required at Level 1) | Recommended combination for most deployments | Full controls |
| Tier 2 | **Caution.** Level 1 lacks the audit query support (§13.3) needed for effective post-hoc oversight | Viable with audit infrastructure | Recommended for automation |
| Tier 3 | **Prohibited.** Level 1 lacks anomaly detection, SIEM export, and approval fatigue controls required by Tier 3 compensating controls (TIER-3-C1 through TIER-3-C6). See TIER-3-L below | Viable if compensating controls are externally provided | Full alignment: all Tier 3 compensating controls are Level 3 capabilities |

| ID | Level | Requirement |
|----|-------|-------------|
| TIER-3-L | MUST | Tier 3 MUST NOT be used with Level 1 implementations. Tier 3 compensating controls (TIER-3-C1 through TIER-3-C6) require capabilities (anomaly detection, structured audit queries, alerting infrastructure) that are not present at Level 1. Operating at Tier 3 without these capabilities creates an unmonitored, fully autonomous environment with no architectural mechanism to detect abuse |

Implementations **MUST** enforce the following behaviors when a profile's tier selection is incompatible with the deployment's conformance level:

| Tier–Level Combination | Required Behavior |
|------------------------|-------------------|
| Tier 3 at Level 1 (prohibited by TIER-3-L) | **MUST reject** with a clear error message describing why the combination is prohibited. The Guardian **MUST NOT** persist a Tier 3 profile configuration at Level 1, even temporarily. This is a hard stop, not an advisory warning |
| Tier 2 at Level 1 (advisory caution) | **SHOULD warn** the administrator prominently at configuration time, describing which Level 2+ capabilities (audit queries, anomaly detection, alerting) are unavailable and how this affects operational visibility. MAY proceed if the administrator acknowledges the warning |
| Any tier where required compensating controls are not operational | **MUST warn** at startup and **SHOULD** surface the gap in audit events. Implementations that can detect non-operational compensating controls (e.g., alerting channel unreachable) **MUST** log this state and **SHOULD** notify the human principal |

At minimum, the implementation **MUST** prevent Tier 3 assignment at Level 1. The TIER-3-L requirement is not advisory.

---

Next: [Secret Profiles](../03-architecture/08-secret-profiles.md)
