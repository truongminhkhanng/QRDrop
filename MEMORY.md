# Working memory

## Last updated
2026-10-06 22:00, Asia/Ho_Chi_Minh. QRDrop 1.0.0 receiver controls implemented; native build and stable publication in progress. User wants actual new release/tag, product wording, bilingual English/Vietnamese README and release notes, About metadata, public visibility after completion, and saved context.

## Current source/build
Repo: https://github.com/truongminhkhanng/QRDrop (currently private). Tested candidate source 523b49acfec366390313bfedfda42992f05a5c01; exact native run 37482136952. New publisher .github/workflows/release-v1.0.0.yml checks source/run, three successful jobs, protected tree equality, actual downloaded installer bytes/SHA256, creates a separate stable release and publishes latest. Old v0.1.0/tag/installers retained. Publisher early push 37482552967 succeeded by waiting for the build; this does not prove publication.

## Receive behavior
App starts off. Bật nhận tệp enables a new session; Tắt nhận tệp revokes credentials, aborts/joins listener, serializes disk cleanup, keeps completed files. Làm mới QR stops old session then creates fresh session/token; pending requests/transfers ask confirmation. Desktop ignores late old-session events. Headless integration tests cover stop with an idle socket, immediate port closure, re-enable and old token denial, preserving completed/unrelated files and cleaning owned incomplete staging.

## Language and publication preferences
README.md is English user documentation, README.vi.md Vietnamese with language links; no agent/build/internal brief in README. Release notes are bilingual. App remains Vietnamese; no application language switch was explicitly requested. User superseded earlier private-only preference and authorized Public after completion. User will change visibility to Public manually after preparation. Tools expose source/releases but not repository visibility/About mutation. Local gh has no usable connection (authentication/network checks fail). Do not claim these settings changed. Concrete About fields prepared in .github/PROJECT_ABOUT.md.

## Verification/resources
Local SHA256 regression passed. npm ci fails EAI_AGAIN; TypeScript cache and Rust Axum unavailable. Source reviewed with targeted rg fallback. Native CI uses genuine locked dependencies. Publisher refreshes code index and exports derived SQLite/state through logs for local restore. Do not download installers to VPS. Preserve source/locks/history/index and source ZIP; clean owned dependencies/temp files after work. No usable local .git; GitHub writes use expected-head lease.

## Security/acceptance
One-request 256-bit QR credential, immutable approved manifest, separate upload grant, selected peer plus credential, private IPv4/ephemeral port, bounded chunks, SHA256/no overwrite. HTTP unencrypted; IP/port/hash do not prevent interception/MITM. Real PC/iPhone/Android installation/transfers, multi-GB phone transfer, firewall/disk/filesystem acceptance remain pending. Windows unsigned; Mac Apple Silicon only/ad-hoc/no notarization, configured minimum 13.0. Installer users need no Node/npm/Rust.

## Remaining
Await native build, verify stable release/tag/four asset digests. Record actual results and any public/About capability block. Restore fresh index, update final docs/memory/history/long-term, source ZIP and cleanup; push and verify maintained files. Do not move published tags or replace published installers.
