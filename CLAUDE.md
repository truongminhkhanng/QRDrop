> **Đây là file luật nền để AI hiểu nguyên tắc và kiến trúc project. Không phải toàn bộ nội dung phải được load ở mọi task; chỉ đọc section liên quan khi cần.**

## Project overview
QRDrop receives phone files over a reachable LAN using a QR/browser and mandatory desktop approval. Product contract: `docs/MVP.md`.
## Goals
Simple utility UI, opaque bytes, safe bounded-memory receiver, local-only operation, project-local agent context/index, native installers through CI.
## Non-goals
Cloud transfer/accounts; processing images; original Photos guarantee; background phone upload; durable resume; multiple senders; folder sync.
## Stack
Tauri 2, Rust, Tokio, Axum, React, strict TypeScript, Vite. Browser integrity hasher: bounded incremental SHA-256 Worker, tested independently against Node crypto. Tooling: project Node >=24/TypeScript + built-in SQLite; no global indexing service.
## Architecture
`commands.rs` is desktop-only control; `server.rs` exposes a restricted mobile API. `session.rs` owns state; `transfer.rs` serializes disk operations and authorization; `files.rs` uses directory capabilities and no-clobber publication; `hash.rs` verifies actual disk bytes. Mobile and desktop are separate builds. Rust embedded assets require `mobile-dist` from frontend build first.
## Directory structure
`src/desktop`, `src/mobile`, shared `src/types`, `src/utils`; Rust `src-tauri/src`; integration tests `src-tauri/tests`; `.github/workflows`; tool source `tools/codeintel`; derived cache `.agent`; semantic markdown at root; historical evidence `HISTORY`.
## Code style
Strict TS, no `any`; explicit boundary types. Rust handles `Result`; no unchecked panic for user input. No shell interpolation. Use small functions and error codes. No source/credentials uploaded for indexing.
## Naming conventions
Rust snake_case; React PascalCase; TS lowerCamelCase; JSON wire snake_case; session states SCREAMING_SNAKE_CASE, file states snake_case.
## Testing rules
Target behavior/security first. `npm run build`, `test:hash`, `test:codeintel`. Cargo HTTP integration tests are real network/disk operations; approval occurs through Manager, not a LAN admin API. CI compiles desktop separately. Phone Wi-Fi/iOS/10GB checks require real devices; don't substitute a browser mock for that claim.
## Deployment principles
Native OS build runners: Windows NSIS setup.exe; macOS ARM64 DMG; Linux x64 AppImage/deb. GitHub is only for source/build/distribution, not file transport. Draft releases only. Public macOS signing/notarization and Windows signing credentials remain unconfirmed. WebView2 offline installer increases Windows package size. AppImage compatibility is limited to tested distros.
## Security principles
Trust boundary is HTTP on a trusted LAN; no encryption claim. 256-bit Rust-generated credentials; immutable approval; deadlines; same-origin mutation checks; bounded connections and requests; no filesystem APIs remotely; no overwrite, traversal or automatic execution. No secret values in docs/history/cache. Privileged local software running as the same OS user is outside the security boundary.
## Agent editing rules
Latest user instructions prevail. Source/config/test is truth. Query index before broad crawling; verify source before patch. No blind global replace, unrelated cleanup, stack/public API/database/deployment change without scope authorization. Never invent business facts. Apply internal brief → product copy rule from `AGENT.md`.
## Code intelligence rules
Cache is optional/rebuildable; source never depends on it. TypeScript declarations/ranges/imports/constant classes come from AST. Rust is lexical fallback, NOT an AST/type-resolved compiler graph. Rust declarations/calls/routes, global CSS matching, cross-file name resolution and test hints have reduced confidence. Macros, traits dispatch, aliases, dynamic imports/classes and complete framework resolution are unsupported. Use targeted rg/source/browser tooling when omitted or uncertain. Incremental update reparses changed files; relationship resolution is regenerated globally from saved drafts so deleted/renamed targets can't leave confirmed stale links. Source hashes detect same-size/same-mtime changes.
