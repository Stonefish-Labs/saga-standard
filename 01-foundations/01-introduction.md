# 1. Introduction and Motivation

## 1.1 The Secrets Isolation Problem in Agentic AI

Modern agentic systems operate by invoking tools and services that require **secrets**.

> **Secret** (n.): Any piece of information that, alone or in combination, grants access to a resource or enables a privileged capability. Credentials, keys, tokens, and any other material whose disclosure would permit unauthorized operations. (See [Core Concepts](04-core-concepts.md) for the full definition.)

For instance: 

* An agent tasked with managing a deployment pipeline needs cloud provider tokens. 
* An agent handling customer support needs CRM API keys. 
* An agent managing email needs OAuth credentials. 
* An agent performing signing operations needs access to tools that leverage a private key.

However, the agents that orchestrate these operations cannot be trusted as principals:

- **Non-deterministic behavior.** Agent outputs cannot be formally verified. The same input may produce different actions across invocations.
- **Susceptibility to corruption.** Prompt injection, adversarial inputs, and emergent behaviors can influence the agent in ways that no amount of instruction-tuning can guarantee against.
- **Unknowable behavior landscape.** The full space of actions an agent may take is not enumerable or auditable in advance.

Yet the resources and capabilities these agents need to get things done require secrets. This is the fundamental tension: the agent cannot be trusted with secrets, but it must drive tools that depend on them.

> **A note on sensitive data:** Agents routinely handle PII, financial records, medical information, and other sensitive data as part of normal operation. That carries its own risks, addressed by other standards. All secrets are sensitive, but not all sensitive data are secrets. A leaked medical record is a privacy violation; a leaked API key opens a door. 

This is a fundamentally different problem from traditional secrets management.

### The Traditional Model

In conventional systems, the principal consuming the secret (a running service, a deployment pipeline, a human operator) is also the entity that is trusted with the secret:

```
┌─────────────┐
│ Application │ ─── holds secret ───→ Access API
└─────────────┘
      │
      └── same entity is authorized and consumes
```
These models work because the entity consuming the secret is deterministic and verifiable. OAuth assumes the requesting party *is* the consuming party. RBAC assumes a single identity at the point of use. Secrets managers like HashiCorp Vault and AWS Secrets Manager assume the process consuming the secret is the authorized principal. Even SPIFFE/SPIRE, which provides cryptographic workload identity for autonomous systems without a human behind them, assumes the attested workload itself is the trusted consumer.

Agentic systems technically *are* consuming the secret, but they insert a nondeterministic, corruptible reasoning layer between authorization and consumption. That reasoning layer has minimal isolation, can be coerced into leaking secrets or routing them to unrelated tools, and operates in an environment where the full landscape of potential behaviors is unknowable. None of these traditional models have any concept of isolating *within* the consuming entity's own execution chain.

### The Agentic Model

In agentic systems, the secrets management problem involves three parties:

- The **human principal** who owns the secrets and authorizes their use
- The **agent** (LLM reasoning loop) that decides *which* operations to perform but must never see or hold secrets
- The **tool runtime** (function, skill, MCP server) that performs authenticated operations and needs the actual secret values

This is the **three-party problem**: the human authorizes, the agent decides, and the tool consumes. However, the agent, which sits between authorization and consumption, cannot be trusted with the secrets it is orchestrating the use of.

This standard resolves the three-party problem through a **Guardian** - a process-isolated mediator entrusted by the human principal with their secrets and the policies governing their use. The Guardian controls access to the encrypted secret store, enforces authorization, and delivers secrets directly to authorized tools. The Guardian has no connection to the Agent. The agent instructs the tool; the Guardian supplies the secret. These are entirely separate channels, and the agent has no viable path to intercept the secret delivery. (See [Core Concepts](04-core-concepts.md) for the full Guardian definition.)

```
┌─────────────────┐
│ Human Principal │ ─── owns secrets, authorizes their use
└────────┬────────┘
         │ entrusts secrets and policies
         │
         ▼
┌─────────────────┐         ┌─────────────────┐
│    Guardian     │────────►│      Tool       │
│   (Mediator)    │ delivers│   (Executor)    │
└────────┬────────┘ secrets └─────────────────┘
         │                          ▲
         │ requests approval        │ instructs (no secrets)
         │ when policy requires     │
         ▼                   ┌─────────────────┐
┌─────────────────┐          │     Agent       │
│ Human Principal │          │  (LLM Loop)     │
│  (approves/     │          └─────────────────┘
│   denies)       │            NEVER sees secrets
└─────────────────┘            NO connection to Guardian
```

