# 14. Cryptographic Requirements

This section specifies the cryptographic requirements for conformant implementations. All algorithm references are normative and cite their defining standards in [§14.8](#148-normative-references).

## 14.1 Encryption at Rest

All secret values MUST be encrypted at rest.

### Algorithm Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| CRYPTO-1 | MUST | All secret values **MUST** be encrypted at rest using an AEAD cipher approved in this section | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-2 | MUST | AES-256-GCM ([NIST SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final)) or ChaCha20-Poly1305 ([RFC 7539](https://datatracker.ietf.org/doc/html/rfc7539)). Other AEAD ciphers **MAY** be used if they provide at least 256-bit key strength, authenticated encryption, and are defined by a published NIST or IETF standard | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-3 | MUST | Each entry **MUST** be encrypted with a unique nonce/IV | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-4 | MUST | Nonces **MUST** be randomly generated using a CSPRNG (not sequential) | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-5 | MUST | Nonces **MUST** be at least 96 bits (12 bytes) | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-6 | MUST NOT | The same nonce **MUST NOT** be reused with the same key | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-7 | MUST | Stored ciphertext **MUST** include an algorithm identifier that allows the implementation to determine which AEAD cipher was used for decryption. See [§14.7](#147-algorithm-agility) | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

### Why AEAD

> **Informative:** Authenticated Encryption with Associated Data (AEAD) provides both confidentiality and integrity. Confidentiality ensures secret values cannot be read; integrity ensures tampering with ciphertext is detected on decryption. AES-256-GCM is the most widely supported AEAD cipher. ChaCha20-Poly1305 is an equivalent alternative that performs well in software-only environments without AES hardware acceleration.

### Nonce Management

Nonce reuse with the same key is catastrophic for AEAD ciphers -- it completely breaks confidentiality and integrity. Implementations MUST:

1. Generate nonces using a CSPRNG (CRYPTO-4)
2. Never reuse nonces with the same key (CRYPTO-6)
3. Store nonces alongside ciphertext -- nonces are not secret, but MUST be retrievable for decryption

The nonce and authentication tag MUST be stored alongside the ciphertext. The storage format is implementation-defined but MUST allow unambiguous retrieval of the nonce, ciphertext, and authentication tag.

## 14.2 Master Key Management

The master encryption key protects all secret entries.

### Key Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| KEY-1 | MUST | Single master key per vault | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-2 | MUST | Key **MUST** be at least 256 bits | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-3 | MUST | Key **MUST** be generated using a CSPRNG | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-4 | SHOULD | Key **SHOULD** be stored in OS keychain or platform-provided credential manager. At Level 3, this is elevated to MUST (see [CONF-L3-1](../part-4-conformance/13-conformance.md#134-level-3-advanced)) | [TS-6](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-5 | MUST NOT | Key **MUST NOT** be stored in the vault database | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-6 | MUST NOT | Key **MUST NOT** be stored in environment variables | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-7 | MUST | Key **MUST** reside only in Guardian process memory at runtime. See Boundary 1 ([§3.3](../part-1-foundations/03-threat-model.md#33-security-boundaries)) and PROC-* requirements ([§6.1](../part-2-principles/06-trust-boundaries.md#61-boundary-1-process-isolation-agent--guardian)) | [TS-6](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

### Key Storage Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| STORE-1 | SHOULD | OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service/libsecret) **SHOULD** be used for key storage | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| STORE-2 | MAY | Hardware Security Module (HSM) or cloud KMS **MAY** be used. At Level 3, HSM or equivalent hardware-backed storage is RECOMMENDED | [TS-6](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| STORE-3 | MAY | Encrypted file with password-derived key (see [§14.3](#143-password-based-key-derivation)) **MAY** be used at Level 1. This is not sufficient at Level 3 ([CONF-L3-1](../part-4-conformance/13-conformance.md#134-level-3-advanced)) | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| STORE-4 | MUST NOT | Environment variables **MUST NOT** be used for key storage | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| STORE-5 | MUST NOT | Configuration files **MUST NOT** be used for key storage | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| STORE-6 | MUST NOT | The vault database **MUST NOT** be used for key storage | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

### Key Rotation

Key rotation is an advanced capability (Level 3). If implemented:

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| ROTATE-1 | MUST | A new master key **MUST** be generated per KEY-2 and KEY-3 | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| ROTATE-2 | MUST | All entries **MUST** be re-encrypted with the new key | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| ROTATE-3 | MUST | If re-encryption fails for any entry, the implementation **MUST** roll back to the previous key. Partial re-encryption states **MUST NOT** be persisted | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| ROTATE-4 | MUST | The old key **MUST** be securely erased from memory after successful rotation | [TS-6](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| ROTATE-5 | MUST | The rotation event **MUST** be recorded in the audit log ([§15](15-audit-observability.md)) | [TS-11](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| ROTATE-6 | SHOULD | Key rotation **SHOULD NOT** require re-entry of secret values by the human principal | -- |

## 14.3 Password-Based Key Derivation

If the master key is derived from a user-supplied password (common for Level 1):

### KDF Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| KDF-1 | MUST | Implementations **MUST** use Argon2id ([RFC 9106](https://datatracker.ietf.org/doc/html/rfc9106)), scrypt ([RFC 7914](https://datatracker.ietf.org/doc/html/rfc7914)), or PBKDF2-HMAC-SHA256 ([NIST SP 800-132](https://csrc.nist.gov/pubs/sp/800/132/final)) | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| KDF-2 | MUST | Salt **MUST** be at least 128 bits, randomly generated using a CSPRNG | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| KDF-3 | SHOULD | Argon2id **SHOULD** be preferred over scrypt, and scrypt over PBKDF2 | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| KDF-4 | MUST | Work factor **MUST** be sufficient to resist brute-force attacks with contemporary hardware | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

### Recommended Parameters

> **Informative:** The following parameters represent current minimum recommendations. Implementations SHOULD periodically re-evaluate these against contemporary attack capabilities.

**Argon2id (preferred):**
```
time_cost = 3
memory_cost = 64 MB
parallelism = 4
salt_length = 16 bytes
hash_length = 32 bytes
```

**scrypt:**
```
N = 2^17 (131072)
r = 8
p = 1
salt_length = 16 bytes
hash_length = 32 bytes
```

**PBKDF2-HMAC-SHA256:**
```
iterations = 600000
salt_length = 16 bytes
hash_length = 32 bytes
```

### Why Argon2id is Preferred

> **Informative:** Argon2id is resistant to GPU-based attacks (memory-hard), side-channel attacks, and time-memory tradeoffs. PBKDF2 is GPU-friendly and SHOULD only be used when Argon2id and scrypt are unavailable in the target environment.

## 14.4 Token Generation

Agent tokens MUST be unpredictable.

### Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| TOK-1 | MUST | Tokens **MUST** be generated using a CSPRNG | [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| TOK-2 | MUST | Tokens **MUST** be at least 256 bits (32 bytes) | [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| TOK-3 | MUST | Tokens **MUST** use an implementation-defined prefix that uniquely identifies the token type and prevents collision with other credential formats in the deployment environment. The prefix **MUST** be human-recognizable to support visual identification in logs and diagnostics | [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| TOK-4 | MUST | Tokens **MUST** be stored as a cryptographic hash digest, not as cleartext | [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

### Token Hashing

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| TOK-5 | MUST | Tokens **MUST** be stored as SHA-256 ([FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)) digests | [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| TOK-6 | MUST NOT | Implementations **MUST NOT** store cleartext tokens in any persistent storage | [TS-18](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| TOK-7 | MAY | Salt is not required for token hashing -- tokens generated per TOK-1 and TOK-2 provide sufficient entropy to resist preimage and collision attacks | -- |

> **Informative:** SHA-256 is appropriate because the input is a 256-bit random value (TOK-2), not a low-entropy password. Salting provides no additional security benefit for high-entropy inputs. The stored representation SHOULD be hexadecimal or base64 encoding of the hash digest.

## 14.5 Delegation Token Signing

Delegation tokens MUST be integrity-protected to prevent forgery.

### Signature Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| SIG-1 | MUST | Delegation tokens **MUST** be signed using HMAC-SHA256 ([RFC 2104](https://datatracker.ietf.org/doc/html/rfc2104), [FIPS 198-1](https://csrc.nist.gov/pubs/fips/198-1/final)) | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| SIG-2 | MUST | The delegation signing key **MUST** be derived from the master key using HKDF-SHA256 ([RFC 5869](https://datatracker.ietf.org/doc/html/rfc5869)) with an application-specific `info` parameter | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| SIG-3 | MUST | The Guardian **MUST** verify the signature before honoring any delegation token | [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-13](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| SIG-4 | MUST NOT | The master encryption key **MUST NOT** be used directly as the signing key | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| SIG-5 | SHOULD | At Level 3, implementations **SHOULD** use independent key material for signing and encryption rather than deriving both from a single master key | [TS-6](../part-1-foundations/03-threat-model.md#32-threat-scenarios), [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

### 14.5.1 Canonical Signed Payload

The signed payload is the byte sequence passed to HMAC-SHA256. Implementations **MUST** construct the canonical form as follows to ensure two independent implementations compute identical signatures.

| ID | Level | Requirement |
|----|-------|-------------|
| SIG-6 | MUST | The signed payload **MUST** include all delegation token fields that carry security-relevant authorization information: `token_id`, `parent_token_id`, `profile_name`, `scope` (all entry keys), `permissions` (all permitted operations), `issued_at`, `expires_at`, and `max_uses` (when present). Fields not listed here (e.g., a human-readable `description`) **MUST NOT** be included in the signed payload |
| SIG-7 | MUST | The signed payload **MUST** be the UTF-8 encoding of a JSON object containing exactly the fields listed in SIG-6. The JSON object **MUST** use no insignificant whitespace (no spaces after `:` or `,`, no newlines). Fields **MUST** appear in the order listed in SIG-6. No additional fields **MAY** appear in the payload object |
| SIG-8 | MUST | Array fields (`scope`, `permissions`) **MUST** be serialized with elements sorted in lexicographic (byte-order) ascending order. This ensures identical inputs regardless of the order in which array elements were specified at token creation time |
| SIG-9 | MUST | Timestamps (`issued_at`, `expires_at`) **MUST** be serialized as UTC ISO 8601 strings with second precision (e.g., `"2026-02-17T12:00:00Z"`). Millisecond or sub-second precision **MUST NOT** be used in the signed payload |
| SIG-10 | MUST | When `max_uses` is absent (unlimited uses), the field **MUST** be omitted from the payload object entirely. When present, it **MUST** be serialized as a JSON integer |
| SIG-11 | MUST | The HMAC output **MUST** be encoded as lowercase hexadecimal (64 characters) for storage and comparison. Base64 variants are **NOT** acceptable for the canonical signature representation |

**Example canonical payload** (illustrative, not normative):

```json
{"token_id":"del_abc123","parent_token_id":"tok_xyz789","profile_name":"aws-production","scope":["access_key_id","region","secret_access_key"],"permissions":["read"],"issued_at":"2026-02-17T12:00:00Z","expires_at":"2026-02-17T13:00:00Z"}
```

Note that `scope` entries are lexicographically sorted and no whitespace is present.

> **Design note:** Deriving the signing key from the master encryption key creates a single-root-key architecture. Compromise of the master key compromises both confidentiality and delegation integrity. Level 3 deployments with HSM-backed key storage SHOULD maintain separate key material for encryption and signing operations to limit the blast radius of a single-key compromise.

## 14.6 Cryptographic Library Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| LIB-1 | MUST | Implementations **MUST** use cryptographic libraries that have undergone public security audit or are maintained by the platform vendor | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| LIB-2 | MUST NOT | Implementations **MUST NOT** implement custom cryptographic primitives. All cryptographic operations **MUST** be delegated to vetted libraries satisfying LIB-1 | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| LIB-3 | SHOULD | Implementations **SHOULD** pin or lock cryptographic library versions and track security advisories for those libraries | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |

## 14.7 Algorithm Agility

Cryptographic algorithms have finite lifespans. Implementations MUST support algorithm identification to enable future migration without requiring a complete re-architecture of the secret store.

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AGILE-1 | MUST | Stored ciphertext **MUST** include an algorithm identifier (e.g., metadata field or prefix) that specifies the AEAD cipher used for encryption | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AGILE-2 | MUST | The Guardian **MUST** be able to decrypt entries encrypted with any previously-approved algorithm, even after a new default algorithm is configured | [TS-7](../part-1-foundations/03-threat-model.md#32-threat-scenarios) |
| AGILE-3 | SHOULD | Implementations **SHOULD** support configurable default algorithm selection, so that new entries are encrypted with the current preferred algorithm while existing entries remain readable | -- |
| AGILE-4 | SHOULD | Implementations **SHOULD** support re-encryption of existing entries to a new algorithm as part of key rotation (ROTATE-1 through ROTATE-6) or as a standalone migration operation | -- |

> **Design note:** Algorithm agility does not mean algorithm negotiation at runtime. The Guardian selects the algorithm; tools have no influence over which cipher is used. Agility means the storage format can evolve without a flag-day migration.

## 14.8 Normative References

The following external standards define the cryptographic algorithms and constructions referenced in this section:

| Algorithm / Construction | Reference | Used In |
|--------------------------|-----------|---------|
| AES-256-GCM | [NIST SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final) -- Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM) | CRYPTO-2 |
| AES (Rijndael) | [FIPS 197](https://csrc.nist.gov/pubs/fips/197/final) -- Advanced Encryption Standard | CRYPTO-2 |
| ChaCha20-Poly1305 | [RFC 7539](https://datatracker.ietf.org/doc/html/rfc7539) -- ChaCha20 and Poly1305 for IETF Protocols | CRYPTO-2 |
| Argon2id | [RFC 9106](https://datatracker.ietf.org/doc/html/rfc9106) -- Argon2 Memory-Hard Function for Password Hashing and Proof-of-Work Applications | KDF-1 |
| scrypt | [RFC 7914](https://datatracker.ietf.org/doc/html/rfc7914) -- The scrypt Password-Based Key Derivation Function | KDF-1 |
| PBKDF2 | [NIST SP 800-132](https://csrc.nist.gov/pubs/sp/800/132/final) -- Recommendation for Password-Based Key Derivation | KDF-1 |
| HKDF-SHA256 | [RFC 5869](https://datatracker.ietf.org/doc/html/rfc5869) -- HMAC-based Extract-and-Expand Key Derivation Function | SIG-2 |
| HMAC-SHA256 | [RFC 2104](https://datatracker.ietf.org/doc/html/rfc2104) -- HMAC: Keyed-Hashing for Message Authentication; [FIPS 198-1](https://csrc.nist.gov/pubs/fips/198-1/final) | SIG-1, SIG-6 through SIG-11 |
| SHA-256 | [FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final) -- Secure Hash Standard | TOK-5 |

---

Next: [Audit and Observability](15-audit-observability.md)
