# QRDrop — AI entry point

> **ĐÂY LÀ ENTRY POINT CHÍNH CỦA AI TRONG PROJECT. USER CHỈ CẦN GỌI `@AGENT.md`. AGENT PHẢI TỰ LOAD CONTEXT CẦN THIẾT, DÙNG PROJECT-LOCAL CODE INTELLIGENCE KHI PHÙ HỢP, XÁC MINH SOURCE THẬT, THỰC HIỆN TASK, VERIFY VÀ CẬP NHẬT MEMORY/HISTORY.**

## Start every task
1. Read this file and `MEMORY.md` only by default.
2. Classify: UI micro change, bug fix, feature, API, database/schema, auth/security, config, integration, refactor, deployment, documentation, investigation, business/content.
3. Load only relevant sections from `CLAUDE.md`, `CONFIG.md`, `SKILL.md`. Read long-term decisions/history only when needed; don't load all context files.
4. Code task: `npm run codeintel -- status`; if stale/missing, `npm run codeintel -- update`; then `explore "task"`, `search`, `callers`, `callees`, `impact` as appropriate.
5. Open and verify actual source at reported ranges before any patch. Unresolved graph targets and heuristic edges aren't facts. Fallback: targeted `rg` and source reads.
6. Find the smallest correct scope; inspect shared callers/styles/config before changing them. No unrelated refactor, rewrite or global replace.
7. Verify targeted behavior; run required checks. Refresh index, append meaningful history, update working memory and durable decisions before returning the result.

## Source-of-truth hierarchy
Latest user instruction → current source/config/schema/tests → direct runtime/build/test evidence → derived code index → CONFIG → CLAUDE → LONG_TERM_MEMORY → MEMORY → HISTORY. History is past evidence, never current truth. Index/cache is rebuildable and never overrides source.

## QUY TẮC PHÂN BIỆT VĂN NỘI BỘ VÀ NỘI DUNG CHO NGƯỜI DÙNG
Lời người dùng trong trao đổi là **brief / yêu cầu nội bộ**: ý tưởng, ví dụ và cách vận hành. KHÔNG mặc định sao chép nguyên văn vào giao diện, placeholder, label, button, tooltip, thông báo, mô tả chức năng, heading hoặc hướng dẫn người dùng cuối.

Phải hiểu mục đích rồi viết thành ngôn ngữ sản phẩm phù hợp. Ví dụ:
- “cái nút này để bấm xóa hết” → button **Xóa tất cả**.
- “chỗ này khách nhập sđt” → label **Số điện thoại**, placeholder **Nhập số điện thoại**.
- “ví dụ 400.000đ đổi thành 150.000 VNĐ” là ví dụ chức năng; không biến thành placeholder. Dùng **Nhập nội dung cần tìm** và **Nhập nội dung thay thế**.

Chỉ giữ nguyên khi user nói rõ “giữ nguyên câu này”, “để đúng nội dung này”, “copy nguyên văn”, hoặc đó rõ ràng là dữ liệu cần hiển thị. Số liệu/câu chữ minh họa không tự trở thành UI. Khi không chắc, coi là chỉ dẫn nội bộ. Quy tắc này không ngăn history lưu brief làm bằng chứng; history không được dùng làm UI copy.

## QRDrop invariants
- Explicit desktop approval for an immutable manifest before any file bytes are written.
- QR join token creates one immutable request and is consumed at valid connect; identical retries from the selected peer recover the same reply. API credentials remain necessary; peer IP is an extra restriction, never identity proof. Never log credentials or put them into memory/history/index.
- Opaque bytes; no conversion/recompression. Only guarantee the browser-supplied file object, not original Photos resources.
- HTTP LAN is unencrypted. No claims of protection against LAN interception/MITM.
- Private selected IPv4 only; no UPnP, relay, cloud transfer or public binding.
- Bounded chunks/streaming/backpressure; `.part` until verified; never overwrite.
- Native folder APIs; no shell with user data. Remote pages get no Tauri IPC permissions.
- Build success is not phone-to-desktop end-to-end evidence. State verification gaps explicitly.

## UI micro-change
Visible element → route/entry → component → applied class/style/token → actual declaration → shared usage/impact → minimal patch → appropriate UI/build verification. A Header-only request must not modify a token used by Button/Footer/Alert.

## Recording
Meaningful interactions: append `HISTORY/YYYY-MM-DD.md` using the user's timezone (Asia/Ho_Chi_Minh), update `HISTORY/INDEX.md`. Never rewrite past entries. Keep `MEMORY.md` short (maximum ~700 words). Durable decisions include date, status, reason, source. Secret values become `[REDACTED SECRET]` or env variable names.

## Current commands
See `README.md` for setup and `tools/codeintel/README.md` for exact graph semantics. Default verification: frontend `npm run build`; hashes `npm run test:hash`; graph `npm run test:codeintel`; mobile API regressions `npm run test:mobile`; backend `cargo test --locked --manifest-path src-tauri/Cargo.toml --no-default-features`; desktop `npm run tauri -- build` on a supported build host. Large-input SHA-256 check is opt-in: `npm run test:hash:large`. Mobile assets must be built before compiling Rust. If dependencies/build output were cleaned to save VPS space, restore with `npm ci` and `npm run build`; don't assume generated files exist.
