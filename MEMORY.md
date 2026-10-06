# Working memory

## Last updated
2026-10-06 22:13, Asia/Ho_Chi_Minh. QRDrop 1.0.0 implemented, tested, published and verified. Bilingual user docs and public project listing prepared. Owner will manually make Public and apply About metadata. Context/history/durable decisions saved. Source ZIP validated: 78 maintained files, CRC and exact bytes/inclusion checks passed. Final upload contains documentation only.

## Release and source
[QRDrop 1.0.0](https://github.com/truongminhkhanng/QRDrop/releases/tag/v1.0.0): release ID 404865053, draft=false, prerelease=false; latest endpoint confirms v1.0.0. Four installers: Windows x64 exe (offline WebView2), Apple Silicon dmg, Linux x64 AppImage/deb. Users need no Node/npm/Rust. Repo remains private until owner changes it.

Application source 523b49acfec366390313bfedfda42992f05a5c01; native run 37482136952 SUCCESS. Tag 2ef17c68da39537f16a7d69fb1152d44d3f55c6c is the documentation/publication commit; 54 protected blobs independently match tested source/config/locks/tests/icons/tools. Publish run 37484962550 SUCCESS; runner verified actual installer bytes/SHA256 before copying to the separate stable release. Old v0.1.0/tag/installers and test drafts retained. See docs/BUILD_STATUS.md for asset digests/evidence.

## Receiver controls
Receiving starts off. Bật nhận tệp opens a new private-interface session/QR. Tắt nhận tệp revokes credentials, aborts/joins listener, serializes disk cleanup and retains completed files. Làm mới QR ends old session and creates fresh session/token; pending request/transfer asks confirmation. Late old-session events ignored. Two new real HTTP/disk regressions passed on all OS.

## Verification and resources
All three native runners passed strict frontend production builds, hash/index/mobile checks, real receiver suite (13 Windows/14 macOS/15 Linux), desktop check and native packaging with genuine locked dependencies. Local hash passed; npm ci fails EAI_AGAIN and TypeScript/Axum unavailable. Native/publication evidence comes from GitHub. Restored CI-generated index after SHA256/SQLite integrity checks: 43 files/819 symbols, actual scan/freshness functions confirm fresh. No installer on VPS. Removed 401408 bytes (0.383 MiB) of owned temporary cache/export/check files. Dependencies/build outputs absent. Preserve source/locks/history/index/source ZIP; restore npm ci/build for future work. No usable .git; writes use GitHub expected-head lease.

## User preferences/public preparation
README.md English, README.vi.md Vietnamese with language links; user instructions/install/help/privacy only, no internal agent/build brief. Release notes and security docs bilingual (SECURITY.md/SECURITY.vi.md). App remains Vietnamese; an app language switch was not requested explicitly. Latest user chose to make Public manually after preparation, superseding prior private-only preference. Connected tools cannot mutate visibility/About, local gh auth/network unavailable. About description/website/topics prepared in .github/PROJECT_ABOUT.md; metadata still unset. Never claim it changed.

## Security and device acceptance
256-bit one-request QR credential with identical same-peer retry, immutable desktop approval, separate grant, peer plus credential, private IPv4/ephemeral port, bounded chunks/SHA256/no overwrite. HTTP unencrypted; IP/port/hash do not prevent interception/MITM. Real PC/phone installation/transfers, multi-GB phone RAM/network, firewall/disk/filesystem acceptance pending. Windows unsigned, macOS ad-hoc/no notarization, Apple Silicon only/minimum configured 13.0. Regular release status is not proof of real-device acceptance. Do not move published tags or replace installers.
