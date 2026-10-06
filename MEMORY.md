# Working memory

## Last updated
2026-10-06 07:08, Asia/Ho_Chi_Minh. VPS checks and cleanup completed; GitHub upload in progress.

## Current objective
Test QRDrop, remove temporary dependencies/download caches after testing, and push source to the user-authorized private repository `truongminhkhanng/QRDrop`. Save memory/history and use product language for end users. User will test on their PC.

## Current project state
New workspace had no source or usable Git metadata. Tauri/Rust/React scaffold and real receiver source, HTTP integration tests, native build workflow, icons, docs and context created. Desktop/mobile TypeScript builds passed. Product uses HTTP on trusted LAN; no TLS/MITM guarantee. Desktop and mobile are separate bundled entry points.

## Recent changes
Fixed mobile status polling: network error status 0 now retries instead of stopping immediately. Four API regression cases passed after reproducing the failure. Added opt-in large-hash check; equivalent stress run matched Node crypto on 4,303,355,907 bytes in 135 seconds, peak Node RSS ~79 MiB; no multi-GB file created. Strict TypeScript and both frontend builds passed after fix; hash and graph fixture checks passed. Fresh graph: 41 files/727 symbols. CI now includes mobile API tests. Removed project node_modules/build outputs and QRDrop-only /tmp dependency caches; freed 285.74 MiB. Source, generated index and source ZIP kept. Restore `npm ci` and `npm run build` before next native check.

## Active decisions
Latest user request “tao cho tao đi” interpreted in context as permission to create after repeated creation requests; prior approval gate was not kept as a blocker. Single approved immutable batch, one sender, sequential 8MiB chunks; no browser-reload/app-restart resume. QR deadline applies before approval. Preserve browser-supplied bytes, not original Photos resources. Runtime transfer never depends on GitHub/cloud.

## Active hypotheses
Provisional identifier app.qrdrop.desktop and configured macOS minimum 13.0 need confirmation/testing. Filename capability APIs and native filesystem behavior need compiled integration tests.

## Open issues
VPS cannot resolve index.crates.io or github.com. GitHub connector can access the authorized repository; initial main commit contains only README. Cargo test --offline stopped before compilation because Axum was unavailable. Cargo.lock unresolved. Rust/native/installers/real phone path NOT verified yet. Large-hash Node test is not proof of 10GB phone transfer or phone RAM. HTTP limitations and signing gaps remain.

## Next actions
Push reviewed source through GitHub connector, verify remote contents and check workflow results. Resolve/commit Cargo.lock after successful CI resolution; fix native errors before installer claims. User tests real phone/PC, multi-GB transfers, interruption, firewall, disk full and crash recovery. Confirm identifier/platform minimums and signing before public distribution.
