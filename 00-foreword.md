# Secret Access Governance for Agents (SAGA)

## Foreword

### Abstract

Autonomous AI agents accomplish tasks by invoking tools and services that require secrets -- API keys, OAuth tokens, cryptographic keys, and other credentials. The agent decides which operations to perform, but it cannot be trusted with the secrets those operations require: its behavior is non-deterministic, susceptible to prompt injection, and not formally verifiable. Yet the tools it drives need real credentials to do real work.

This standard defines an architectural framework for governing how agents obtain mediated access to secrets on behalf of a human principal. A trusted intermediary -- the Guardian -- holds secrets, enforces human-authorized access policies, and delivers credentials exclusively to authorized tools. The agent orchestrates; it never holds secret values. The human principal retains authority to approve, deny, inspect, revoke, and audit all secret access at any time.

Secret access is the first and most critical domain of a broader problem: how principals delegate sensitive capabilities to autonomous agentic systems under governed, auditable, revocable terms. The three-party model and mediation architecture defined here are designed to extend to other domains of governed capability delegation as the agentic ecosystem matures.

### Document Status

| Attribute | Value |
|-----------|-------|
| **Standard Identifier** | SAGA-2026-01 |
| **Version** | 1.0 Working Draft |
| **Status** | Solo Working Draft — Pre-Review |
| **Date** | 2026-02-17 |
| **Author** | Solo draft, not yet submitted to any working group or standards body |

#### Status of This Document

This is a solo working draft produced prior to any external review or working group formation. It has not been submitted to any standards body and does not carry the endorsement of any organization. The document is published for early feedback and is expected to change substantially before any formal standardization process.

Comments and contributions are welcome. See [How to Contribute](#how-to-contribute).

### Document Conventions

The key words "MUST", "MUST NOT", "REQUIRED", "SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "NOT RECOMMENDED", "MAY", and "OPTIONAL" in this document are to be interpreted as described in BCP 14 [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174) when, and only when, they appear in capitalized form, as shown here.

This foreword is entirely informative. Normative requirements begin in [Part 1: Foundations](part-1-foundations/01-introduction.md).

### How to Contribute

This is an open standard in early draft. Contributions, comments, and implementations are welcome.

- **Issues and proposals:** [github.com/Stonefish-Labs/saga-standard/issues](https://github.com/Stonefish-Labs/saga-standard/issues)
- **Pull requests:** Fork the repository and submit against `main`
- **Discussion:** [github.com/Stonefish-Labs/saga-standard/discussions](https://github.com/Stonefish-Labs/saga-standard/discussions)

### Acknowledgments

This standard was developed through threat modeling and iterative design informed by practical experience building secret isolation for AI agents that invoke tools, MCP servers, and external services.

The standard draws on work by:

- **Risk taxonomy:** OWASP Agentic Security Initiative -- identifies the risks this standard mitigates architecturally
- **Adjacent standardization:** IETF OAuth Working Group discussions on AI agent identity; NIST CAISI request for information on agentic system security
- **Operational experience:** Production deployments of agentic systems in enterprise environments

### Revision History

| Version | Date | Changes |
|---------|------|---------|
| 1.0-wd | 2026-02-17 | Working draft. Developed through iterative design including transport agnosticism, multi-part restructuring, service-mediated access principles, expanded threat model, and practitioner guidance. Renamed from AACS/ASMS to SAGA to reflect standard scope: secret access governance for agentic systems. |

### License

This standard is released under the Creative Commons Attribution 4.0 International License (CC BY 4.0).

You are free to:
- **Share** -- copy and redistribute the material in any medium or format
- **Adapt** -- remix, transform, and build upon the material for any purpose, including commercially

Under the following terms:
- **Attribution** -- You must give appropriate credit, provide a link to the license, and indicate if changes were made

---

*This is an open standard. The goal is not to prescribe a single implementation, but to establish principles and architectural patterns that govern how agentic systems obtain mediated access to secrets -- ensuring human principals retain authority over which tools receive which credentials, and that the agent reasoning layer never holds secret values. Wire-level implementation details, JSON schemas, example flows, and reference architectures are provided in [Annex A](annexes/annex-a-protocol-details.md) (Informative).*
