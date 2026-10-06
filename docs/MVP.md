# QRDrop MVP — implementation contract

## Identity and scope
Phone → Computer, reachable private IPv4 LAN. Phone camera/browser only. No runtime cloud/account/relay/Internet requirement. No image processing or extension whitelist. Preserve browser-supplied bytes including embedded metadata, not filesystem metadata or original Apple Photos resources. Initial UI Vietnamese; internal brief is not literal UI copy.

## Trust boundary
HTTP trusted LAN only: no confidentiality, TLS or MITM guarantee. QR token ≥256 bits from Rust OS CSPRNG. Device/browser labels are unverified client descriptions; socket peer IP is informative, not authentication. No public/wildcard binding, router forwarding or automatic network changes. Guest isolation/firewall can still prevent connection.

## Session
One receiver session, one pending/approved sender, one immutable manifest, one disk operation at a time. Listener bound before QR. GET doesn't consume QR. Pending request consumes the opportunity to claim the batch; exact connect retry is idempotent. Join token never grants upload. Accept/Reject only desktop IPC; Reject is terminal. Destination frozen for session.

States: WAITING → WAITING_FOR_APPROVAL → APPROVED → TRANSFERRING → VERIFYING → COMPLETED. Terminal alternatives: REJECTED/EXPIRED/CANCELLED/FAILED/PARTIALLY_COMPLETED. Partial completion retains verified files. Terminal invalidates join/upload credentials. Attempt credential can read final receipt for up to 30s, never upload. Listener then shuts down. Receive Again creates new credentials/session; OS may reuse a port.

Deadlines: 10m creation→approval; 2m approval→first data; 5m without transfer/verification progress; 24h approved session maximum; 90s inactive chunk/transport. Polling alone doesn't extend transfer. Clock is monotonic for enforcement; wall time for display.

## Protocol
`POST /api/connect`: bounded JSON token/request_id/device/files; reply attempt token and chunk size. First valid request freezes IDs/name/size/order. Exact request retries retrieve the same attempt; changed metadata/new attempt denied.

`GET /api/status`: attempt bearer token; state/files and upload grant only after approval while active. No server filesystem paths served to mobile.

`PUT /api/files/{id}/chunks`: upload bearer, binary body, matching Content-Length, X-QRDrop-Offset/Length/SHA256. Maximum 8MiB; streamed frames to disk. ACK after complete write/digest match. Last-ACK retry doesn't append. Interrupted chunk truncates to ACK boundary; unexpected offsets/content rejected. ACK is not durable crash recovery.

`POST /api/files/{id}/finish`: expected whole-file SHA256; 202 starts background bounded-memory disk readback. Poll for verifying→complete or failure. Duplicate finish cannot publish again. Zero-byte supported.

`POST /api/complete`: only after all files complete; revoke writes and retain read-only receipt briefly. `POST /api/cancel`: own attempt only; revoke immediately and cleanup after active disk operation exits.

No multipart endpoint in MVP. No arbitrary filesystem/download/admin API. Host/Origin validation, no wildcard CORS, cap on connections 64/active requests 16, connect 10/IP/min and bounded rate-map. Manifest ≤1000 files/1MiB; filenames ≤240 UTF-8 bytes before collision suffix; totals limited to exact browser integer representation. Extremely slow/hostile peers can still degrade availability; local listener limits reduce resource growth, not absolute DoS prevention.

## File lifecycle
Owned staging directory under selected destination, same filesystem. Directory capabilities confine path resolution; filenames never select a desktop path. Reject separators/traversal/NUL, normalize invalid/reserved/control/bidi names and show saved names. Files written create-new, no entire-file RAM buffer.

Hash in browser Worker reads bounded chunks once; independently hashes each chunk and whole-file byte stream. Rust flushes/syncs then rereads the actual file in bounded buffers. Matching digest required before publish. Extra CPU/battery and disk read are intentional tradeoffs.

Publication uses directory-relative hard-link creation without replacement, then removes temp link. Existing filename gets numeric suffix preserving final extension. A bounded preflight checks filesystem support before approval/upload. Filesystems without safe supported publication (including typical exFAT/FAT configurations) fail; choose another destination rather than use an unsafe overwrite fallback. Final file bytes verified; power-loss durability of directory metadata is not guaranteed uniformly across every OS/filesystem. No file auto-execution/preview/extraction.

Settings/recent and owner journal in native app-data; credentials RAM only. On normal termination close handles before cleanup. After crash, only UUID partials in journal-owned directory are removed; unknown contents/corrupt journal cause explicit manual-recovery error. Cleanup never deletes general Downloads `.part` files. Local malicious processes with same OS privileges are outside scope.

## Failures and compatibility
Network interruption: same live page/session retries; changed desktop address requires new QR. Lock/background/reload: no reliable continuation. Disk full/permission/removable-drive error: fail, don't publish incomplete bytes. Completed files remain under partial-completion result. Old QR/grants invalid. No LAN: actionable message, no ready QR.

Original Photos, Live Photo structure, full folder trees, multi-sender/parallel transfer, persistent resume, native mobile, IPv6/Bonjour, TLS and PC→Phone are future work.

## Distribution and unconfirmed items
CI native Windows x64 setup.exe; macOS ARM64 dmg; Linux x64 AppImage/deb. This does not prove runtime compatibility. App identifier `app.qrdrop.desktop`, minimum macOS 13.0, business KPI, pricing, signing credentials, tested OS/browser versions are provisional/[CHƯA XÁC NHẬN]. GitHub artifacts are test builds until real device acceptance is complete.

## Desktop receive controls (1.0.0)
Receiving starts disabled. Enable opens a new private-interface listener and QR. Disable terminates the active session, closes/joins the serving task, waits for disk rollback and cleans owned staging before releasing the session. Completed files remain. QR refresh performs disable then enable; a pending request/transfer needs user confirmation. Start/stop serialize on Manager.current so old cleanup cannot touch a new session journal. Late desktop events from an old session are ignored.
