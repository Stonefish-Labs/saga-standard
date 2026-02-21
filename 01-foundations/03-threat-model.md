# 3. Threat Model

A robust threat model is essential for understanding why the architectural controls in this standard exist. This section defines the threat actors, scenarios, and security boundaries that the standard addresses.

## 3.1 Threat Actors

This standard considers three categories of threat actors, operating against a defined trust hierarchy:

| Entity | Trust Level | Rationale |
|--------|-------------|-----------|
| **Human Principal** | Trust anchor | Owns secrets, authorizes use, retains override authority |
| **Guardian** | Trusted | Process-isolated mediator; holds encryption keys, enforces policy |
| **Tools** (authorized, within scope) | Semi-trusted | Receive secrets within authorized scope; not trusted beyond it. The classification is based on verifiable properties — authorization and scope confinement — not on an unverifiable assertion of benign intent |
| **Tools** (compromised) | Untrusted (T2) | Actively malicious; may attempt lateral access or exfiltration |
| **Agent** | Untrusted (T1) | Primary threat actor; may misbehave through injection, emergent behavior, or misinterpretation |
| **Guardian** (compromised) | Untrusted (T4) | Software supply-chain compromise or binary backdoor; holds master key, all tokens, audit record |

### T1: The Agent Itself

The LLM reasoning loop is treated as an untrusted party by design. This is not because the model is malicious, but because:

- **Non-deterministic behavior:** Model outputs cannot be formally verified
- **Prompt injection:** Attacks can cause the model to take unintended actions
- **Observable outputs:** Model outputs may be logged, cached, or transmitted to third parties
- **Future uncertainty:** Model versions may have different safety properties

> **The agent is the primary threat actor in this model.** This is the core assumption that drives all architectural decisions.

#### Relationship to Established Threat Disciplines

The agent threat profile borrows from two well-understood security disciplines without fitting cleanly into either:

- **Insider threat.** The security community has decades of research on trusted insiders who go rogue. However, the traditional insider threat model assumes a *human* actor with existing access who makes a deliberate choice to misuse it. An agent is not deliberate: it may misbehave due to prompt injection, emergent behavior, or simple misinterpretation. The intent is absent, but the capability is identical.

- **Malicious code detection.** Conventional malware analysis assumes code that was *not intended* to run on the system. An agent is the opposite: it is code you *invited in* and *granted execution privileges to* as a feature. Modern agents routinely have access to the filesystem, the terminal, and the ability to write and execute arbitrary code. These are foundational capabilities that make them useful. They are also the exact capabilities that allow a misbehaving agent to read files, search for credentials, write exfiltration scripts, and execute them: functionally indistinguishable from a malicious insider with developer-level access.

The agent is a new category: an entity you trust with *action* but cannot trust with *access*. Neither insider threat frameworks nor malicious code detection frameworks were designed for an actor that is simultaneously invited, privileged, and unverifiable. This is why the standard treats the agent as the primary threat actor and relies on architectural isolation rather than behavioral controls.

### T2: Malicious Tools

A tool may become malicious through supply-chain attacks (dependency confusion, compromised package registries, malicious updates), intentional backdoors by the tool author, or runtime compromise of the tool process. The standard addresses the *consequences* of tool compromise, what a malicious tool can do once it has access, while acknowledging that supply-chain integrity and tool provenance verification are complementary concerns (see §3.4, Accepted Risks).

A compromised MCP server could:

- Attempt to read secrets from profiles it shouldn't access
- Escalate its access to other tools' secrets
- Exfiltrate secret values through side channels
- Write poisoned values to another tool's profile

### T3: Infrastructure Attackers

Standard external attackers who gain access to the filesystem, network, or process space through conventional vulnerabilities. The standard addresses the subset of infrastructure attacks that target secret storage and mediation.

### T4: Compromised Guardian Software

The Guardian binary itself may be compromised through supply-chain attack (malicious dependency, compromised build pipeline), a vulnerability exploited in the Guardian's IPC parsing or storage layer, or a malicious update to the Guardian package. Unlike T1–T3, a compromised Guardian can bypass all architectural controls silently, because all access decisions, key operations, and audit writes flow through it.

**Why this is the most catastrophic threat:**

The Guardian holds the master encryption key (KEY-7), derives all delegation signing keys from it (SIG-2), makes all access authorization decisions, and writes all audit entries. A backdoored Guardian can exfiltrate all secrets without generating any audit event the human principal would see, because it controls the audit log. The three-party model's security guarantees depend on the Guardian being trustworthy; T4 represents a failure of that foundational assumption.

**Trusted Computing Base (TCB) definition:**

The Guardian TCB includes: the Guardian binary and all dynamically linked libraries, the OS process scheduler and memory management, the OS-provided IPC primitives (Unix domain sockets or TCP/TLS stack), the key storage subsystem (OS keychain, HSM, or encrypted file), and all cryptographic keys held by the Guardian — specifically: KEY-1 (master encryption key), KEY-2 (key-encryption key for DEK wrapping), KEY-7 (key encryption key for at-rest secrets), SIG-1 (integrity key), SIG-2 (delegation signing key), and any other key material defined in [§14 Cryptographic Requirements](../05-reference/14-cryptographic-requirements.md). Implementers must ensure that the full set of §14-defined key material is within the TCB boundary when sizing OS-level security controls.

**Guardian TCB verification requirements (by conformance level):**

| Level | Requirement | Rationale |
|-------|-------------|-----------|
| **Level 1** | Human principals **SHOULD** verify the Guardian TCB before deployment: (a) obtain the Guardian binary from a verified source channel (e.g., signed release artifact with verifiable signature); (b) verify the binary signature against the publisher's public key; (c) review or obtain a Software Bill of Materials (SBOM) for the Guardian's dependencies. The deployment's verification posture **MUST** be acknowledged in the conformance statement | Level 1 deployments are explicitly development and low-risk contexts; binary verification is strongly advised but not a hard conformance gate at this level |
| **Level 2** | All Level 1 steps are **MUST**, not SHOULD. The conformance statement **MUST** document the specific binary source channel and the verification mechanism used | Level 2 production deployments require attestable verification; "SHOULD" is insufficient for environments with real secret values |
| **Level 3** | All Level 2 requirements apply. Binary signature verification **MUST** be incorporated into the deployment pipeline (e.g., a CI/CD verification step that gates Guardian startup). Reproducible builds are **RECOMMENDED**. The conformance statement **MUST** include the verification mechanism and a link to or description of the pipeline step | Level 3 high-value deployments require verifiable, repeatable binary integrity assurance, not a one-time manual check |

