# QRDrop 1.0.0 — build and release results

Verified: 2026-10-06 22:13, Asia/Ho_Chi_Minh.

[QRDrop 1.0.0](https://github.com/truongminhkhanng/QRDrop/releases/tag/v1.0.0) is published as a regular release: `draft=false`, `prerelease=false`, release ID `404865053`. GitHub's latest-release endpoint resolves to v1.0.0. All four installers are uploaded.

Application source: `523b49acfec366390313bfedfda42992f05a5c01`. [Native build and tests 37482136952](https://github.com/truongminhkhanng/QRDrop/actions/runs/37482136952) succeeded on Windows x64, macOS Apple Silicon ARM64 and Ubuntu 24.04 x64.

[Publication 37484962550](https://github.com/truongminhkhanng/QRDrop/actions/runs/37484962550) succeeded. Tag `v1.0.0` points to `2ef17c68da39537f16a7d69fb1152d44d3f55c6c`. Independently verified **54 protected Git blobs** match the tested application/config/lock/test/icon/tool source. Only documentation and the new publication workflow differ from the build source.

## Changes in this version

- Receiving starts off; explicit desktop enable/disable controls.
- Disabling revokes credentials, closes/joins the listener, waits for disk operations and cleans owned incomplete staging. Completed files stay intact.
- QR refresh ends the old session and creates a new QR/credential. Pending requests/transfers ask confirmation. Old session events cannot repopulate the disabled desktop UI.
- English/Vietnamese user README, bilingual release notes and security documentation. Application UI remains Vietnamese.

## Automated verification

All three native jobs passed strict TypeScript/desktop/mobile production builds, SHA-256 regression, two code-index fixtures, four mobile API regressions, real receiver tests, desktop Cargo check and native packaging. Dependencies were installed with `npm ci` and Cargo `--locked`.

Receiver tests: **13 Windows / 14 macOS / 15 Linux**, zero failures. The two new real listener/disk cases passed on each OS:

1. Manager starts disabled; stop is idempotent, closes the port within the test deadline despite an idle socket, and re-enabling changes the session/token. An old QR credential is rejected by the new listener.
2. Stopping an approved partial transfer preserves completed and unrelated files, removes owned incomplete staging, revokes the grant and permits a new session.

Existing approval/input/Origin/replay/hash/no-overwrite/expiry/cancellation regressions passed. Unix symlink and Linux different-source-IP cases remain platform-specific. These are real HTTP/disk automation, not real phone installation or LAN acceptance.

## Installers and SHA-256

| Installer | Bytes | SHA-256 |
|---|---:|---|
| QRDrop_1.0.0_aarch64.dmg | 4005291 | `2001b0bc74fdfdbb0533ce4f892167e172f848be291906cd1fd9ffea0d46ec95` |
| QRDrop_1.0.0_amd64.AppImage | 80476664 | `a392b732e42a1178dbeed016048520d33413a86e886149ebd52e9e9e8b3cccdc` |
| QRDrop_1.0.0_amd64.deb | 4961130 | `8ec37aefe813c58ebe02c63e08b5268915ce12cfce7d063d2931e349bf45abf7` |
| QRDrop_1.0.0_x64-setup.exe | 218094443 | `d8b5e41b11d0b638dc7ed5429ecd6407283cd8f3abdb0d8a34474167fd0c2040` |

A separate version release was created; the source test draft was retained. On the GitHub publication runner, actual downloaded installer bytes were hashed and compared with source metadata before upload. The published assets' names, sizes and digests match the verified test assets. No installer was downloaded to the VPS. The previous v0.1.0 release/tag/installers remain intact; see [its build report](BUILD_STATUS_v0.1.0.md).

## Locked dependencies and local resources

| Lockfile | SHA-256 |
|---|---|
| package-lock.json | `e608e2edd60c752fdcd699b5eeba0064b36d257485c87d092e251bdbca4d7b43` |
| src-tauri/Cargo.lock | `00724ea692de0e3ae68574dd7bd6cd8ffc9cb00e535b0b6028a0e5347dc3d0c5` |

The dependency graph/checksums were preserved; only QRDrop's own version became 1.0.0. Rust Tauri and npm API remain 2.12.1.

VPS npm restoration failed EAI_AGAIN and cached TypeScript/Axum were unavailable. Local SHA-256 regression passed; frontend/native evidence comes from the successful GitHub jobs. The publication runner generated a fresh code index using locked TypeScript. Derived SQLite/state were restored locally after export SHA-256 and SQLite integrity checks: **43 files / 819 symbols**. The actual index tool's scan/freshness functions verified `stale=false`, matching every source and manifest hash without needing the absent TypeScript parser locally.

Owned temporary npm cache/export/syntax-check files removed: **401408 allocated bytes (0.383 MiB)**. Dependencies/build outputs absent; source, locks, index and source ZIP retained. Restore `npm ci` and frontend builds before future source verification.

## Public project preparation

README.md is English, README.vi.md Vietnamese, with language links and installation/receiving/help/privacy instructions. Internal agent/build briefs are absent from both READMEs. About description, website and topics are prepared in [.github/PROJECT_ABOUT.md](../.github/PROJECT_ABOUT.md).

Repository remains private and About metadata is unset at verification. The owner explicitly chose to apply Public visibility manually. The connected source/release tools do not expose visibility/About administration; these settings were not changed or claimed to be changed. Both READMEs explain access conditionally and remain accurate after the owner makes the repository public.

## Acceptance boundary

Real user PC/iPhone/Android installation and file transfers, multi-GB phone uploads/RAM, firewall, disk-full and filesystem compatibility remain pending. See [TESTING.md](TESTING.md). HTTP remains unencrypted; tokens/IP/ports/hashes do not provide confidentiality or MITM protection.

Windows lacks a publisher signature. macOS is ad-hoc signed, without Developer ID/notarization; Apple Silicon only, configured minimum 13.0. There is no Mac Intel installer and no claim of support for every Linux distribution. Stable release metadata records the user's requested release status; it does not substitute for device acceptance.
