# 14. Cryptographic Requirements

This section specifies the cryptographic requirements for conformant implementations. All algorithm references are normative and cite their defining standards in [§14.8](#148-normative-references).

## 14.1 Encryption at Rest

All secret values MUST be encrypted at rest.

### Algorithm Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| CRYPTO-1 | MUST | All secret values **MUST** be encrypted at rest using an AEAD cipher approved in this section | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-2 | MUST | AES-256-GCM ([NIST SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final)) or ChaCha20-Poly1305 ([RFC 8439](https://datatracker.ietf.org/doc/html/rfc8439)). Other AEAD ciphers **MAY** be used if they use a key of at least 256 bits, provide authenticated encryption, and are defined by a published NIST or IETF standard. Note: the 256-bit key size requirement specifies key material size, not classical security level (AES-256 provides approximately 128-bit classical security level due to Grover's algorithm bounds; this is sufficient for the threat model of this standard, which does not require quantum-resistant encryption at this revision — see the Post-Quantum Cryptography Forward Note in §14.7) | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-3 | MUST | Each entry **MUST** be encrypted with a unique nonce/IV | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-4 | MUST | Nonces **MUST** be randomly generated using a CSPRNG (not sequential) | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-5 | MUST | Nonces **MUST** be at least 96 bits (12 bytes) | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-6 | MUST NOT | The same nonce **MUST NOT** be reused with the same key | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-7 | MUST | Stored ciphertext **MUST** include an algorithm identifier that allows the implementation to determine which AEAD cipher was used for decryption. See [§14.7](#147-algorithm-agility) | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| CRYPTO-8 | MUST | When AES-256-GCM is used, the authentication tag **MUST** be 128 bits (16 bytes). Tag truncation is **NOT** permitted. Implementations **MUST NOT** accept ciphertext with authentication tags shorter than 128 bits | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |

### Why AEAD

> **Informative:** Authenticated Encryption with Associated Data (AEAD) provides both confidentiality and integrity. Confidentiality ensures secret values cannot be read; integrity ensures tampering with ciphertext is detected on decryption. AES-256-GCM is the most widely supported AEAD cipher. ChaCha20-Poly1305 is an equivalent alternative that performs well in software-only environments without AES hardware acceleration.

### Nonce Management

Nonce reuse with the same key is catastrophic for AEAD ciphers; it completely breaks confidentiality and integrity. Implementations MUST:

1. Generate nonces using a CSPRNG (CRYPTO-4)
2. Never reuse nonces with the same key (CRYPTO-6)
3. Store nonces alongside ciphertext (nonces are not secret, but MUST be retrievable for decryption)

The nonce and authentication tag MUST be stored alongside the ciphertext. The storage format is implementation-defined but MUST allow unambiguous retrieval of the nonce, ciphertext, and authentication tag.

## 14.2 Master Key Management

The master encryption key protects all secret entries.

### Key Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| KEY-1 | MUST | Single master key per vault | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-1a | SHOULD | Implementations **SHOULD** support per-entry data encryption keys (DEK) — envelope encryption — where each entry is encrypted with a unique DEK that is itself encrypted with the master key and stored alongside the entry ciphertext. When envelope encryption is implemented: (a) each DEK **MUST** be at least 256 bits, generated using a CSPRNG (per KEY-2, KEY-3); (b) the DEK **MUST** be encrypted using the AEAD algorithm configured per CRYPTO-2, with a unique nonce per CRYPTO-4/CRYPTO-5; (c) the DEK ciphertext envelope **MUST** include an algorithm identifier per AGILE-1 — the DEK ciphertext MUST be stored as a complete AGILE-1 envelope, not as a bare ciphertext blob; (d) the entry ciphertext is encrypted by the DEK, not the master key directly; the master key is used only to decrypt the DEK; (e) **per-write freshness** — a new DEK MUST be generated for every write operation; the same DEK MUST NOT be reused across multiple write operations for the same entry, even when the entry value has not changed, as DEK reuse enables cryptanalytic attacks if nonce uniqueness guarantees are weakened. The stored structure per entry MUST be: `[AGILE-1 envelope: master-key-encrypted DEK ciphertext] || [AGILE-1 envelope: DEK-encrypted entry ciphertext]`, where each envelope is a full AGILE-1 ciphertext including the 1-byte algorithm identifier prefix. This makes master key rotation tractable for large vaults (only DEK ciphertexts need re-encryption with the new master key; entry ciphertext is re-encrypted only when the DEK changes) and limits the scope of any single-DEK compromise to one entry | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-2 | MUST | Key **MUST** be at least 256 bits | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-3 | MUST | Key **MUST** be generated using a CSPRNG | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-4 | SHOULD | Key **SHOULD** be stored in OS keychain or platform-provided credential manager. At Level 3, this is elevated to MUST (see [CONF-L3-1](../04-conformance/13-conformance.md#134-level-3-advanced)) | [TS-6](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-5 | MUST NOT | Key **MUST NOT** be stored in the vault database | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-6 | MUST NOT | Key **MUST NOT** be stored in environment variables | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| KEY-7 | MUST | Key **MUST** reside only in Guardian process memory at runtime. See Boundary 1 ([§3.3](../01-foundations/03-threat-model.md#33-security-boundaries)) and PROC-* requirements ([§6.1](../02-principles/06-trust-boundaries.md#61-boundary-1-process-isolation-agent--guardian)) | [TS-6](../01-foundations/03-threat-model.md#32-threat-scenarios) |

### Key Storage Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| STORE-1 | SHOULD | OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service/libsecret) **SHOULD** be used for key storage | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| STORE-2 | MAY | Hardware Security Module (HSM) or cloud KMS **MAY** be used. At Level 3, HSM or equivalent hardware-backed storage is RECOMMENDED | [TS-6](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| STORE-3 | MAY | Encrypted file with password-derived key (see [§14.3](#143-password-based-key-derivation)) **MAY** be used at Level 1. This is not sufficient at Level 3 ([CONF-L3-1](../04-conformance/13-conformance.md#134-level-3-advanced)) | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| STORE-4 | MUST NOT | Environment variables **MUST NOT** be used for key storage | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| STORE-5 | MUST NOT | Configuration files **MUST NOT** be used for key storage | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| STORE-6 | MUST NOT | The vault database **MUST NOT** be used for key storage | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |

### Key Rotation

Key rotation is an advanced capability (Level 3). If implemented:

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| ROTATE-1 | MUST | A new master key **MUST** be generated per KEY-2 and KEY-3 | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| ROTATE-2 | MUST | All entries **MUST** be re-encrypted with the new key | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| ROTATE-3 | MUST | If re-encryption fails for any entry, the implementation **MUST** roll back to the previous key. Partial re-encryption states **MUST NOT** be persisted | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| ROTATE-4 | MUST | The old key **MUST** be securely erased from memory after successful rotation. **In native/systems language runtimes** (C, C++, Rust, Go): Implementations **MUST** use an explicit memory zeroing mechanism that is guaranteed not to be elided by compiler dead-store elimination optimizations: `explicit_bzero` or `memset_s` (C11 Annex K) on POSIX; `SecureZeroMemory` or `RtlSecureZeroMemory` on Windows; `zeroize` (Rust crate with volatile write guarantee); explicit volatile writes. Naive `memset` calls are **NOT** conformant because compilers routinely elide them as dead stores when the memory is not subsequently read. **In managed runtime environments** (Java, Python, .NET, Go with GC, Node.js) where the runtime controls memory layout and the developer cannot directly zero heap memory: implementations MUST apply all of the following compensating measures, documented in the conformance statement: (a) minimize the lifetime of in-memory key material by storing keys as mutable byte arrays rather than immutable strings, and explicitly overwriting the array with zeros immediately before releasing the reference; (b) avoid copying key material into long-lived variables, caches, or serialization buffers; (c) invoke the runtime's available secure erase mechanism if present (e.g., `Arrays.fill(keyBytes, (byte)0)` in Java, `Array.Clear` in .NET before the array goes out of scope); (d) document that full memory zeroing guarantees are not achievable in this runtime environment. Implementations MUST NOT claim equivalence to native-code zeroing for managed runtimes | [TS-6](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| ROTATE-5 | MUST | The rotation event **MUST** be recorded in the audit log ([§15](15-audit-observability.md)) | [TS-11](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| ROTATE-6 | SHOULD | Key rotation **SHOULD NOT** require re-entry of secret values by the human principal | -- |

## 14.3 Password-Based Key Derivation

If the master key is derived from a user-supplied password (common for Level 1):

### KDF Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| KDF-1 | MUST | Implementations **MUST** use Argon2id ([RFC 9106](https://datatracker.ietf.org/doc/html/rfc9106)), scrypt ([RFC 7914](https://datatracker.ietf.org/doc/html/rfc7914)), or PBKDF2-HMAC-SHA256 ([NIST SP 800-132](https://csrc.nist.gov/pubs/sp/800/132/final)) | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| KDF-2 | MUST | Salt **MUST** be at least 128 bits, randomly generated using a CSPRNG | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| KDF-3 | SHOULD | Argon2id **SHOULD** be preferred over scrypt, and scrypt over PBKDF2 | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| KDF-4 | MUST | Work factor **MUST** meet the following minimum normative requirements. For Argon2id ([RFC 9106](https://datatracker.ietf.org/doc/html/rfc9106)): `time_cost` ≥ 3, `memory_cost` ≥ 65536 (in KiB, per RFC 9106 §3.1 — this is 64 × 1024 KiB = 64 MiB), `parallelism` ≥ 4, `hash_length` = 32 bytes (256 bits, to satisfy KEY-2). *Note: RFC 9106 measures `memory_cost` in kibibytes (KiB). An implementation expressing this as "64 MB" MUST verify it is using 65536 KiB, not 64000 KiB.* For scrypt ([RFC 7914](https://datatracker.ietf.org/doc/html/rfc7914)): N ≥ 2^17 (131072), r ≥ 8, p ≥ 1, `dkLen` = 32 bytes (256 bits). For PBKDF2-HMAC-SHA256: iterations ≥ 600,000, `dkLen` = 32 bytes (256 bits). In all cases, the derived key output length **MUST** be exactly 32 bytes (256 bits) to satisfy KEY-2. These are minimum values; implementations **SHOULD** use higher values and **SHOULD** periodically re-evaluate against contemporary attack capabilities (OWASP Password Storage Cheat Sheet provides current guidance). Implementations **MUST** document their chosen parameters, including the output length, in their conformance statement | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |

### Minimum Parameters

> **Informative:** The parameters in KDF-4 represent current minimum normative values. Implementations SHOULD use higher values and SHOULD re-evaluate periodically.

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
| TOK-1 | MUST | Tokens **MUST** be generated using a CSPRNG | [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| TOK-2 | MUST | Tokens **MUST** be at least 256 bits (32 bytes) | [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| TOK-3 | MUST | Tokens **MUST** use an implementation-defined prefix that uniquely identifies the token type and prevents collision with other credential formats in the deployment environment. The prefix **MUST** be human-recognizable to support visual identification in logs and diagnostics | [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| TOK-4 | MUST | Tokens **MUST** be stored as a cryptographic hash digest, not as cleartext | [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios) |

### Token Hashing

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| TOK-5 | MUST | Tokens **MUST** be stored as SHA-256 ([FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final)) digests | [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| TOK-6 | MUST NOT | Implementations **MUST NOT** store cleartext tokens in any persistent storage | [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| TOK-7 | MAY | Salt is not required for token hashing; tokens generated per TOK-1 and TOK-2 provide sufficient entropy to resist preimage and collision attacks | -- |
| TOK-8 | MUST | Token hash comparison at authentication time **MUST** use a constant-time comparison function to prevent timing oracle attacks. Implementations **MUST NOT** use standard string equality or byte-array equality operations for token comparison, as these may return early on the first differing byte | [TS-18](../01-foundations/03-threat-model.md#32-threat-scenarios) |

> **Informative:** SHA-256 is appropriate because the input is a 256-bit random value (TOK-2), not a low-entropy password. Salting provides no additional security benefit for high-entropy inputs. The stored representation SHOULD be hexadecimal or base64 encoding of the hash digest.

## 14.5 Delegation Token Signing

Delegation tokens MUST be integrity-protected to prevent forgery.

### Signature Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| SIG-1 | MUST | Delegation tokens **MUST** be signed using HMAC-SHA256 ([RFC 2104](https://datatracker.ietf.org/doc/html/rfc2104), [FIPS 198-1](https://csrc.nist.gov/pubs/fips/198-1/final)) | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| SIG-2 | MUST | The delegation signing key **MUST** be derived from the master key using HKDF-SHA256 ([RFC 5869](https://datatracker.ietf.org/doc/html/rfc5869)) with the `info` parameter set to the UTF-8 encoding of the ASCII string `"SAGA-delegation-signing-key-v1"` (30 bytes, no null terminator). The `salt` parameter **MUST** be omitted (zero-length), per RFC 5869 §2.2. This normative `info` value ensures two independent implementations deriving from the same master key produce identical signing keys. Implementations MUST verify that the byte length of their encoded `info` value is exactly 30 before use; a mismatch indicates a transcription error that will produce non-interoperable signing keys | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| SIG-3 | MUST | The Guardian **MUST** verify the signature before honoring any delegation token | [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-13](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| SIG-4 | MUST NOT | The master encryption key **MUST NOT** be used directly as the signing key | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-12](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| SIG-5 | MUST | At Level 3, implementations **MUST** use independent key material for signing and encryption rather than deriving both from a single master key. The signing key and the encryption master key **MUST** be independently generated or independently derived from separate root secrets. **At Level 3, this requirement supersedes SIG-2: the HKDF derivation path specified in SIG-2 (deriving the signing key from the master encryption key) is not conformant at Level 3.** SIG-2 applies at Level 1 and Level 2 only. At Level 3, the delegation signing key MUST be independently generated or derived from a root secret that is independent of the master encryption key. The conformance statement MUST document the key material derivation path for the signing key and confirm it does not share a root secret with the encryption master key. This requirement prevents a single-root-key compromise from simultaneously breaking both confidentiality and delegation integrity | [TS-6](../01-foundations/03-threat-model.md#32-threat-scenarios), [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |

### 14.5.1 Canonical Signed Payload

The signed payload is the byte sequence passed to HMAC-SHA256. Implementations **MUST** construct the canonical form as follows to ensure two independent implementations compute identical signatures.

| ID | Level | Requirement |
|----|-------|-------------|
| SIG-6 | MUST | The signed payload **MUST** include all delegation token fields that carry security-relevant authorization information: `token_id`, `parent_token_id`, `profile_name`, `scope` (all entry keys), `permissions` (all permitted operations), `issued_at`, `expires_at`, and `max_uses` (when present). Fields not listed here (e.g., a human-readable `description`) **MUST NOT** be included in the signed payload |
| SIG-7 | MUST | The signed payload **MUST** be the UTF-8 encoding of a JSON object containing exactly the fields listed in SIG-6. The JSON object **MUST** use no insignificant whitespace (no spaces after `:` or `,`, no newlines). Fields **MUST** appear in the order listed in SIG-6. Additional fields **MUST NOT** appear in the payload object. Implementations **MUST** reject delegation tokens whose signed payload contains fields not listed in SIG-6, as unrecognized fields indicate either a canonicalization error or an attempt to include unsigned data within the payload boundary |
| SIG-8 | MUST | Array fields (`scope`, `permissions`) **MUST** be serialized with elements sorted in lexicographic (byte-order) ascending order. This ensures identical inputs regardless of the order in which array elements were specified at token creation time |
| SIG-9 | MUST | Timestamps (`issued_at`, `expires_at`) **MUST** be serialized as UTC ISO 8601 strings with second precision (e.g., `"2026-02-17T12:00:00Z"`). Millisecond or sub-second precision **MUST NOT** be used in the signed payload. **Design note:** Delegation token timestamps use second precision for RFC 8693 (OAuth 2.0 Token Exchange) interoperability. Audit log timestamps (§15.2 AUDIT-3a) use millisecond precision for SIEM correlation and TS-17 anomaly detection. This divergence is intentional; do not harmonize them |
| SIG-10 | MUST | When `max_uses` is absent (unlimited uses), the field **MUST** be omitted from the payload object entirely. When present, it **MUST** be serialized as a JSON integer |
| SIG-11 | MUST | The HMAC output **MUST** be encoded as lowercase hexadecimal (64 characters) for storage and comparison. Base64 variants are **NOT** acceptable for the canonical signature representation |

**Example canonical payload** (illustrative, not normative):

```json
{"token_id":"del_abc123","parent_token_id":"tok_xyz789","profile_name":"aws-production","scope":["access_key_id","region","secret_access_key"],"permissions":["read"],"issued_at":"2026-02-17T12:00:00Z","expires_at":"2026-02-17T13:00:00Z"}
```

Note that `scope` entries are lexicographically sorted and no whitespace is present.

> **Design note:** Deriving the signing key from the master encryption key creates a single-root-key architecture. Compromise of the master key compromises both confidentiality and delegation integrity. Level 3 deployments with HSM-backed key storage MUST maintain separate key material for encryption and signing operations (see SIG-5) to limit the blast radius of a single-key compromise.

### 14.5.2 Cross-System Signing Requirements

HMAC-SHA256 is symmetric: verification requires the same key as signing. For cross-system delegation between independent Guardian instances that maintain independent master key hierarchies, HMAC-SHA256 alone is insufficient because key sharing would be required for verification, which DEL-10 prohibits.

When delegation tokens cross independent trust domains, one of the following three mechanisms **MUST** be used:

| Mechanism | Requirement | When to Use |
|-----------|-------------|-------------|
| **Option A — Asymmetric signing** | The issuing Guardian **MUST** sign delegation tokens using ECDSA with NIST P-256 ([FIPS 186-5](https://csrc.nist.gov/pubs/fips/186/5/final)) or Ed25519 ([RFC 8032](https://datatracker.ietf.org/doc/html/rfc8032)). The issuing Guardian's public key **MUST** be communicated to the verifying Guardian through a pre-established trust anchor. The verifying Guardian **MUST** verify the signature using the issuing Guardian's public key before honoring the delegation token. **Payload:** The signed byte sequence **MUST** be the canonical payload defined in §14.5.1 (SIG-6 through SIG-9): a JSON object serialized per SIG-7 containing exactly the fields listed in SIG-6, with arrays sorted per SIG-8 and timestamps formatted per SIG-9. **Signature encoding:** ECDSA signatures **MUST** be encoded in DER format (SEQUENCE of two INTEGERs r and s). Ed25519 signatures **MUST** be encoded as the 64-byte raw concatenation R\|\|S as specified in RFC 8032 §5.1.6. The encoded signature **MUST** be stored in the token's `signature` field as lowercase hexadecimal | Cross-organization; independent key hierarchies; no shared secrets |
| **Option B — OAuth 2.0 Token Exchange** | Cross-system authorization **MUST** use RFC 8693 Token Exchange with the issuing Guardian as the authorization server. The verifying Guardian **MUST** validate the token via RFC 7662 introspection at the issuing Guardian. This option is **RECOMMENDED** for cross-organization federation | Cross-organization; existing OAuth infrastructure; Internet-accessible endpoints |
| **Option C — Pre-established shared channel** | HMAC-SHA256 **MAY** be used across Guardians within the same organization when the signing key is distributed via a pre-established, mutually-authenticated secure channel (mTLS per TOPO-2). Key distribution **MUST** be documented in the conformance statement and **MUST NOT** use the primary secret access channel. Delegation tokens using Option C **MUST** include a `key_id` field identifying which registered shared key was used to sign the token, enabling the verifying Guardian to select the correct verification key from its trust registry. The `key_id` field **MUST** be included in the canonical signed payload (in addition to the fields listed in SIG-6) to prevent key-confusion attacks | Same-organization; shared operations team; private network |

Guardians **MUST** reject HMAC-signed delegation tokens from unknown or unregistered Guardian instances. Cross-system trust registration (the mechanism by which Guardian A becomes a known issuer to Guardian B) is deployment-defined but **MUST** be documented in the conformance statement for Level 3 cross-system deployments.

## 14.6 Cryptographic Library Requirements

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| LIB-1 | MUST | Implementations **MUST** use cryptographic libraries that satisfy at least one of the following criteria: (a) have undergone a public security audit by an independent security firm within the past five years, with the audit report publicly accessible; (b) are maintained by the platform vendor as part of the OS or platform distribution (e.g., OpenSSL/BoringSSL on Linux, Security.framework on macOS, BCrypt/NCrypt on Windows, JCA/JCE in Java); or (c) are part of a recognized security-focused project with a documented security response process and published CVE history (e.g., libsodium, Bouncy Castle with active maintenance). Implementations **MUST** document in their conformance statement which library is used and which criterion it satisfies | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| LIB-2 | MUST NOT | Implementations **MUST NOT** implement custom cryptographic primitives. All cryptographic operations **MUST** be delegated to vetted libraries satisfying LIB-1 | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| LIB-3 | SHOULD | Implementations **SHOULD** pin or lock cryptographic library versions and track security advisories for those libraries | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |

## 14.7 Algorithm Agility

Cryptographic algorithms have finite lifespans. Implementations MUST support algorithm identification to enable future migration without requiring a complete re-architecture of the secret store.

| ID | Level | Requirement | Mitigates |
|----|-------|-------------|-----------|
| AGILE-1 | MUST | Stored ciphertext **MUST** include an algorithm identifier that specifies the AEAD cipher used for encryption. The algorithm identifier **MUST** be stored as a 1-byte unsigned integer prefix immediately preceding the nonce in the serialized ciphertext envelope. **Normative algorithm identifier registry:** `0x01` = AES-256-GCM; `0x02` = ChaCha20-Poly1305; `0x00` = reserved, **MUST NOT** be used; `0x03`–`0x0F` = reserved for future standard algorithms; `0x10`–`0x7F` = available for implementation-specific extensions (see below); `0x80`–`0xFF` = reserved for future standard allocation. **Extension identifiers (`0x10`–`0x7F`):** Implementations using other AEAD ciphers permitted by CRYPTO-2 **MUST** use identifiers in the `0x10`–`0x7F` range. Extension identifiers and their associated algorithms **MUST** be documented in the conformance statement with the algorithm name, reference standard, and key/nonce/tag sizes. **Unknown identifier handling:** If the Guardian encounters a ciphertext with an algorithm identifier it does not recognize, the Guardian **MUST** refuse decryption and return an error. The Guardian **MUST NOT** attempt to guess the algorithm or proceed with partial decryption. This is a fail-closed requirement. **Serialized ciphertext envelope format for standard identifiers 0x01 (AES-256-GCM) and 0x02 (ChaCha20-Poly1305):** `[1-byte algorithm ID] || [12-byte nonce] || [ciphertext] || [16-byte authentication tag]`. All fields are concatenated with no framing; the 12-byte nonce and 16-byte authentication tag lengths are fixed for identifiers 0x01 and 0x02 only. **For extension identifiers (0x10–0x7F):** the nonce length and authentication tag length are algorithm-defined and MUST NOT be assumed to match the 12-byte/16-byte values specified above; the format is `[1-byte algorithm ID] || [nonce of algorithm-defined length] || [ciphertext] || [authentication tag of algorithm-defined length]`; implementations MUST document the exact byte lengths for the nonce and authentication tag alongside the extension identifier definition in the conformance statement. Implementations encountering an unrecognized identifier MUST NOT assume the 12-byte/16-byte format and MUST fail closed per the unknown identifier handling requirement above | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AGILE-2 | MUST | The Guardian **MUST** be able to decrypt entries encrypted with any previously-approved algorithm, even after a new default algorithm is configured | [TS-7](../01-foundations/03-threat-model.md#32-threat-scenarios) |
| AGILE-3 | SHOULD | Implementations **SHOULD** support configurable default algorithm selection, so that new entries are encrypted with the current preferred algorithm while existing entries remain readable | -- |
| AGILE-4 | SHOULD | Implementations **SHOULD** support re-encryption of existing entries to a new algorithm as part of key rotation (ROTATE-1 through ROTATE-6) or as a standalone migration operation | -- |

> **Design note:** Algorithm agility does not mean algorithm negotiation at runtime. The Guardian selects the algorithm; tools have no influence over which cipher is used. Agility means the storage format can evolve without a flag-day migration.

### Post-Quantum Cryptography Forward Note

> **Informative:** In August 2024, NIST finalized the first post-quantum cryptographic standards: FIPS 203 (Module-Lattice-Based Key-Encapsulation Mechanism Standard, based on CRYSTALS-Kyber), FIPS 204 (Module-Lattice-Based Digital Signature Standard, based on CRYSTALS-Dilithium), and FIPS 205 (Stateless Hash-Based Digital Signature Standard, based on SPHINCS+). These algorithms are designed to be secure against quantum computing attacks that would break current RSA, ECDSA, and Diffie-Hellman-based schemes.
>
> This version of the SAGA standard does not mandate post-quantum algorithms because the ecosystem integration (library support, performance characteristics, and interoperability tooling) is still maturing. However, the AGILE-1 registry is designed to accommodate post-quantum AEAD ciphers through the extension identifier range (`0x10`–`0x7F`), and the §14.5.2 Option A asymmetric signing requirements do not preclude use of FIPS 204 or FIPS 205 for delegation token signing at Level 3.
>
> Implementations operating in environments with long-term data sensitivity (secrets that must remain confidential beyond a 10-year horizon), or in threat models that include well-resourced state-level adversaries with access to quantum computing capability, **SHOULD** evaluate post-quantum migration timelines and document their approach in the conformance statement. A future revision of this standard is expected to include normative post-quantum algorithm requirements as NIST FIPS 203/204/205 library support matures.
>
> For current NIST guidance, see: [NIST Post-Quantum Cryptography](https://csrc.nist.gov/projects/post-quantum-cryptography).

## 14.8 Normative References

The following external standards define the cryptographic algorithms and constructions referenced in this section:

| Algorithm / Construction | Reference | Used In |
|--------------------------|-----------|---------|
| AES-256-GCM | [NIST SP 800-38D](https://csrc.nist.gov/pubs/sp/800/38/d/final) -- Recommendation for Block Cipher Modes of Operation: Galois/Counter Mode (GCM) | CRYPTO-2 |
| AES (Rijndael) | [FIPS 197](https://csrc.nist.gov/pubs/fips/197/final) -- Advanced Encryption Standard | CRYPTO-2 |
| ChaCha20-Poly1305 | [RFC 8439](https://datatracker.ietf.org/doc/html/rfc8439) -- ChaCha20 and Poly1305 for IETF Protocols (obsoletes RFC 7539) | CRYPTO-2 |
| Argon2id | [RFC 9106](https://datatracker.ietf.org/doc/html/rfc9106) -- Argon2 Memory-Hard Function for Password Hashing and Proof-of-Work Applications | KDF-1 |
| scrypt | [RFC 7914](https://datatracker.ietf.org/doc/html/rfc7914) -- The scrypt Password-Based Key Derivation Function | KDF-1 |
| PBKDF2 | [NIST SP 800-132](https://csrc.nist.gov/pubs/sp/800/132/final) -- Recommendation for Password-Based Key Derivation | KDF-1 |
| HKDF-SHA256 | [RFC 5869](https://datatracker.ietf.org/doc/html/rfc5869) -- HMAC-based Extract-and-Expand Key Derivation Function | SIG-2 |
| HMAC-SHA256 | [RFC 2104](https://datatracker.ietf.org/doc/html/rfc2104) -- HMAC: Keyed-Hashing for Message Authentication; [FIPS 198-1](https://csrc.nist.gov/pubs/fips/198-1/final) | SIG-1, SIG-6 through SIG-11 |
| SHA-256 | [FIPS 180-4](https://csrc.nist.gov/pubs/fips/180-4/upd1/final) -- Secure Hash Standard | TOK-5 |
| ECDSA / NIST P-256 | [FIPS 186-5](https://csrc.nist.gov/pubs/fips/186/5/final) -- Digital Signature Standard (DSS) | §14.5.2 Option A |
| Ed25519 | [RFC 8032](https://datatracker.ietf.org/doc/html/rfc8032) -- Edwards-Curve Digital Signature Algorithm (EdDSA) | §14.5.2 Option A |
| OAuth 2.0 Token Exchange | [RFC 8693](https://datatracker.ietf.org/doc/html/rfc8693) -- OAuth 2.0 Token Exchange | §14.5.2 Option B; CONF-L3-3 |
| OAuth 2.0 Token Introspection | [RFC 7662](https://datatracker.ietf.org/doc/html/rfc7662) -- OAuth 2.0 Token Introspection | §14.5.2 Option B |

---

Next: [Audit and Observability](15-audit-observability.md)