Critically, the agent must not need to know about specific secrets to accomplish its tasks. But we cannot pretend the agent will never discover that a tool requires a secret - it may infer this from tool descriptions, error messages, or its own reasoning. Even when the agent *does* know a secret exists, the architecture must make it impossible for the agent to retrieve, reconstruct, or exfiltrate the value. This is an architectural requirement, not a behavioral one.

No existing standard addresses the combination of agent-isolation, scoped tool authorization, and human-mediated approval that the three-party model requires. This is the gap this standard fills.

## 1.2 Why Existing Standards Are Insufficient

### [OWASP Top 10 for Agentic Applications (2026)](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)

Identifies "Insecure Credential Storage" and "Excessive Permissions" as risks but intentionally defers architectural solutions to domain-specific standards. The OWASP list is a risk taxonomy; this standard provides the implementation architecture it points to.

### [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)

Defines transport-level authentication (OAuth 2.1) for server identity but explicitly delegates secret management to the application layer. It provides:
- No mechanism for per-tool secret scoping
- No isolation between tools sharing a runtime
- No human approval attestation

### [IETF OAuth On-Behalf-Of for AI Agents (draft)](https://datatracker.ietf.org/doc/draft-oauth-ai-agents-on-behalf-of-user/01/)

Addresses identity delegation (how an agent acts on behalf of a user with a third-party service) but does not address:
- Secret storage
- Isolation from the reasoning model
- Multi-secret profiles

### [NIST AI RMF](https://www.nist.gov/itl/ai-risk-management-framework) and [CAISI](https://www.nist.gov/caisi)

Focus on AI safety, bias, and organizational governance. The CAISI RFI (closing March 2026) explicitly calls for proposals on "agentic system security" but no secret management specification has been proposed.

### [SPIFFE/SPIRE](https://spiffe.io/) and Workload Identity

SPIFFE provides cryptographic workload identity and SPIRE delivers secrets to authenticated processes (directly relevant to secret delivery). However, both assume the workload receiving the secret *is* the trusted principal. They have no concept of a nondeterministic reasoning layer between identity attestation and secret consumption. SPIFFE solves *which process gets the secret*; this standard solves *what happens when the process that decides is not the process that consumes*.

### Confidential Computing and [TEEs](https://confidentialcomputing.io/)

Trusted Execution Environments (Intel SGX, ARM TrustZone, AMD SEV) provide hardware-enforced memory isolation, protecting workloads from the infrastructure they run on. This solves a different problem. The three-party problem is not about protecting secrets from the platform; it's about isolating secrets from the application's own reasoning layer. TEEs protect workloads from the infrastructure they run on (the hypervisor, the host OS, co-tenant processes on the same hardware). This is valuable, but it does not address the three-party problem, which is an isolation problem *within a single workload's trust domain*: the agent, the tool, and the Guardian all run within the same TEE-protected boundary. TEEs have no concept of isolating the reasoning layer from the secret-consuming layer within their own protected boundary. This standard governs the intra-workload isolation that TEEs do not address.

## 1.3 What This Standard Provides

This standard establishes a comprehensive framework that addresses:

| Concern | Approach |
|---------|----------|
| Agent access to secrets | Architectural isolation: agent never holds secrets |
| Tool access control | Scoped tokens, per-profile authorization |
| Human oversight | Configurable approval policies with out-of-band confirmation channels |
| Secret lifecycle | Write-back through mediated channel, OAuth refresh |
| Auditability | Complete, tamper-evident access logs (see [Audit & Observability](../05-reference/15-audit-observability.md)) |
| Delegation | Controlled inter-agent secret propagation |
| Risk management | Autonomy tiers with graduated controls |

## 1.4 Design Goals

> **Note on normative language:** The design goals in this section describe the mandatory properties of a conformant implementation. Formal normative requirements using RFC 2119 keywords (**MUST**, **SHOULD**, **MAY**) appear in their respective architectural sections (see [Design Principles](../02-principles/05-design-principles.md)). Where this section uses "must," the corresponding normative requirement is stated with RFC 2119 precision in the referenced section.

The standard is designed around six mandatory design goals:

### Goal 1: The Agent Never Holds Secrets

The reasoning model, its context window, its output streams, and the orchestration environment in which the agent operates (including client applications, framework logs, conversation history, and any other storage or telemetry accessible to the agent process) must never contain raw secret values. The agent must never need to know about specific secrets to accomplish its tasks. Secret access must be mediated by an architectural boundary, not by prompt engineering or behavioral constraints.

