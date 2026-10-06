# Durable project knowledge

## Project identity
QRDrop: Phone → Computer, local LAN, no phone installation or account. Reference: `docs/MVP.md`, original user product brief.
## Confirmed business facts
No cloud file relay/account/Internet runtime requirement. User will test on PC; wants GitHub builds for exe/dmg/Linux. Pricing/KPI [CHƯA XÁC NHẬN].
## Architecture decisions
- Date: 2026-10-06; Status: Confirmed (implementation choice); Reason: keep privilege boundary explicit; Decision: native desktop control via Tauri IPC, restricted mobile Axum API; Source: `commands.rs`, `server.rs`.
- Date: 2026-10-06; Status: Confirmed (implementation choice); Reason: bounded memory and idempotent retry for large files; Decision: sequential 8MiB binary chunks with approved manifest; Source: `transfer.rs`, `docs/MVP.md`.
## Technical decisions
- Date: 2026-10-06; Status: Confirmed; Reason: opaque byte preservation and no overwrite; Decision: cap-std directory handles, staged files, SHA-256 disk readback and hard-link no-clobber publication; Source: `files.rs`, `hash.rs`. Unsupported filesystem publication fails rather than overwrites.
- Date: 2026-10-06; Status: Confirmed; Reason: project-local toolchain already has Node/TS; Decision: built-in Node SQLite, TS AST and clearly marked Rust lexical fallback; Source: `tools/codeintel/README.md`. Index has no secret values.
- Date: 2026-10-06; Status: Confirmed; Reason: WebCrypto digest is unavailable for this HTTP/streaming use; Decision: small incremental SHA-256 Worker implementation, checked against independent Node crypto; Source: `src/utils/sha256.mjs`, `tools/tests/sha256.test.mjs`. Not used for token generation or encryption.
## Product decisions
HTTP trusted-LAN scope; no claim of encryption or original Photos retrieval. Native iOS companion is future work. Source: product brief, `docs/MVP.md`.
## User preferences
Vietnamese communication. User's internal brief must be rewritten into product copy unless explicitly requested verbatim. User prefers action over repetitive confirmation; latest direct creation instruction was interpreted as authorization. Rules: `AGENT.md`.
2026-10-06: user explicitly authorized pushing to `https://github.com/truongminhkhanng/QRDrop`, requested memory updates and reaffirmed product-copy rules. Remove QRDrop-only temporary downloads/dependencies/build outputs after VPS testing; preserve source/history/source ZIP and unrelated project data.
## Important constraints
No fake transfers or success claims without end-to-end evidence; no global index daemon; no telemetry; no secret values in history/memory/index; minimal relevant changes.
## Key workflows
AGENT + MEMORY → selective context → status/update/explore → actual source → patch → verify → index/memory/history. Native CI builds separate from runtime LAN transfer.
## Known pitfalls
Same Wi-Fi is not sufficient under client isolation/firewall. Safari may supply converted photo objects and suspend background tabs. std::fs::rename can overwrite. Chunk ACK is not durable restart recovery. Old QR invalidation depends on credentials, not a permanently unique port.
## Experiments and results
2026-10-06: frontend strict build passed; browser hasher matched Node crypto including padding boundaries and >8MiB data. Code index fixture tests passed. Rust build blocked by missing cached Axum and restricted network; NOT evidence of compile/runtime success.
2026-10-06 VPS follow-up: incremental browser hasher matched independent Node crypto for 4,303,355,907 bytes using one reusable 8MiB buffer; ~135 seconds, peak Node RSS ~79MiB. Mobile API network-retry regression reproduced and fixed; four unit cases passed. These are Node/unit observations, not real Safari/LAN transfer evidence. Source: `tools/tests/sha256-large.mjs`, `tools/tests/mobile-api.test.mjs`, `HISTORY/2026-10-06.md` Interaction 004.
## Rejected approaches
Status: Rejected — cloud relay/global indexing service; unnecessary for LAN/local structural memory. Rejected — full-file RAM hashing, massive multipart batch, using QR token as upload grant, arbitrary filename paths, unconditional final rename.
## Things future agents must not forget
Never treat graph confidence/history as current source truth. Never say original HEIC recovered from Safari-provided JPG. Never label server-only hash as source MATCH. Resolve and commit Cargo.lock on first network-enabled host; test actual native builds and phones before release claims.
