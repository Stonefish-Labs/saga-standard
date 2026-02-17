# 8. Secret Profiles and Classification

A secret profile is the atomic unit of management. Each profile represents a logical grouping of related secrets--typically all the values needed to authenticate with a specific service or perform a specific class of operations.

## 8.1 Profile Structure

### Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| PROFILE-1 | MUST | Profile MUST have a `name` attribute that uniquely identifies the profile within the secret store |
| PROFILE-2 | MUST | Profile MUST have an `entries` attribute containing zero or more secret entries |
| PROFILE-3 | MUST | Profile MUST have an `approval_policy` attribute governing read access (see [§4.4](../part-1-foundations/04-core-concepts.md#44-approval-terms) and [§10](10-approval-policies.md)) |
| PROFILE-4 | MUST | Profile MUST have a `write_policy` attribute governing write access (see [§4.5](../part-1-foundations/04-core-concepts.md#45-lifecycle-terms) and [§10](10-approval-policies.md)) |
| PROFILE-5 | MUST | Profile MUST have `created_at` and `updated_at` timestamps in UTC ISO 8601 format |
| PROFILE-6 | MAY | Profile MAY have a `description` attribute for human-readable documentation |
| PROFILE-7 | MAY | Profile MAY have a `tags` attribute containing organizational labels for filtering |

## 8.2 Entry Structure

Each entry within a profile represents a single secret or configuration value.

### Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| ENTRY-1 | MUST | Entry MUST have a `key` attribute that uniquely identifies the entry within its parent profile |
| ENTRY-2 | MUST | Entry MUST have a `value` attribute containing the secret value (encrypted at rest; see [Cryptographic Requirements](../part-5-reference/14-cryptographic-requirements.md)) |
| ENTRY-3 | MUST | Entry MUST have a `sensitive` boolean attribute indicating display/logging behavior |
| ENTRY-4 | MAY | Entry MAY have a `description` attribute for human-readable documentation |
| ENTRY-5 | MAY | Entry MAY have a `field_type` attribute providing a UI rendering hint |

### Field Types

Field types are an open extension point. The following values are recommended for interoperability; additional values are provided in [Annex A](../annexes/annex-a-protocol-details.md):

| Type | Use Case | UI Behavior |
|------|----------|-------------|
| `text` | General text values | Single-line input |
| `password` | Passwords, secrets | Masked input |
| `url` | Endpoints, URLs | URL-validated input |
| `email` | Email addresses | Email-validated input |
| `number` | Numeric values | Number input |
| `boolean` | True/false flags | Checkbox/toggle |

## 8.3 Sensitivity Classification

Sensitivity classification determines how entries are displayed and logged--not how they're stored. This section restates the sensitivity behavior defined in [§5.3 Principle of Declared Sensitivity](../part-2-principles/05-design-principles.md#53-principle-of-declared-sensitivity).

### Behavior Matrix

| Behavior | `sensitive=true` | `sensitive=false` |
|----------|-----------------|-------------------|
| Encryption at rest | Required | Required |
| Display in CLI | Masked (`****`) | Shown |
| Display in UI | Masked with reveal option | Shown |
| Included in audit log values | No | Optional |
| Default for new entries | Yes | No |
| Can override on write | Only with explicit flag | Only with explicit flag |

### Critical Requirement

> **All entries MUST be encrypted at rest regardless of sensitivity classification.**
>
> Sensitivity affects *display and logging behavior*, not storage security. An implementation that stores non-sensitive entries in plaintext is non-conformant. See [Cryptographic Requirements](../part-5-reference/14-cryptographic-requirements.md) for algorithm and key management requirements.

### Classification Guidance

The following guidance illustrates common classification patterns. The human principal makes the final classification decision for each entry (see [§5.3](../part-2-principles/05-design-principles.md#53-principle-of-declared-sensitivity)).

| Typically Sensitive | Typically Non-Sensitive |
|--------------------|-------------------------|
| Passwords | Public endpoints |
| API keys | Region identifiers |
| Access tokens | Non-secret configuration |
| Private keys | Public keys |
| Connection strings with embedded credentials | Connection strings without credentials |

Context matters: an endpoint URL that reveals internal infrastructure topology may be sensitive in one environment and not in another.

## 8.4 Profile Name Resolution

Tools MUST resolve the target profile name before issuing a request to the Guardian. The profile name is the *identity* of the secret set a tool needs--it is not itself a secret and MUST NOT contain secret values.

### Resolution Order

| Priority | Source | Description |
|----------|--------|-------------|
| 1 | Explicit parameter | Client constructor receives profile name directly (e.g., `Vault(profile="discord-webhook")`) |
| 2 | Environment variable | Implementation-defined env var, set by process launcher, overrides tool default |
| 3 | Tool default | Compile-time or configuration-time default |

If none of these yield a profile name, the implementation MUST raise an error. Implementations MUST NOT fall back to a global default profile.

### Requirements

| ID | Level | Requirement |
|----|-------|-------------|
| RESOLVE-1 | MUST | Explicit parameter takes highest priority |
| RESOLVE-2 | MUST | Environment variable overrides tool default |
| RESOLVE-3 | MUST | The profile environment variable MUST be treated as a plain profile name, never a secret (see RESOLVE-4) |
| RESOLVE-4 | MUST | Environment variables MUST NOT be used to pass secret values |
| RESOLVE-5 | SHOULD | Tools SHOULD document their default profile name and expected keys |
| RESOLVE-6 | MAY | Additional resolution sources allowed between priorities |

### Example

```
Resolution Priority 1 (explicit parameter):
  tool --profile staging-discord "Hello"

Resolution Priority 2 (environment variable):
  PROFILE_ENV=staging-discord tool "Hello"

Resolution Priority 3 (tool default):
  tool "Hello"
  → tool uses its compiled or configured default profile name
```

## 8.5 Designing Your Profiles

> **Note:** The guidance in this section is non-normative. It illustrates recommended practices but does not define conformance requirements.

### Profile Granularity

Apply the principle of least privilege when designing profiles. A profile should grant only the capabilities a tool actually needs--not merely group credentials by service or environment.

**Scope by capability, not just by environment:**

```
PRINCIPLE OF LEAST PRIVILEGE:
├── aws-production-readonly    (Read-only access to production)
├── aws-production-deploy      (Deploy capabilities only)
├── aws-production-admin       (Full administrative access)
├── github-readonly            (Read repository access)
├── github-write               (Write repository access)
├── github-actions             (CI/CD workflow management)
├── database-production-read   (Read-only database queries)
└── database-production-write  (Database write access)

AVOID:
├── aws-production             (Ambiguous: what can this do?)
├── github-api                 (Ambiguous: read, write, or admin?)
├── all-secrets                (Everything in one profile)
└── aws-all-environments       (Production and dev in same profile)
```

**Why capability-scoped profiles:**

- Compromise of one profile doesn't expose others (see [§3.3 Boundary 2](../part-1-foundations/03-threat-model.md#32-threat-scenarios), TS-4 and TS-5)
- Different tools need different capability levels--read-only monitoring tools shouldn't hold write credentials
- Different risk levels warrant different approval policies--deploy profiles may require Tier 0, read-only profiles may operate at Tier 2
- Blast radius is limited when credentials are scoped to minimum necessary capability
- Easier to audit which operations were possible with compromised credentials

**Read-only vs. write profiles:**

Many services support separate credentials for read and write operations. Where available, use separate profiles:

| Profile Type | Use Case | Typical Tier |
|--------------|----------|--------------|
| Read-only | Monitoring, reporting, audit tools | Tier 1-2 |
| Write-only | Ingestion, logging sinks | Tier 2 |
| Read-write | General-purpose operations | Tier 0-1 |
| Admin | Account management, credential rotation | Tier 0 |

### Entry Organization

Within a profile, include all values needed for the intended capability level:

```
aws-production-readonly:
├── access_key_id       (AWS access key)
├── secret_access_key   (AWS secret key)
├── region              (Default region)
└── (no write permissions in IAM policy)

aws-production-deploy:
├── access_key_id       (AWS access key with deploy permissions)
├── secret_access_key   (AWS secret key)
├── region              (Default region)
├── deploy_role_arn     (Role to assume for deployments)
└── (no admin permissions in IAM policy)

oauth-google:
├── client_id           (OAuth client ID)
├── client_secret       (OAuth client secret)
├── refresh_token       (Long-lived refresh token)
├── access_token        (Current access token, updated by tool)
└── token_url           (Token endpoint URL)
```

### Naming Conventions

Use consistent, descriptive names that convey both service and capability:

```
GOOD:
- github-readonly
- github-write
- aws-production-readonly
- aws-production-deploy
- stripe-live-read
- stripe-live-write

BAD:
- profile1
- secret
- prod (ambiguous: which service? which capability?)
- aws-production (ambiguous: readonly or full access?)
- my-key
```

---

Next: [Access Control](09-access-control.md)
