# Working memory

## Last updated
2026-10-06 21:21, Asia/Ho_Chi_Minh. Authorized remaining software work completed: Vietnamese error wording, token/peer hardening, source/locks/docs pushed, new three-platform native build successful, v0.1.0 prerelease published and verified. Final release/security records and source archive validated (72 maintained files, CRC/inclusion checks passed); documentation-only upload preserves published application/tag.

## Current state
Private repo: https://github.com/truongminhkhanng/QRDrop. Download: https://github.com/truongminhkhanng/QRDrop/releases/tag/v0.1.0. Release ID 404759440; draft=false, prerelease=true, four uploaded installers with SHA-256. Published source application f118e962e0af655e43e5f061b06cabe434ff0eec passed run 37471485522. Tag points to recording/publisher commit e97eaa26b92f4668572eb32d870fb2299dc89b01; 53 protected Git blobs independently verified identical to tested source. Publish run 37477828846 SUCCESS. Repository remains private. Previous drafts retained as historical builds.

## Verification
All runners passed strict frontend production builds, hash/index/mobile regressions, real receiver suite, desktop check and native packaging with npm ci and Cargo --locked. Receiver 11 Windows / 12 macOS / 13 Linux tests. Token consumption/retry, malformed input and Linux different-source-IP denial passed. Assets unchanged across publication. See docs/BUILD_STATUS.md for sizes/digests. Tauri Rust/npm API 2.12.1; genuine npm/Cargo locks preserved.

## Security / product
Join token consumed at first valid connect; immutable approved manifest. Identical retries recover original reply only from selected peer; API guard and locked connect check prevent another peer's access/race. Attempt/upload credentials remain required; IP is extra restriction, not identity. Private selected IPv4 with OS-assigned port, bounded requests/chunks, no overwrite. HTTP remains unencrypted; TLS/trust not implemented. UI errors now use Vietnamese product wording instead of Offset/chunk/hash/raw runtime details; includes storage/folder/Worker/settings messages. Worker startup is inside send try/finally.

## Resources / recording
VPS npm ci fails EAI_AGAIN; local native build lacks Axum. New build evidence is GitHub-native. Local hash/mobile/index checks passed using verified cached TS5.9.2 only for tooling; CI locked TS5.9.3. Index refreshed: 42 files/756 symbols; SQLite integrity ok. Removed node_modules, /tmp/qrdrop-final-npm and owned scratch files: 24092672 bytes (22.977 MiB). No installer downloaded to VPS. Keep source, locks, history, index and source ZIP. Restore npm ci/build before tooling/Cargo next time. No usable local .git; use GitHub tools with expected-head lease.

## Acceptance boundary
Real user PC installation/iPhone/Android LAN transfer remain pending, as do multi-GB phone transport/RAM, firewall/disk-full/filesystems. Windows unsigned, macOS ad-hoc (no notarization), no Mac Intel installer; macOS 13.0 minimum/Linux distro compatibility require device checks. Do not call the prerelease production accepted. SECURITY.md covers HTTP/IP/NAT/port limits. Publication permission preserves private repo visibility.

## Publisher behavior
.github/workflows/release-v0.1.0.yml is pinned to tested source/run. It verifies private repo, three successful jobs, four asset digests, protected tree equality and main head before tagging recording commit. GITHUB_TOKEN cannot tag older commits with different workflow files; use verified recording head. Do not move published version tag or silently replace installers in future work.