If the agent learns that a secret exists - through tool descriptions, error messages, or its own reasoning, the architecture must provide no viable path for the agent to retrieve, reconstruct, or exfiltrate the value. The agent must not be able to write or execute arbitrary code that accesses secret storage or intercepts tool-to-mediator communication. The secret must be unreachable through any path available to the agent or tools operating at standard privilege levels. (The standard assumes a trusted operating system kernel; see [Accepted Risks](03-threat-model.md#34-accepted-risks) for the implications of privileged system access.)

Modern agents are not passive question-answerers. A growing number of agents have access to the filesystem, the terminal, and the ability to write and execute arbitrary code - these are foundational capabilities that make them useful. They are also the exact capabilities that allow a misbehaving agent to function as a malicious insider: reading files, searching for credentials, writing exfiltration scripts, and executing them. Prompt engineering cannot prevent this. A model instructed to "not reveal secrets" has no guarantee of compliance, especially under prompt injection attacks. Behavioral constraints are not security controls. Only architectural barriers that make retrieval impossible, regardless of agent intent or ingenuity, satisfy this goal.

### Goal 2: The Human Always Retains Control

Regardless of autonomy level, the human principal must be able to inspect, revoke, and audit any secret access at any time. Automation does not eliminate human authority; it defers it. Even when the immediate approval decision is delegated to an automated evaluator or another agentic system, a human principal must remain at the end of the chain with the ability to override, revoke, or shut down access at any point.

The human owns the secrets, the consequences of their use, and the liability for the actions of agents acting on their behalf. No amount of delegation removes the human from the accountability chain. No level of convenience justifies removing the owner's ability to control their own credentials.

### Goal 3: Access Is Scoped, Not Global

A tool must only be able to access the specific profiles it has been explicitly authorized for, no more. A tool that needs multiple profiles (e.g., source and destination credentials for a migration) may hold multiple scoped tokens, but each must be individually granted. Authorization to one profile must never implicitly grant access to another.

An agent that can invoke a tool has access to the full scope of that tool's capabilities; restricting what the tool can *do* is outside the scope of this standard. What this standard *can* control is which secrets the tool receives. Scoped access is the principle of least privilege applied to the one dimension the secret management layer controls: which credentials reach which tool. Compartmentalization limits blast radius. If one tool is compromised, damage is contained to its authorized profiles.

### Goal 4: Write-Back Is a First-Class Operation

Secrets are not static. OAuth tokens expire and must be refreshed. API keys are rotated. Session tokens change. The standard must support writing updated secrets through the same mediated channel as reads, subject to independent write authorization policies that may be more restrictive than read policies.

OAuth token refresh is the most common write-back scenario. Without mediated writes, tools would store refreshed tokens in their own storage, breaking the isolation model. But a write path is also an attack surface: a compromised tool that can write back can poison credentials for future invocations. This is why write-back requires its own authorization policy, independent of and potentially stricter than the read policy (see [Design Principles](../02-principles/05-design-principles.md)).

Note that external provisioning methods (human-seeded, Guardian-mediated, programmatic) are the preferred mechanisms for cold-starting and seeding secret values (see [Secret Lifecycle](../03-architecture/11-secret-lifecycle.md)). These channels do not expose the tool write path at all. Write-back exists for operational updates during tool execution, but where possible, Guardian-managed refresh eliminates the need for tool-initiated writes entirely. When write-back is required, it must be done properly through the mediated channel with appropriate authorization controls.

### Goal 5: Every Access Is Auditable

There must be a complete, tamper-evident record of which tool accessed which secret, when, from which process, and whether the access was approved automatically, by session cache, or by interactive confirmation.

In the event of a breach or misuse, you need to know exactly what was accessed and by what.

### Goal 6: The Standard Must Be Implementable in Any Runtime

The standard must not require specific programming languages, operating systems, or frameworks. A conformant implementation must be achievable with common operating system primitives (process isolation, filesystem permissions, IPC), standard cryptographic libraries, and standard inter-process communication mechanisms. The standard does not require any specific operating system, though specific transport bindings (see [Conformance](../04-conformance/13-conformance.md)) may leverage platform-specific facilities such as Unix domain sockets or Windows named pipes.

Agentic systems are heterogeneous. The standard must work across Python tools, Node.js servers, Go services, and anything else the ecosystem produces, on any platform that supports process isolation and standard cryptography.

---

Next: [Scope](02-scope.md)
