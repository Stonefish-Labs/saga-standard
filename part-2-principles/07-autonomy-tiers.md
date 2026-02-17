# 7. Autonomy Tiers

This standard defines four autonomy tiers that represent progressively greater levels of trust delegated to the agent and its tools. Selecting the appropriate tier is a risk management decision that balances operational efficiency against security posture.

Autonomy tiers are selected **per-profile**. A profile's tier determines the approval policy, session caching behavior, and compensating control requirements that **MUST** be applied to that profile. A deployment **MAY** operate different profiles at different tiers (see §7.5, Mixed-Tier Deployments).

The approval modes referenced in each tier (`auto`, `prompt_once`, `prompt_always`) are defined in [§4.4 Approval Policy](../part-1-foundations/04-core-concepts.md#44-approval-terms) and governed by the normative requirements in [§10 Approval Policies](../part-3-architecture/10-approval-policies.md). The write modes (`same`, `auto`, `deny`, `prompt_always`) are defined in [§4.5 Write Mode](../part-1-foundations/04-core-concepts.md#45-lifecycle-terms).

## 7.1 Tier 0: Supervised

**Principle:** Human approves every secret access.

| ID | Level | Requirement |
|----|-------|-------------|
| TIER-0-1 | MUST | Read approval policy MUST be `prompt_always` |
| TIER-0-2 | MUST | Write approval policy MUST be `prompt_always` |
| TIER-0-3 | MUST | Session caching MUST NOT be enabled |
| TIER-0-4 | MUST | Headless (unattended) operation MUST NOT be used |

### Use Cases

- Initial deployment of agentic systems
- Compliance-heavy environments (financial, healthcare, government)
- Production systems with direct financial or safety impact
- High-value secrets (root credentials, production database access)

### User Visibility

**Maximum.** The user sees every access request, approves or denies each one individually, and receives immediate notification of any secret use.

> **Note:** Profiles operating at Tier 0 generate the highest volume of approval prompts and are subject to approval fatigue risk ([TS-17](../part-1-foundations/03-threat-model.md#353-approval-fatigue-exploitation-ts-17)). Implementations **SHOULD** apply the rate limiting and escalating confirmation controls specified in [§3.5.3](../part-1-foundations/03-threat-model.md#353-approval-fatigue-exploitation-ts-17) for profiles at Tier 0.

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
| TIER-1-4 | SHOULD | Session TTL SHOULD be between 1800 and 3600 seconds (30-60 minutes). TTLs exceeding 3600 seconds reduce the security benefit of session-scoped approval; TTLs below 300 seconds (5 minutes) impose excessive approval friction without proportionate security gain |
| TIER-1-5 | MUST | Headless (unattended) operation MUST NOT be used |

### Use Cases

- Development workflows
- Interactive agent sessions
- Pair-programming with AI assistants
- Day-to-day engineering work

> **This is the RECOMMENDED default tier for most deployments.** Tier 1 preserves explicit human consent at session boundaries (addressing approval social engineering, [TS-16](../part-1-foundations/03-threat-model.md#352-approval-social-engineering-ts-16)) while reducing friction for interactive workflows. Tier 0 imposes per-operation approval overhead that degrades usability for routine development. Tier 2 removes the human approval gate entirely, which is inappropriate as a default given the risks identified in [§3.5.2](../part-1-foundations/03-threat-model.md#352-approval-social-engineering-ts-16).

> **Note:** Approval fatigue risk ([TS-17](../part-1-foundations/03-threat-model.md#353-approval-fatigue-exploitation-ts-17)) applies during session establishment, particularly when the user operates multiple Tier 1 profiles. Implementations **SHOULD** apply the rate limiting and escalating confirmation controls specified in [§3.5.3](../part-1-foundations/03-threat-model.md#353-approval-fatigue-exploitation-ts-17) during session establishment.

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
| TIER-2-2 | MUST | Write approval policy MUST be `auto` or `deny`, configured per-profile. Profiles with any entries marked `sensitive=true` MUST use `deny` unless write-back is operationally required for that profile (e.g., OAuth token refresh), in which case `auto` is permitted with a documented justification in the profile configuration |
| TIER-2-3 | SHOULD | Token TTLs SHOULD be shorter than at lower tiers to limit the exposure window in the absence of interactive approval |
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

When operating at Tier 2, implementations **SHOULD** apply the following controls to offset the absence of interactive human approval:

| Control | Cross-Reference |
|---------|-----------------|
| Regular audit log review | [§15 Audit & Observability](../part-5-reference/15-audit-observability.md) |
| Anomaly detection on access patterns | [Appendix B Compensating Controls](../appendices/appendix-b-compensating-controls.md) |
| Short token TTLs | [§4.3 Agent Token](../part-1-foundations/04-core-concepts.md#43-access-control-terms) |
| Network segmentation | [§3.6 Guardian Deployment Topology](../part-1-foundations/03-threat-model.md#36-guardian-deployment-topology) |
| Alerting on unusual access patterns | [§15 Audit & Observability](../part-5-reference/15-audit-observability.md) |

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

> **Warning:** Tier 3 **SHOULD** only be adopted after the deployment has operated at Tier 2 with the compensating controls below verified as operational. Adopting Tier 3 without verified compensating controls creates an unmonitored automation environment -- the highest-risk configuration this standard addresses.

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
| TIER-3-C1 | MUST | Network segmentation | Guardian is network-isolated from untrusted hosts; only authorized agent hosts can reach the Guardian's listening port | [§3.6 TOPO-7](../part-1-foundations/03-threat-model.md#364-normative-requirements-for-remote-deployment) |
| TIER-3-C2 | MUST | Rate limiting | Maximum secret access requests per token per time window is configured and enforced | [Appendix B Compensating Controls](../appendices/appendix-b-compensating-controls.md) |
| TIER-3-C3 | MUST | Credential rotation | Token TTLs and secret rotation schedules are configured per-profile | [§11 Secret Lifecycle](../part-3-architecture/11-secret-lifecycle.md) |
| TIER-3-C4 | MUST | Anomaly detection | Access patterns are monitored against an established baseline; deviations trigger alerts | [Appendix B Compensating Controls](../appendices/appendix-b-compensating-controls.md) |
| TIER-3-C5 | MUST | Access reviews | Periodic human review of access logs and token assignments at a cadence not exceeding 30 days | [§15 Audit & Observability](../part-5-reference/15-audit-observability.md) |
| TIER-3-C6 | MUST | Alerting | Alerts configured for: token creation/revocation, access outside baseline patterns, failed authentication attempts, and write operations | [§15 Audit & Observability](../part-5-reference/15-audit-observability.md) |

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

In-flight operations that were authorized under the previous tier's policy **MAY** complete, but new requests **MUST** be evaluated under the escalated tier's policy immediately upon escalation. Secrets already delivered to tool memory are subject to the retention rules of [§5.2 Minimal Disclosure](05-design-principles.md#52-principle-of-minimal-disclosure).

### De-escalating (Moving to Higher Tier Number)

When reducing human oversight:
1. Verify compensating controls required by the target tier are in place and operational
2. Reduce token TTLs to the target tier's recommended range
3. Increase audit review frequency
4. Set up additional alerting as required by the target tier
5. **MUST** operate at the target tier for a trial period of at least 7 days with enhanced monitoring before finalizing the transition. During the trial period, the previous tier's compensating controls **MUST** remain active in addition to the target tier's requirements

---

## 7.7 Relationship to Conformance Levels

Autonomy tiers and conformance levels ([§13](../part-4-conformance/13-conformance.md)) are orthogonal concepts. **Conformance levels** define the implementation's architectural capabilities (what the system *can* do). **Autonomy tiers** define the operational posture for a specific profile (how much human oversight is *applied*).

Any conformance level can operate at any tier, but certain combinations have implications:

| Tier | Level 1 | Level 2 | Level 3 |
|------|---------|---------|---------|
| Tier 0 | Viable. Terminal-based approval is permitted | Full agent-independent approval channel support | Full controls |
| Tier 1 | Viable. Session caching may be limited (not required at Level 1) | Recommended combination for most deployments | Full controls |
| Tier 2 | **Caution.** Level 1 lacks the audit query support (§13.3) needed for effective post-hoc oversight | Viable with audit infrastructure | Recommended for automation |
| Tier 3 | **Prohibited.** Level 1 lacks anomaly detection, SIEM export, and approval fatigue controls required by Tier 3 compensating controls (TIER-3-C1 through TIER-3-C6). See TIER-3-L below | Viable if compensating controls are externally provided | Full alignment -- all Tier 3 compensating controls are Level 3 capabilities |

| ID | Level | Requirement |
|----|-------|-------------|
| TIER-3-L | MUST | Tier 3 MUST NOT be used with Level 1 implementations. Tier 3 compensating controls (TIER-3-C1 through TIER-3-C6) require capabilities -- anomaly detection, structured audit queries, alerting infrastructure -- that are not present at Level 1. Operating at Tier 3 without these capabilities creates an unmonitored, fully autonomous environment with no architectural mechanism to detect abuse |

Implementations **MUST** reject or warn administrators when a profile's tier selection exceeds the compensating control capabilities of the deployment's conformance level. At minimum, the implementation **MUST** prevent Tier 3 assignment at Level 1.

---

Next: [Secret Profiles](../part-3-architecture/08-secret-profiles.md)
