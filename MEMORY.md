# Working memory

## Last updated
2026-10-06 20:31, Asia/Ho_Chi_Minh. User requests completing all remaining work. Vietnamese error wording updated; source and genuine lockfiles pushed at 27c1ad2a3c091b3ac3ee8ee97e940a6571dc5e89. Native build run 37468085213 is superseded by security source f118e962e0af655e43e5f061b06cabe434ff0eec, run 37471485522. v0.1.0 publication is authorized within the private repository, gated to this exact run/source.

## Current objective / handoff
Finish three-platform native CI, verify the four newly built installers, publish v0.1.0 prerelease, update final documentation/archive/memory and remove owned temporary tooling/cache. Device installation and iPhone/Android LAN acceptance require user's hardware; never claim they were run here. Do not change repository visibility.

## Verified current work
Localized Offset/chunk/hash/storage/server/folder errors; removed raw runtime details from UI and Worker errors. Worker creation is now inside the guarded send operation so startup failure releases the busy state. Upload protocol/status codes, approval and file lifecycle are unchanged. Local hash, four mobile API cases and code-index tests pass. Index refreshed (41 files/722 symbols before adding release workflow).

npm ci fails with EAI_AGAIN; local frontend/native build cannot run because dependencies are absent (offline Cargo lacks Axum). Restored SHA-512-verified cached TypeScript 5.9.2 for tooling only; locked CI uses 5.9.3. CI now uses genuine committed npm/Cargo locks, matched Tauri 2.12.1, npm ci and Cargo --locked.

## Remote state and previous evidence
Authorized repo https://github.com/truongminhkhanng/QRDrop remains private. Previous source 5378dc13f756edd3a0afe6b5ae0c365fd127316b passed run 37401346039 on Windows/macOS/Linux. Its draft ID 404232651 contains four historical installers; they lack today's wording changes and will not be promoted as the new version. New source is 27c1ad2a3c091b3ac3ee8ee97e940a6571dc5e89, run 37468085213. Inspect live run/main/release before final claims. No usable local .git; use connected GitHub tools with branch lease.

## Release workflow
.github/workflows/release-v0.1.0.yml publishes only after successful push run 37468085213 at exact source 27c1ad2. Verifies private repo, all three successful jobs, matching draft, exactly four uploaded installers and SHA-256 metadata, version/tag conflicts and unchanged assets. Reuses new draft assets without downloading installers to VPS. Publishes prerelease with product notes and generated digest table. Earlier publisher was disabled at 60b8425. Re-enable only for final security source f118e962 and run 37471485522; documentation push is pending at this checkpoint.

## VPS / acceptance
Retain source, genuine locks, history, index and artifacts/QRDrop-source.zip. Cleanup after verification: node_modules, owned /tmp/qrdrop-final-npm and publish-script/head scratch files; do not remove unrelated caches/projects. Historical cleanup totaled 285.74 MiB and 22.953 MiB in separate rounds. HTTP trusted LAN; no TLS/MITM/original Photos guarantee. No real device installation, multi-GB phone transport/RAM, firewall/disk-full/platform acceptance. Windows unsigned; macOS ad-hoc, no Developer ID/notarization. Mac Intel installer absent; macOS minimum 13.0 and Linux distro support remain device acceptance gaps.

## Security steering
User asks about one-use tokens, server input validation and ports. Consume join credential at first valid request; hide consumed QR; bind API access and identical retries to selected peer (race-safe connect lock). Added real HTTP tests for once-only token/retry and invalid input, plus Linux test with a different socket source IP for stolen attempt/grant/cancel denial. Source f118e962 is pushed; final native checks pending. HTTPS is a future transport/trust setup change, not implemented; never claim IP binding protects against LAN interception.
