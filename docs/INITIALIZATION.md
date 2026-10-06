# Báo cáo khởi tạo — 2026-10-06

1. **Files tạo:** AGENT/AGENTS/CLAUDE/CONFIG/SKILL/MEMORY/LONG_TERM_MEMORY, daily HISTORY + INDEX; npm/Cargo/Tauri/Vite config; desktop/mobile UI; Rust modules; HTTP tests; codeintel + hash tests; icons; native GitHub workflow; README/MVP/testing docs.
2. **Kiến trúc:** desktop IPC → Rust state/authorization/transfer/filesystem; phone cùng-origin Axum page/API. Current truth, structural cache, semantic memory và history tách biệt.
3. **Stack:** Tauri 2, Rust/Tokio/Axum, React 19, strict TypeScript/Vite; native dialog/opener dùng qua Rust. Không có app điện thoại/cloud runtime.
4. **Code intelligence:** project Node >=24 + TypeScript AST + built-in SQLite; Rust lexical fallback. Không global install/daemon/telemetry. Cache gitignored, rebuildable.
5. **Commands:** `npm run codeintel -- status|index|update|search|explore|callers|callees|impact`; query đặt sau command. Ví dụ `npm run codeintel -- explore "start_verification"`.
6. **Index:** 39 file, 704 symbol ở thời điểm báo cáo. Imports, calls, JSX renders, component→constant class/CSS hints, 9 Axum route-handler patterns, test hints, config keys. Confidence theo symbol/edge; unresolved target không phải quan hệ xác nhận. Xem tool README về giới hạn.
7. **Self-test:** 1 nhóm SHA-256 so với Node crypto và 2 nhóm code graph đều pass; graph có stale detection same-mtime/same-size, incremental/no-op update, deletion và exclusion secret. Status/index/search/explore/callers/callees hoạt động trên project. Strict TypeScript và cả hai production frontend build pass. JSON config, Cargo metadata (no dependencies) và workflow YAML parse được. **Cargo test không chạy tới compile do thiếu cached Axum/network; chưa verify native hoặc điện thoại.**
8. **Quyết định:** immutable manifest + approval; separate credentials; sequential 8MiB binary chunks; actual disk hash before no-clobber publish; preflight safe publication; no persistent resume; HTTP trusted LAN. UI copy chuyển brief thành nội dung sản phẩm. CI installers chỉ là build artifacts; tag tạo draft release.
9. **Chưa xác nhận:** identifier app.qrdrop.desktop, OS minimums/device/browser matrix, pricing/KPI và signing. Cargo.lock phải resolve trên host có mạng; không tạo lockfile/checksum giả.
10. **Next:** user đưa source lên GitHub → chạy workflow → sửa lỗi native nếu có → commit resolved Cargo.lock → tải bộ cài → test phone/PC và file lớn theo docs/TESTING.md. Build thành công chưa đủ để tuyên bố end-to-end.
11. **Session sau:** chỉ cần `@AGENT.md [task]`; selective context/index/source verification/history-memory workflow đã ghi trong entry point.

Source archive không chứa node_modules, target, credentials, generated cache hoặc build outputs. Nó không phải bộ cài executable. Chưa upload GitHub/chưa phát hành.
