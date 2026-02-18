# SAGA: Secret Access Governance for Agents

## What This Is

This is a standard for managing secrets in systems where autonomous AI agents invoke tools and services on your behalf. It defines how to keep secrets away from agent reasoning while still allowing agents to get work done that requires authentication.

**The problem:** Your AI agent needs to access your AWS account, your GitHub repos, your Slack workspace. But you don't want the agent's reasoning model to ever see your API keys, tokens, or passwords. And you want to stay in control: knowing what's accessed, approving when needed, and able to revoke at any time.

**The solution:** A mediated architecture where a trusted service (the Guardian) holds secrets and provides them only to authorized tools, never to the agent itself.

## Who This Is For

**Security architects** evaluating whether an agentic system can be trusted with secrets. Start with the [Appendices](06-appendices/): they tell you what to look for, what to avoid, and how to assess risk.

**Platform engineers** building agentic systems that need to handle secrets. Read [Part 1: Foundations](01-foundations/) to understand the threat model, then [Part 3: Architecture](03-architecture/) for the design patterns.

**Standard authors and auditors** assessing conformance. [Part 2: Principles](02-principles/) defines the non-negotiables. [Part 5: Reference](05-reference/) has the cryptographic and audit requirements.

**Implementers** building protocol-level code. Start here for architecture, then see [Annex A](07-annexes/annex-a-protocol-details.md) for wire protocol, schemas, and example flows.

## How to Read This Standard

Prefer a single document? Read the [full specification](SAGA-Standard-20260217.md).

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   Evaluating a system? ──→ Appendices (Informative)             │
│                                                                 │
│   Building a system? ────→ Part 1 → Part 2 → Part 3 → Part 4   │
│                                                                 │
│   Implementing protocol? → Annex A (Informative)                │
│                            (wire protocol, schemas, flows)      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## The Core Idea in 60 Seconds

Traditional secrets management assumes the thing consuming the secret is the thing authorized to have it. In agentic systems, this breaks down:

```
Traditional:  Human → Application → Secret → API
              (same entity is authorized and consumes)

Agentic:      Human → Agent → Tool → Secret → API
              (agent decides, tool consumes, human authorizes)
```

This creates a **three-party trust problem**:

1. **Human principal** - owns the secrets, authorizes use
2. **Agent** - decides *what* to do, must never see secrets
3. **Tool** - does the actual work, needs the secrets

The standard solves this with a **Guardian service** that sits between tools and secrets, enforcing that:

- The agent never holds secrets (architectural isolation)
- Each tool can only access secrets it's scoped to (credential scoping)
- The human can approve, deny, or revoke access at any time (human oversight)
- Every access is logged (auditability)

## The Six Principles

1. **The agent never holds secrets** - Not through prompt engineering, not through careful instructions: through architecture.

2. **The human always retains control** - Override authority, revocation, inspection: always available, never circumvented.

3. **Access is scoped, not global** - A tool authorized for one profile cannot access any other.

4. **Write-back is first-class** - OAuth tokens expire. Secrets rotate. Updates flow through the same mediated channel.

5. **Every access is auditable** - Who accessed what, when, from where, with what approval.

6. **Works in any runtime** - No language requirements, no framework dependencies, standard primitives.

## The Four Autonomy Tiers

| Tier | Read Approval | Write Approval | Use Case |
|------|---------------|----------------|----------|
| **0: Supervised** | Every access | Every access | Production, compliance-heavy |
| **1: Session-Trusted** | Once per session | Follows read | Development, interactive (recommended) |
| **2: Tool-Autonomous** | Automatic | Selective/automatic | CI/CD, services |
| **3: Full Delegation** | Automatic | Automatic | Trusted internal, with compensating controls |

## Directory Structure

```
SAGA-Standard/
├── README.md                           (you are here)
├── SAGA-Standard-20260217.md           (single-page rendered spec)
├── 00-foreword.md
│
├── 01-foundations/
│   ├── 01-introduction.md              The credential problem in agentic AI
│   ├── 02-scope.md                     What's in and out of scope
│   ├── 03-threat-model.md              Threat actors, scenarios, boundaries
│   └── 04-core-concepts.md             Terms and mental model
│
├── 02-principles/
│   ├── 05-design-principles.md         The six non-negotiable principles
│   ├── 06-trust-boundaries.md          Three mandatory security boundaries
│   └── 07-autonomy-tiers.md            When to use which tier
│
├── 03-architecture/
│   ├── 08-secret-profiles.md           Profiles, entries, classification
│   ├── 09-access-control.md            Token model and scoping
│   ├── 10-approval-policies.md         Read/write approval, sessions
│   ├── 11-secret-lifecycle.md          Write-back, OAuth, rotation
│   └── 12-delegation.md                Inter-agent and cross-system
│
├── 04-conformance/
│   └── 13-conformance.md               Conformance levels
│
├── 05-reference/
│   ├── 14-cryptographic-requirements.md
│   ├── 15-audit-observability.md
│   └── 16-relationship-to-standards.md
│
├── 06-appendices/                       (Informative)
│   ├── appendix-a-evaluation-criteria.md  What to look for, red flags
│   ├── appendix-b-compensating-controls.md  When you can't do it perfectly
│   └── appendix-c-anti-patterns.md        Common failures and why
│
└── 07-annexes/                          (Informative)
    └── annex-a-protocol-details.md      Wire protocol, schemas, flows
```

> **Note:** Wire protocol, schema definitions, example flows, and reference architecture are provided in [Annex A](07-annexes/annex-a-protocol-details.md) (Informative).

## Contributing

This is an open standard in early draft. Feedback, corrections, and contributions are welcome.

**How to participate:**

1. **Open an issue** — Found a gap, inconsistency, or have a suggestion? [Open an issue](https://github.com/Stonefish-Labs/saga-standard/issues) describing the problem or proposal.
2. **Submit a pull request** — For editorial fixes, clarifications, or proposed normative changes, fork the repo and open a PR against `main`.
3. **Join the discussion** — Use [GitHub Discussions](https://github.com/Stonefish-Labs/saga-standard/discussions) for broader questions, implementation experience, or design conversations.

**Contribution guidelines:**

- Reference specific section numbers (e.g., "Section 9, Access Control") when filing issues.
- For normative changes, explain the security rationale — why the current text is insufficient and what threat the change addresses.
- Editorial PRs (typos, formatting, cross-reference fixes) are always welcome and will be merged quickly.
- Use RFC 2119 keywords (`MUST`, `SHOULD`, `MAY`, etc.) correctly per [BCP 14](https://www.rfc-editor.org/rfc/rfc2119) when proposing normative text.

## Building the Single-Page Version

```bash
python build.py
```

This generates `SAGA-Standard-20260217.md` with all sections concatenated and a table of contents.

## Version

**Identifier:** SAGA-2026-01  
**Status:** Working Draft  
**Date:** 2026-02-17

## License

Creative Commons Attribution 4.0 International (CC BY 4.0). Share and adapt freely with attribution.
