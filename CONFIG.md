# QRDrop context map

## Business
Project: QRDrop. Description: phone → desktop LAN file receiver. Primary users: people transferring phone files to their computer. Business model/pricing: [CHƯA XÁC NHẬN]. Success metric: [CHƯA XÁC NHẬN]; suggested operational metric is successful byte-verified transfers, not yet a confirmed KPI.
## Product
Utility desktop app, Vietnamese UI initially, phone browser, explicit approval. `docs/MVP.md` is the product contract; examples in user briefs are not literal UI requirements.
## Features
Single session/batch/sender; files including zero-byte and arbitrary extensions; chunk retry within live session; SHA-256 before finalize; native folder selection/open; recent successful files. Source: `src-tauri/src/{session,transfer,files,commands}.rs`, `src/{desktop,mobile}/App.tsx`.
## Auth
No accounts. Rust random join/attempt/upload credentials, approval and state enforced server-side. Source: `auth.rs`, `session.rs`, `server.rs`. Actual credential values: [SECRET - ENV ONLY] for distribution credentials; session credentials are RAM ONLY, not env.
## Database
No product database server. Local settings/recent JSON and partial journal in OS app-data directory. Derived code index: `.agent/codegraph.sqlite`, rebuildable and gitignored.
## API
Same-origin `/api/connect`, `/api/status`, `/api/files/{id}/chunks`, `/api/files/{id}/finish`, `/api/complete`, `/api/cancel`. Wire definitions: `protocol.rs`; handlers: `server.rs`. No LAN approval or filesystem API.
## Integrations / External Services
No runtime cloud integration/analytics. Authorized source/build repository: `https://github.com/truongminhkhanng/QRDrop`. GitHub Actions builds artifacts only, independent of transfer. No third-party QR API/CDN.
## Pricing / Analytics / SEO
Pricing [CHƯA XÁC NHẬN]. Analytics absent. SEO not applicable to desktop utility; marketing website outside current scope.
## Deployment
`src-tauri/tauri.conf.json`, `.github/workflows/build.yml`. Provisional identifier `app.qrdrop.desktop` [CHƯA XÁC NHẬN]. macOS min config 13.0 is provisional, not proof of tested support. Windows x64 and Linux x64 build targets; ARM64 Windows/Linux postponed.
## Limits / Important Constants
Reference constants, don't duplicate technical config: `src-tauri/src/config.rs`; transport bounds: `server.rs`; chunk timeout: `transfer.rs`. QR approval deadline differs from authorized transfer deadline.
## Environment Variables
Runtime has no required env credentials. CI signing, when configured: APPLE_CERTIFICATE, APPLE_CERTIFICATE_PASSWORD, APPLE_SIGNING_IDENTITY, APPLE_ID, APPLE_PASSWORD, APPLE_TEAM_ID — [SECRET - ENV ONLY]. Never store values here. Signing not enabled until configured.
## Feature Flags
Cargo `desktop` gates Tauri for headless backend tests. `allow_loopback` exists only in test/headless APIs, desktop network selection never offers loopback. No user-facing production flags.
## Important Paths
Default: OS Downloads/QRDrop (`config.rs`). Session destination is frozen. Settings apply next session. `.qrdrop-partials/<uuid>` holds owned staging. `README.md` and `docs/TESTING.md` explain running/testing.