**Mitigations:** Binary signing verification (SHOULD at Level 1, MUST at Level 2, MUST-with-pipeline at Level 3), SBOM review, remote audit log replication to an independent system the Guardian cannot modify, dependency pinning and security advisory monitoring.

## 3.2 Threat Scenarios

| ID | Scenario | Actor | Likelihood | Impact | Mitigated By |
|----|----------|-------|------------|--------|--------------|
| TS-1 | Agent extracts secret from tool output | T1 | High | Secret exposure in model context | §5.2 Minimal Disclosure, tool output sanitization |
| TS-2 | Agent instructs tool to send secret to attacker endpoint | T1 | High | Secret exfiltration | Boundary 1, scoped access |
| TS-3 | Prompt injection causes agent to access unintended profile | T1 | High | Unauthorized secret access | Boundary 3, approval attestation |
| TS-4 | Compromised tool reads secrets for unauthorized profiles | T2 | Medium | Lateral secret access | Boundary 2, credential scoping |
| TS-5 | Malicious tool writes poisoned values to another profile | T2 | Medium | Secret integrity attack | Boundary 2, write policies |
| TS-6 | Tool extracts encryption key from shared process memory | T2 | Low | Complete secret store compromise | Boundary 1, process isolation |
| TS-7 | Attacker reads encrypted secret storage from disk | T3 | Low | Offline secret recovery | Crypto requirements, key separation |
| TS-8a | Attacker connects to Guardian via local socket from unauthorized process | T3 | Low | Secret access bypass | UDS permissions (§6.1, PROC-1/PROC-2/UDS-1 through UDS-3), token auth |
| TS-8b | Attacker connects to Guardian via network transport | T3 | Medium | Secret access bypass | TLS mutual auth (§6.4), token auth, network ACLs |
| TS-9 | Malicious process displays fake approval dialog | T3 | Medium | Social engineering | Verification codes (§4.4) |
| TS-10 | Tool updates OAuth token with malicious value | T2 | Medium | Token substitution | Write policies, audit |
| TS-11 | Agent accumulates secrets across sessions via write-back | T1 | Medium | Progressive harvesting | Audit, session limits |
| TS-12 | Cascading agent delegation causes unaudited access | T1, T2 | Medium | Loss of audit trail | Delegation controls |
| TS-13 | Shared service retains credential beyond authorized scope | T2 | Medium | Persistence beyond intent | Delegation principles |
| TS-14 | Shared service escalates credential to unauthorized resources | T2 | Medium | Privilege escalation | Scope attenuation |
| TS-15 | Agent creates or substitutes a tool to intercept secrets | T1 | High | Secret exfiltration via agent-authored code | Tool provenance, Guardian token binding |
| TS-16 | Agent socially engineers human into approving unintended access | T1 | High | Unauthorized secret access via deceptive context | Approval dialog content requirements, request-context binding |
| TS-17 | Agent exploits approval fatigue through rapid or batched requests | T1 | Medium | Gradual scope escalation | Rate limiting, escalating scrutiny controls |
| TS-18 | Attacker obtains valid token via memory, logs, or network interception | T3 | Medium | Unauthorized secret access via token replay | Token TTL, transport encryption, audit |
| TS-19 | Supply-chain attack or vulnerability in Guardian binary introduces backdoor or key exfiltration capability | T4 | Low | Total secret store and audit log compromise; all architectural controls bypassed | Binary signing verification, SBOM review, remote audit log replication, reproducible builds |
| TS-20 | In multi-principal Guardian deployments, one principal's agent accesses another principal's profiles through namespace collision or token confusion | T1, T3 | Medium | Unauthorized cross-principal secret access | Principal namespace isolation (NS-1 through NS-4 in [§4.2](04-core-concepts.md#42-core-terms)): per-principal namespaces (NS-1), profile name uniqueness within namespace (NS-2), namespace-bound token scoping (NS-3), no implicit cross-namespace access (NS-4) |
| TS-21 | Agent reads MCP client configuration to discover tool server filesystem paths, then tampers with or replaces the server binary or source in place | T1 | High | Tool integrity compromise; secrets exfiltrated through a trusted, registered tool identity | Network-isolated tool servers, code signing with runtime verification, configuration path isolation (§3.5.4) |
| TS-22 | Attacker or compromised agent intercepts or replays approval channel tokens (Slack OAuth, Teams webhook, HMAC callback secrets) to forge approval responses | T1, T3 | Medium | Unauthorized secret access via forged approval on out-of-band channel | Hardware-bound second factor (FIDO2/WebAuthn), channel token rotation, approval binding to hardware attestation (§3.5.5) |

> **Likelihood definitions:** Likelihood assessments use the following operational scale: **High** — exploitable with widely available tools in common deployment environments, expected in targeted attacks; **Medium** — requires specific knowledge or access to the deployment environment, plausible in targeted attacks; **Low** — requires significant resources, insider access, or a chain of prior compromises.

> **Note on TS-1:** Boundary 1 (process isolation) prevents the agent from reading secrets in Guardian or tool memory. It does *not* prevent a tool from including secret values in its response to the agent. Mitigation of TS-1 relies on the Principle of Minimal Disclosure (§5.2) and tool-side output sanitization, both of which are behavioral controls on the tool. The standard acknowledges that once a tool holds a secret, it must be trusted to handle it properly within its authorized scope (see §3.4, Side-Channel Exfiltration).

> **Note on TS-15:** Modern agents routinely have filesystem and terminal access, including the ability to write and execute arbitrary code. An agent can create a script that mimics a legitimate tool's interface, invoke it, and use it to request secrets from the Guardian. If the agent can obtain or generate a valid token, the Guardian cannot distinguish the agent-authored tool from a legitimate one. Mitigation requires that tokens are bound to pre-registered tool identities and that the Guardian verifies tool provenance before honoring requests. See §3.5 for the full analysis.

> **Note on TS-16:** The approval dialog (§10.4) shows *what* is being accessed (profile name, entry keys) but not *why*. The agent controls the conversational context in which the human decides whether to approve. An agent, whether through prompt injection or emergent behavior, may describe an operation in misleading terms ("checking dev config") while actually requesting production credentials. The dialog is architecturally sound against forgery (TS-9) and interception (TS-3), but provides no defense against the human making an informed decision based on false context. See §3.5 for the full analysis.

> **Note on TS-21:** TS-15 addresses an agent *creating* a fake tool. TS-21 addresses a distinct and more dangerous variant: the agent *corrupting an existing trusted tool* by reading MCP client configuration files (e.g., `.cursor/mcp.json`, `claude_desktop_config.json`, VS Code `settings.json`) to discover filesystem paths to MCP server binaries or source code, then modifying them in place. Because the tool identity (path, registration entry) is unchanged, TS-15 mitigations such as tool registration and process attestation do not detect the compromise — the Guardian verifies the path it already trusts. The agent does not need root access; normal user-level filesystem permissions on typical developer workstations are sufficient. See §3.5.4 for the full analysis.

> **Note on TS-22:** Boundary 3 requires that approval use a channel the agent cannot intercept or forge. Out-of-band channels (Slack, Teams, PagerDuty) satisfy the *channel independence* property — the agent cannot directly interact with them. However, these channels authenticate approvals using software tokens: OAuth tokens, webhook signing secrets, HMAC callback keys. These tokens exist as data and can be stolen through filesystem access, memory inspection, log exposure, or network interception. An attacker who obtains the channel token can forge approval responses without the human principal's involvement. Software-only approval channels are therefore vulnerable to token replay regardless of how well the channel itself is isolated from the agent. See §3.5.5 for the full analysis.

## 3.3 Security Boundaries

This standard defines three mandatory security boundaries. An implementation **MUST** enforce all three boundaries to claim conformance at any level (see [Conformance](../04-conformance/13-conformance.md) for level-specific requirements). The mechanisms used to satisfy each boundary may vary by conformance level, but the security properties they provide are invariant.

### Boundary 1: Process Isolation (Agent / Guardian)

The agent reasoning loop and the Guardian service MUST execute in separate processes with separate address spaces.

```
┌─────────────────┐         ┌─────────────────┐
│     Agent       │         │    Guardian     │
│  (Untrusted)    │         │   (Trusted)     │
│                 │   IPC   │                 │
│  No secrets     │◄───────►│  Master key     │
│  No key access  │         │  Secret store   │
└─────────────────┘         └─────────────────┘
    Process A                   Process B
    Address Space               Address Space
```

**What this prevents:**
- TS-6: Agent cannot extract encryption keys from Guardian memory
- TS-15: Combined with token storage isolation, limits the agent's ability to create tools that impersonate legitimate ones

**Implementation requirements:**

Implementations **MUST** ensure all of the following:
- Agent and Guardian execute as separate OS processes with separate address spaces
- No shared memory regions between agent and Guardian processes
- No shared file descriptors between agent and Guardian processes
- No shared encryption keys: the agent **MUST NOT** have access to the Guardian's encryption keys or any key material used for secret encryption or integrity verification

**Failure mode:** If the Guardian process becomes unavailable, all secret access **MUST** be denied. The agent **MUST NOT** fall back to direct storage access, cached secrets, or any alternative retrieval mechanism. See [Design Principles §5.5](../02-principles/05-design-principles.md) (Degradation Toward Safety).

### Boundary 2: Secret Scoping (Tool A / Tool B)

Each tool invocation receives only the secret profile(s) it is authorized to access.

```
┌─────────────────┐         ┌─────────────────┐
│     Tool A      │         │     Tool B      │
│                 │         │                 │
│  Token scoped   │         │  Token scoped   │
│  to aws-prod    │         │  to stripe-live │
│                 │         │                 │
│  ✗ Cannot access│         │  ✗ Cannot access│
│    stripe-live  │         │    aws-prod     │
└────────┬────────┘         └────────┬────────┘
         │                           │
         ▼                           ▼
    ┌─────────────────────────────────────┐
    │             Guardian                 │
    │                                      │
    │  Enforces: one token → one profile  │
    └─────────────────────────────────────┘
```

**What this prevents:**
- TS-4: Compromised tool cannot access other profiles
- TS-5: Malicious tool cannot poison other profiles
- TS-18: Token theft is contained to one profile's scope

**Implementation requirements:**

Implementations **MUST** ensure all of the following:
- Every token **MUST** be scoped to exactly one profile
- The Guardian **MUST** verify the token on every request: no cached authorization decisions
- Wildcard tokens, cross-profile tokens, and any mechanism that grants access to multiple profiles with a single credential are prohibited

### Boundary 3: Approval Attestation (System / Human)

The approval mechanism must use a channel that the agent cannot intercept or forge.

```
┌─────────────────┐         ┌─────────────────┐
│     Agent       │         │  Human User     │
│                 │         │                 │
│  Cannot see     │         │  Approves via   │
│  approval dialog│         │  native OS UI   │
│  Cannot forge   │         │                 │
│  verification   │         │  Verifies code  │
└─────────────────┘         └─────────────────┘
                                    │
                                    ▼
                             ┌─────────────────┐
                             │    Guardian     │
                             │                 │
                             │ Spawns dialog   │
                             │ Verifies code   │
                             └─────────────────┘
```

**What this prevents:**
- TS-3: Agent cannot bypass approval through prompt injection
- TS-9: Attacker cannot spoof approval through fake dialog
- TS-16: Approval dialog content is Guardian-authoritative, not agent-influenced (see §3.5.2)
- TS-17: Rate limiting and escalating scrutiny resist approval fatigue (see §3.5.3)
- TS-22: Hardware-bound approval factors resist approval channel token theft (see §3.5.5)

**Implementation requirements:**

The core security property of Boundary 3 is that the approval channel **MUST** use a mechanism the agent cannot intercept, forge, or influence. The mechanism varies by conformance level:

- At **Level 2 and above**, approval **MUST** use an agent-independent channel: native OS dialogs, authenticated out-of-band services (Slack, Teams, PagerDuty — each requiring hardware-attested approval responses per [OOB-4](../03-architecture/10-approval-policies.md#106-out-of-band-approval)), MFA-gated web dashboards with hardware second factor, or hardware-attested out-of-band approval (see [§6.3 DLG-1](../02-principles/06-trust-boundaries.md#63-boundary-3-approval-attestation-human--guardian) for the channel independence property, [§10.6](../03-architecture/10-approval-policies.md#106-out-of-band-approval) for hardware attestation requirements, and [§4.4](04-core-concepts.md) for verification code format and properties)
- At **Level 1**, terminal-based approval is permitted provided the agent process has no access to the approval terminal's input stream (see [Conformance §13.2](../04-conformance/13-conformance.md#132-level-1-basic))
- The default action for any approval request **MUST** be "Deny"
- Approval dialog content **MUST** be generated by the Guardian from its own authoritative records: profile name, entry keys, sensitivity flags. The dialog **MUST NOT** include any text originating from the agent or the agent's conversation. Tool-originated context (e.g., operation description, stack trace) **MAY** be included if submitted through the tool's authenticated Guardian session and not relayed through the agent (see DLG-11)
- The complete list of entry keys **MUST** be displayed without truncation (see §3.5.2, TS-16 mitigations)

**Level 1 terminal approval — required OS isolation mechanism:**

At Level 1, terminal-based approval is permitted only when the agent process operates under a different OS user credential than the terminal receiving approval input, OR when the approval terminal is a physically distinct session boundary (a separate TTY with distinct user credentials, a different OS desktop session, or a hardware terminal). Implementations MUST document in their conformance statement the specific OS mechanism enforcing this isolation. Asserting "the agent cannot access the terminal" is not conformance evidence; the specific OS credential separation mechanism is. If no qualifying mechanism can be specified, terminal-based approval is not conformant at Level 1, and the implementation MUST use an agent-independent channel as required at Level 2.

## 3.4 Accepted Risks

No security architecture is complete. This standard explicitly accepts the following risks as out of scope for architectural mitigation:

### Process Memory Inspection

If an attacker can read arbitrary memory from the tool's process (e.g., through a debugger, `/proc/mem`, or a memory corruption vulnerability), secrets in that tool's address space are exposed.

**Why accepted:**
- Any process that uses a secret must, at some point, hold it in memory
- Memory encryption/scrubbing provides marginal benefit against process-level access
- The countermeasure adds complexity without meaningfully changing the attack surface

**Mitigation:** Boundary 1 (process isolation) and Boundary 2 (credential scoping) limit the blast radius to one tool's authorized profiles.

### Compromised Operating System

This standard assumes a trusted kernel on every machine where a conformant component executes. Kernel-level compromise of a machine defeats all user-space security controls on that machine.

**Why accepted:**
- Kernel-level compromise defeats virtually all user-space security on the affected host
- This is a foundational assumption of most security architectures
- Mitigation is outside the scope of application-level standards

**Critical nuance, co-located vs. remote Guardian:**

The blast radius of a compromised OS depends entirely on **where the Guardian runs relative to the agent**:

| Deployment | OS compromise of agent host | Impact |
|------------|----------------------------|--------|
| **Co-located** (Guardian on same machine as agent) | Attacker can read Guardian process memory, access encryption keys, decrypt secret storage directly | **Total compromise**: all secrets exposed |
| **Remote** (Guardian on separate machine) | Attacker can read tool process memory on the agent host, but cannot reach Guardian memory, encryption keys, or secret storage | **Scoped compromise**: only secrets currently held in tool memory on the compromised host are exposed; Guardian encryption keys and secret storage remain protected on the remote host |

This is not a theoretical distinction. In enterprise deployments, agents routinely run on developer workstations, CI/CD runners, or container orchestration nodes, all of which have elevated compromise risk relative to hardened infrastructure. A remote Guardian on dedicated, hardened infrastructure means that compromising the agent's host does not compromise the secret store.

**Recommendation:** Deployments where agent host compromise is a realistic threat **SHOULD** use a remote Guardian (see §3.6, Guardian Deployment Topology). The standard's transport bindings (TCP/TLS, mTLS at Level 2+) and cross-system access requirements (§12.4) already support this architecture. Co-located deployment is appropriate for development, testing, and environments where the agent host is as well-protected as any other infrastructure component.

### Side-Channel Exfiltration

If a tool intentionally leaks secrets through side channels (encoding in DNS queries, timing attacks, writing to logs), the standard cannot prevent this.

**Why accepted:**
- Once a tool receives a secret, it must be trusted to use it properly
- Technical controls cannot prevent all intentional misuse

**Mitigation:**
- Credential scoping (limit blast radius)
- Audit logging (detect patterns post-hoc)
- Tool provenance verification (only run trusted tools)

### Guardian Binary Integrity

A tampered Guardian binary could bypass all three security boundaries, forge audit entries, and exfiltrate all secrets without detection through any mechanism defined in this standard. Binary integrity verification cannot be enforced by the Guardian's own protocol controls — the architecture cannot validate itself. Guardian binary integrity is therefore a **partially mitigated risk**: fully mitigated at Level 2 and above through mandatory verification requirements (§3.1 T4); residual risk acknowledged at Level 1 where verification is SHOULD, not MUST.

**Why this risk cannot be fully eliminated architecturally:**
- Binary integrity verification is a deployment-time and supply-chain concern. There is no protocol mechanism by which the Guardian can prove its own binary authenticity to callers — this is a bootstrapping problem analogous to the kernel trust assumption
- The standard cannot enforce binary integrity on the Guardian itself through the same controls the Guardian implements; the TCB verification requirements in §3.1 are deployment obligations on the human principal, not protocol enforcement mechanisms

**Risk by level:**

| Level | Residual risk status | Mitigation requirements |
|-------|---------------------|------------------------|
| **Level 1** | Partially mitigated (SHOULD posture). Binary integrity compromise is possible if verification is skipped | Verify binary source and signature per §3.1 T4; acknowledge posture in conformance statement |
| **Level 2** | Substantially mitigated. MUST posture closes the gap for standard production deployments | MUST verify; document mechanism in conformance statement; replicate audit logs to an independent system |
| **Level 3** | Substantially mitigated with pipeline enforcement. Residual risk is supply-chain attack on the verification toolchain itself | MUST incorporate verification in deployment pipeline; reproducible builds RECOMMENDED; SIEM-replicated audit logs required |

**Mitigation:** Binary signing verification (level-tiered per §3.1 T4), SBOM review, real-time audit log replication to an independent system outside the Guardian's write access (see §15.5), dependency pinning and security advisory monitoring.

## 3.5 Agent-Initiated Attack Surfaces

The following attack surfaces deserve expanded treatment because they exploit the agent's unique position in the architecture: it is invited, privileged with execution capabilities, and controls the conversational context in which humans make approval decisions. These are not hypothetical: they follow directly from the capabilities that make modern agents useful.

### 3.5.1 Tool Substitution (TS-15)

**Attack:** The agent writes a script or program that mimics a legitimate tool's interface, then invokes it instead of (or alongside) the real tool. The agent-authored tool requests secrets from the Guardian using an available token, then returns the secret values to the agent through its output.

```
┌─────────────────┐     writes & executes      ┌─────────────────┐
│     Agent       │ ──────────────────────────► │  Fake Tool      │
│  (Untrusted)    │                             │  (agent-authored)│
│                 │ ◄── secret in output ────── │                 │
└─────────────────┘                             └────────┬────────┘
                                                         │ valid token
                                                         ▼
                                                ┌─────────────────┐
                                                │    Guardian     │
                                                │  (cannot        │
                                                │   distinguish)  │
                                                └─────────────────┘
```

**Why this is dangerous:**

Modern agents with filesystem and terminal access can:
1. Read the source code of existing tools to understand the Guardian protocol
2. Write a new tool that implements the same protocol
3. Obtain a valid token from the tool's environment, filesystem, or configuration
4. Execute the fake tool and receive secrets in its output
5. Exfiltrate the secrets through the agent's own output channels

The Guardian enforces token authentication and profile scoping, but it has no mechanism to verify *which binary or script* is presenting the token. A valid token from a valid process owned by the correct user is indistinguishable from a legitimate request.

**Mitigations:**

| Mitigation | Level | Description |
|------------|-------|-------------|
| Token storage isolation | MUST | Tokens **MUST NOT** be stored in locations readable by the agent process. Prohibited storage locations include: environment variables inherited by the agent process, configuration files or working directory files the agent process can read, and any filesystem path accessible under the agent's OS user credentials. Conformant implementations MUST specify in their conformance statement the storage mechanism used for tokens and demonstrate it is inaccessible to the agent process. See Anti-Pattern 1. |
| Tool registration | SHOULD | Implementations **SHOULD** support a tool registration mechanism where the Guardian maintains a list of authorized tool identities (binary hash, path, or code-signing certificate) and refuses requests from unregistered tools. |
| Process attestation | MAY | At Level 3, implementations **MAY** verify the requesting process's binary identity (e.g., via code signing or `/proc` inspection on Linux) before honoring token-based requests. |
| Token delivery channel | SHOULD | Tokens **SHOULD** be delivered to tools through a channel the agent cannot observe: for example, injected into the tool's environment by the Guardian at launch time, rather than passed through the agent's invocation. |

> **Residual risk:** If the agent has root-equivalent access or can modify the tool binary itself, tool registration and process attestation can be bypassed. This falls under the Accepted Risk of Compromised Operating System (§3.4).

### 3.5.2 Approval Social Engineering (TS-16)

**Attack:** The agent provides misleading conversational context to trick the human into approving a request the human would deny if they understood the true intent. The approval dialog is architecturally sound: agent-independent channel (native OS window, trusted communication platform, or other conformant mechanism), verification codes, unforgeable by the agent. But the human's *decision* is based on information the agent controls.

**Example scenarios:**

**Scenario A: Mislabeled intent:**
```
Agent to user:  "I'll check the dev environment config to verify the deployment."
Agent requests:  profile "aws-production"
Dialog shows:    Profile: aws-production
                 Token: deploy-bot (a1b2c3d4)
User thinks:     "Agent said dev, dialog says production, but maybe
                 the production profile contains dev config?"
User approves:   Production credentials exposed.
```

**Scenario B: Buried request:**
```
Agent performs 6 legitimate operations in sequence.
Agent requests approval for routine profile (approved).
Agent requests approval for routine profile (approved).
Agent requests approval for high-value profile (approved: user is on autopilot).
```

**Scenario C: Obfuscated scope:**
```
Agent requests profile with entries: ["db_host", "db_user", "db_password",
    "admin_user", "admin_password", "admin_2fa_seed", "root_ca_key"]
Dialog shows (if truncated): "Entries: db_host, db_user, db_password, ..."
User sees: "database credentials": approves without scrolling.
Actually includes: admin credentials and CA private key.
```

**Why this is dangerous:**

This attack exploits a fundamental asymmetry: the standard's architectural controls protect the *mechanism* of approval (can't forge, can't intercept, can't auto-approve), but the *quality of the human's decision* depends on context the agent controls. The standard assumes the human will carefully read the dialog, but:

- Humans develop approval fatigue after repeated prompts
- Conversational context creates anchoring bias ("the agent said dev, so this must be fine")
- Entry lists may be too long to review meaningfully
- Profile names may not clearly convey risk level

**Mitigations:**

| Mitigation | Level | Description |
|------------|-------|-------------|
| Complete entry display | MUST | Approval dialogs **MUST** display the complete list of entry keys being requested. Truncation is prohibited. If the list is long, the dialog **MUST** use scrolling or pagination, not ellipsis. (Elevates DLG-4 from SHOULD to MUST.) |
| Sensitivity indicators | MUST | Each entry in the approval dialog **MUST** display its sensitivity classification. Entries marked `sensitive=true` **MUST** be visually distinguished (e.g., icon, color, label). |
| Risk-level summary | SHOULD | The approval dialog **SHOULD** display a summary risk indicator based on the profile's approval policy and the sensitivity of requested entries (e.g., "This profile is configured for prompt_always: 3 of 5 entries are marked sensitive"). |
| Rate limiting | SHOULD | Implementations **SHOULD** enforce configurable rate limits on approval requests. After N approvals within a time window, subsequent requests **SHOULD** require an escalated confirmation (e.g., re-entering a PIN or waiting a mandatory delay). |
| Approval context logging | MUST | The audit log **MUST** record the full list of entries requested in each approval, the approval method, and the time between request and approval. Rapid approvals (< 2 seconds) **SHOULD** be flagged for review. |
| No agent context in dialog | MUST | The approval dialog **MUST NOT** display any text originating from the agent or the agent's conversation. All Guardian-authoritative content (profile name, entry keys, sensitivity flags) **MUST** be generated by the Guardian from its own records. Tool-originated context **MAY** be displayed if it meets the conditions in DLG-11: authenticated tool session, no agent relay, and visually distinguished labeling. |

> **Design note:** The "no agent context" requirement prevents the primary threat actor (T1) from controlling the human's decision-making input. If the dialog includes a "reason" field populated by the agent, the agent controls the narrative. However, tool-originated context is categorically different: tools are semi-trusted (they hold secrets within authorized scope), and if a tool submits operational context (a stack trace, a deployment target, a request reason) through its own authenticated Guardian session — not relayed through the agent — that context improves the human's decision quality without giving the agent a manipulation vector. The Guardian **MUST** verify that tool-originated text arrived through the tool's token-authenticated channel (not through the agent's request) and **MUST** visually distinguish it from Guardian-authoritative content so the human knows the provenance. If the implementation cannot verify the provenance of submitted context, it **MUST NOT** display it.

### 3.5.3 Approval Fatigue Exploitation (TS-17)

**Attack:** The agent deliberately generates a high volume of approval requests, mixing legitimate low-risk requests with high-risk ones, to exhaust the human's attention and induce rubber-stamping.

**Why this is a distinct threat:**

TS-16 addresses a single deceptive request. TS-17 addresses the *pattern* of requests over time. Even with perfect dialog content (complete entry lists, sensitivity indicators, no agent-originated text), humans degrade in vigilance over repeated prompts. This is well-documented in security research on alert fatigue.

**Mitigations:**

| Mitigation | Level | Description |
|------------|-------|-------------|
| Approval rate limiting | SHOULD | Implementations **SHOULD** enforce a maximum approval request rate (e.g., no more than 5 requests per 10-minute window per profile). Exceeding the rate **SHOULD** trigger a mandatory cooldown period. |
| Escalating confirmation | SHOULD | After a configurable number of approvals within a session, implementations **SHOULD** require escalated confirmation (e.g., re-entering a passphrase, biometric confirmation, or a mandatory 30-second delay before the Approve button becomes active). |
| Session approval audit | MUST | The audit log **MUST** record the sequence and timing of all approval requests within a session. Anomalous patterns (many requests in short succession, alternating low-risk and high-risk profiles) **SHOULD** trigger alerts. |
| Batch request visibility | SHOULD | If multiple profiles are requested in quick succession, implementations **SHOULD** present a consolidated view showing all pending requests, enabling the human to assess the aggregate scope rather than evaluating each request in isolation. |

### 3.5.4 Tool Server Corruption via Configuration Discovery (TS-21)

**Attack:** The agent reads MCP client configuration files to discover the filesystem paths of MCP server binaries or source code, then modifies the server in place. The corrupted server retains its original identity — same path, same registration, same process name — but now contains agent-injected logic that exfiltrates secrets, bypasses controls, or alters behavior.

```
┌─────────────────┐     reads config        ┌──────────────────────┐
│     Agent       │ ──────────────────────► │  ~/.cursor/mcp.json  │
│  (Untrusted)    │                          │  "server": "/home/   │
│                 │     discovers path       │   user/tools/mcp-    │
│                 │ ◄────────────────────── │   db/index.js"       │
└────────┬────────┘                          └──────────────────────┘
         │
         │  writes malicious code to /home/user/tools/mcp-db/index.js
         ▼
┌─────────────────┐                          ┌─────────────────┐
│  Corrupted Tool │  valid token, valid path │    Guardian     │
│  (trusted       │ ◄──────────────────────► │  (cannot        │
│   identity)     │                          │   distinguish)  │
└─────────────────┘                          └─────────────────┘
```

**Why this is distinct from TS-15:**

TS-15 assumes the agent creates a *new* tool from scratch and must somehow obtain a valid token and pass tool registration checks. TS-21 is worse in every dimension:

1. **No token acquisition needed.** The corrupted server already has its token or will receive one through normal channels at next launch.
2. **Tool registration is bypassed.** The binary path hasn't changed. If the Guardian maintains a list of authorized tool identities by path, the corrupted tool passes.
3. **Process attestation is bypassed** unless the implementation performs cryptographic signature verification on every launch, not just path matching.
4. **The attack requires only normal user permissions.** MCP client configuration files and the MCP server source/binaries they reference typically reside in the same user's home directory. The agent, running as that user, has read access to the config and write access to the server. This is not privilege escalation — it is normal filesystem access.

**Configuration files known to expose tool server paths:**

| Client | Configuration Path | Content |
|--------|-------------------|---------|
| Cursor | `.cursor/mcp.json` | Server command and args, including filesystem paths |
| Claude Desktop | `claude_desktop_config.json` | Server command, args, and environment variables |
| VS Code (Copilot) | `.vscode/settings.json` or workspace settings | MCP server configuration with command paths |
| Continue | `~/.continue/config.json` | MCP server entries with filesystem paths |

**Mitigations:**

| Mitigation | Level | Description |
|------------|-------|-------------|
| Network-isolated tool servers | SHOULD | Tool servers **SHOULD** run on separate infrastructure (container, VM, or remote host) and communicate with the agent exclusively over network transport. When the server binary is not on the agent's filesystem, the agent cannot modify it regardless of its permissions. This is the strongest mitigation. |
| Code signing with runtime verification | SHOULD | Tool server binaries or source **SHOULD** be cryptographically signed. The Guardian or a launch wrapper **SHOULD** verify the signature against a known public key before every launch. Unsigned or signature-mismatched servers **SHOULD** be refused. |
| Configuration path isolation | SHOULD | MCP client configuration files **SHOULD** be stored with restrictive permissions (readable only by the client process, not by the agent process) or in a location the agent cannot access. Implementations **SHOULD** document the OS mechanism enforcing this separation. |
| Immutable tool directories | SHOULD | Tool server installation directories **SHOULD** be read-only to the agent process. On systems where the agent and the user share OS credentials, this may require mounting the tool directory read-only or using OS-level mandatory access controls (SELinux, AppArmor, macOS sandboxing). |
| Launch-time integrity check | MAY | At Level 3, implementations **MAY** compute a cryptographic hash of the tool server binary at launch time and compare it against a previously recorded value. Hash mismatches **MUST** block launch and generate an audit event. |

> **Residual risk:** If the agent runs with the same OS user credentials as the MCP client and tool servers (the common case on developer workstations), configuration path isolation and immutable tool directories require explicit OS-level hardening that most development environments do not have by default. Network isolation of tool servers is the only mitigation that does not depend on OS-level access control configuration. Deployments that cannot isolate tool servers to separate infrastructure **SHOULD** treat this as an accepted risk and document it in their conformance statement.

### 3.5.5 Approval Channel Token Theft (TS-22)

**Attack:** Out-of-band approval channels (Slack, Teams, PagerDuty, webhook endpoints) authenticate the Guardian's approval requests and the human's responses using software tokens: OAuth access tokens, webhook signing secrets, HMAC keys, API keys. These tokens are data. They can be stolen through filesystem access (configuration files, environment variables), process memory inspection, log exposure, or network interception. An attacker — including a compromised agent with filesystem access — who obtains the approval channel token can forge approval responses, bypassing the human principal entirely.

```
┌─────────────────┐                          ┌─────────────────┐
│     Agent       │  reads config/env/logs   │  Slack/Teams    │
│  (or attacker)  │ ──────────────────────► │  webhook secret │
│                 │                          │  or OAuth token │
│                 │  forges approval callback│                 │
│                 │ ──────────────────────► │  Guardian       │
│                 │                          │  accepts forged │
│                 │                          │  approval ✓     │
└─────────────────┘                          └─────────────────┘

     vs.

┌─────────────────┐                          ┌─────────────────┐
│     Agent       │  stolen token is useless │  Guardian       │
│  (or attacker)  │ ──────────────────────► │  requires FIDO2 │
│                 │                          │  hardware       │
│  Has token      │  ✗ no physical key       │  attestation    │
│  Missing key    │                          │  approval ✗     │
└─────────────────┘                          └─────────────────┘
```

**Why this matters:**

The standard's Boundary 3 requires approval channels that the agent cannot intercept or forge. HMAC-signed callbacks (per §4.4 and DLG-5) protect against *forgery by an attacker who doesn't have the signing key*. But the signing key is a software secret stored somewhere on the system. The standard's own threat model (T1, T3) assumes the agent or an attacker may have filesystem and process access. The HMAC key is only as secure as its storage, and in practice, webhook secrets and OAuth tokens for chat integrations are stored in environment variables, configuration files, or secret managers that may be accessible to the agent or to an attacker who has compromised the agent's host.

This is a fundamental limitation of software-only approval factors: they reduce to a secret that, once copied, can be used from anywhere.

**Mitigations:**

| Mitigation | Level | Description |
|------------|-------|-------------|
| Hardware-bound approval factor | SHOULD | For Level 2 and above, approval responses **SHOULD** require a hardware-bound cryptographic factor that cannot be extracted or replicated in software. FIDO2/WebAuthn security keys (e.g., YubiKey) are the reference implementation: the private key never leaves the hardware, and the approval response includes a hardware attestation that the Guardian can verify. Stolen software tokens are useless without physical possession of the key. |
| Hardware factor requirement at Level 3 | SHOULD | At Level 3, implementations **SHOULD** require hardware-bound approval factors for all profiles with `sensitive=true` entries. The conformance statement **MUST** document whether hardware-bound factors are in use and, if not, the compensating controls. |
| Channel token rotation | MUST | Approval channel tokens (webhook secrets, OAuth tokens, HMAC keys) **MUST** be rotated on a configurable schedule. Rotation intervals **SHOULD** default to no more than 24 hours for high-sensitivity deployments. |
| Channel token isolation | MUST | Approval channel tokens **MUST NOT** be stored in locations accessible to the agent process. The same storage isolation requirements that apply to Guardian tokens (§3.5.1, Token storage isolation) apply to approval channel credentials. |
| Approval response binding | SHOULD | Approval responses **SHOULD** be cryptographically bound to the specific request (including a nonce, timestamp, profile name, and entry list). Replaying a captured approval response for a different request **MUST** fail validation. |
| Approval channel audit | MUST | The Guardian **MUST** log the authentication method used for each approval response (software token only, hardware-attested, etc.). Approvals authenticated solely by software token for sensitive profiles **SHOULD** be flagged for review. |

> **Design note:** HMAC-signed callbacks and OAuth tokens protect the *channel* — they ensure the message came from Slack, not from a random HTTP client. They do not protect the *decision* — they do not prove a human with physical presence made the choice. A hardware-bound factor (FIDO2 key, smart card) closes this gap by requiring something that cannot be copied, proxied, or replayed from software alone. This is the same principle behind MFA in authentication: the token proves channel identity, the hardware key proves human presence.

> **Residual risk:** Hardware keys add friction and cost. Not all deployment environments can mandate them. Deployments that rely solely on software-authenticated approval channels should treat approval channel token theft as an accepted risk with compensating controls (aggressive rotation, token isolation, anomaly detection on approval timing and source IP). The risk is proportional to the value of the secrets the approval gates.

## 3.6 Guardian Deployment Topology

The standard is deliberately agnostic about whether the Guardian runs on the same machine as the agent or on a separate one. Both are conformant. But the choice has profound security implications that implementers and deployers must understand.

### 3.6.1 Co-Located Deployment

```
┌────────────────────────────────────────────┐
│              Single Machine                 │
│                                             │
│  ┌──────────┐  IPC   ┌──────────────────┐  │
│  │  Agent   │◄──────►│    Guardian      │  │
│  └──────────┘  (UDS) │  + Secret Store  │  │
│  ┌──────────┐        └──────────────────┘  │
│  │  Tools   │                               │
│  └──────────┘                               │
└────────────────────────────────────────────┘
```

**When appropriate:**
- Development and testing environments
- Single-developer workstations where the developer trusts their own machine
- Environments where the agent host is as well-hardened as any infrastructure component
- Proof-of-concept and evaluation deployments
- Scenarios where network latency to a remote Guardian is unacceptable

**What it provides:**
- Simplest deployment model: no network configuration, no TLS certificates
- Lowest latency: Unix domain socket IPC
- Process isolation still holds: agent cannot read Guardian memory
- All three security boundaries are intact *as long as the OS kernel is trusted*

**What it does not provide:**
- No protection if the agent host OS is compromised: the attacker is on the same machine as the Guardian, its encryption keys, and the encrypted secret storage
- No protection if the agent achieves root-equivalent access (container misconfiguration, privilege escalation)
- The blast radius of a single-machine compromise is total

### 3.6.2 Remote Deployment

```
┌──────────────────────┐          ┌──────────────────────┐
│   Agent Machine       │          │   Guardian Machine    │
│                       │  TLS/   │                       │
│  ┌──────────┐        │  mTLS   │  ┌──────────────────┐ │
│  │  Agent   │        │◄───────►│  │    Guardian      │ │
│  └──────────┘        │         │  │  + Secret Store  │ │
│  ┌──────────┐        │         │  └──────────────────┘ │
│  │  Tools   │        │         │                       │
│  └──────────┘        │         │  Hardened, minimal    │
│                       │         │  attack surface       │
│  Higher compromise    │         │                       │
│  risk (dev machine,   │         │                       │
│  CI runner, container)│         │                       │
└──────────────────────┘          └──────────────────────┘
```

**When appropriate:**
- Production deployments where agent hosts have elevated compromise risk
- Enterprise environments with dedicated secrets infrastructure
- Multi-agent deployments where many agents share a Guardian
- Container orchestration environments (Kubernetes, ECS) where container escape is a realistic threat
- CI/CD pipelines where build runners are ephemeral and semi-trusted
- Any deployment where the agent machine is less trusted than the secrets it orchestrates the use of

**What it provides:**
- **OS compromise of the agent host does not compromise the secret store.** The attacker gains access to tool process memory on the agent machine, which may contain secrets currently in use, but cannot reach the Guardian's encryption keys, the encrypted secret storage, or secrets not currently checked out to a tool on that host.
- The Guardian machine can be hardened independently: minimal services, restricted network access, dedicated hardware, HSM-backed key storage
- Audit logs on the Guardian machine are not accessible from the compromised agent host
- Multi-agent deployments benefit from centralized policy enforcement and audit

**What it costs:**
- Network latency on every secret request (mitigated by session approval caching at the Guardian, not secret caching at the tool)
- TLS certificate management: server certificates for Guardian, client certificates for mTLS at Level 3
- Network infrastructure: firewall rules, load balancers for high availability
- Operational complexity: two machines to manage instead of one

### 3.6.3 Deployment Topology Decision Criteria

| Factor | Favors Co-Located | Favors Remote |
|--------|-------------------|---------------|
| Agent host trust level | Host is hardened infrastructure | Host is a dev machine, CI runner, or container |
| Secret value | Low to moderate (dev keys, test tokens) | High (production credentials, signing keys, customer data access) |
| Number of agents | Single agent | Multiple agents sharing credentials |
| Compliance requirements | Minimal | SOC2, ISO 27001, regulatory (financial, healthcare) |
| Operational complexity budget | Minimal | Enterprise ops team available |
| Network environment | Air-gapped or latency-sensitive | Standard datacenter or cloud networking |
| Container deployment | No / trusted container runtime | Yes / shared container hosts |

### 3.6.4 Normative Requirements for Remote Deployment

When the Guardian is deployed on a separate machine from the agent:

| ID | Level | Requirement |
|----|-------|-------------|
| TOPO-1 | MUST | All Guardian communication **MUST** use TLS 1.3 or later (see [§6.4](../02-principles/06-trust-boundaries.md)) |
| TOPO-2 | MUST | Mutual TLS (mTLS) **MUST** be used for caller authentication at Level 2 and above. At Level 1, mTLS is **SHOULD** — strongly recommended but not a hard conformance gate; Level 1 deployments omitting mTLS MUST document the decision in their conformance statement. At Level 3, see also CONF-L3-8. See TLS-2 ([§6.4](../02-principles/06-trust-boundaries.md#64-transport-security)) for the full normative specification |
| TOPO-3 | MUST | Token-based authentication **MUST** be enforced in addition to transport-level authentication |
| TOPO-4 | MUST | The Guardian machine **MUST NOT** run agent processes or untrusted workloads |
| TOPO-5 | SHOULD | The Guardian machine **SHOULD** run only the Guardian service and its dependencies |
| TOPO-6 | MUST | Tools **MUST NOT** persist received secret values to disk in any form. Tools **MAY** cache received secret values in process memory for the duration of an authorized session (e.g., `prompt_once` with a configured TTL), but **MUST** discard all cached values when the session ends, the TTL expires, or the Guardian revokes access — whichever comes first. The Guardian **MUST** persist secret values exclusively in encrypted form as specified in §14 (CRYPTO-1 through CRYPTO-7). The Guardian **MUST NOT** retain decrypted secret values in any persistent storage |
| TOPO-6a | MUST | The Guardian **MUST** implement revocation signaling appropriate to the communication protocol in use. **Request-response protocols (HTTP REST, MCP, RPC):** The Guardian **MUST** return an explicit revocation error response (e.g., HTTP 401 with a `WWW-Authenticate` header indicating revoked token, or an equivalent structured error) to any request received after the revocation timestamp. Tools **MUST** treat this error as a revocation signal, immediately discard all in-memory cached values for the affected profile, and **MUST NOT** automatically retry with the same token. **Persistent connection protocols (WebSocket, SSE, long-polling):** The Guardian **MUST** send an explicit revocation event (see §4.3 for definition) on the open connection (e.g., a structured message with `event_type: "revocation"` and the revoked token or session identifier) within 5 seconds of the revocation being committed to persistent storage. Tools **MUST** close the connection and discard all cached values upon receiving a revocation event. **Maximum undetected revocation window:** For request-response protocols, the undetected revocation window is bounded by the time between the last request and the next one; implementations **MUST** document this window in the conformance statement and **MUST** document any maximum request polling interval enforced by the implementation. For persistent connections, the window **MUST NOT** exceed 5 seconds |
| TOPO-7 | SHOULD | The Guardian machine **SHOULD** be hardened with minimal network exposure: accessible only from authorized agent hosts on the Guardian's listening port |
| TOPO-8 | SHOULD | In containerized deployments, the Guardian **SHOULD** run in a dedicated, privileged container or on a separate host outside the container orchestration environment that manages agent workloads |

> **Design note:** TOPO-4 strengthens remote deployments by ensuring the Guardian host is more trusted than the agent host. A co-located Guardian (agent and Guardian on the same machine) still provides meaningful security: process isolation, token scoping, approval policies, and audit logging all function regardless of deployment topology. However, co-location means a host-level compromise exposes both the agent and the Guardian simultaneously. Remote deployment on a dedicated host adds a network boundary that limits this risk. The conformance levels reflect this gradient: co-located deployments can satisfy Level 1 and Level 2; Level 3 deployments SHOULD use dedicated Guardian infrastructure.

---

Next: [Core Concepts](04-core-concepts.md)
