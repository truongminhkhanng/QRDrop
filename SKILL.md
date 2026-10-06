# Project workflows (read relevant section only)

## start-new-session
Read AGENT → MEMORY → classify task → relevant context sections only → code index if code task → inspect actual source → execute. Don't ask the user to tag every memory file.
## inspect-code-with-local-index
`npm run codeintel -- status`; `update` if stale; `explore "task"`/`search`; collect paths/symbol ranges; inspect source and validate relationships. `callers`/`callees`/`impact` are hints with confidence, not compiler proof. Fallback to targeted rg when uncertain.
## make-minimal-change
Define exact scope; inspect callers/impact and shared usage; minimal patch; no unrelated refactor; targeted verification; update index and memory/history. Report tests not run.
## ui-micro-change
Visible UI → desktop/mobile entry → component → class/token → CSS declaration → shared usage → local patch → build and browser check if available. Apply product-copy rule. Never replace every color/token globally for a local request.
## record-daily-interaction
Use local date/time Asia/Ho_Chi_Minh. Append meaningful interaction with Time/User Input/Agent Output/Actions Taken/Files Changed/Verification/Decisions/Memory Candidates. Preserve user wording when material, redact credentials. Update history index only for meaningful entries; no past rewrite.
## end-session-and-compress
Before final: append evidence/history; concise working memory; durable facts/decisions to long-term; architecture/config only if changed; index refresh if source changed. Don't copy source/transcript into memory.
## manage-memory
MEMORY = current work/open issues/next steps, max ~700 words. LONG_TERM = dated decisions with Confirmed/Hypothesis/Deprecated/Rejected, reason and source. HISTORY = append-only past evidence; index first to locate old entries.
## audit-receive-authorization
Trace QR join → attempt/manifest → desktop decision → upload grant → chunk/finish → terminal. Test unauthorized uploads, reject/expiry/replay and Accept/Reject race. Keep native control inaccessible via LAN.
## inspect-safe-file-lifecycle
Trace approved file ID → bounded chunk → rollback/ACK → disk hash → no-clobber publication → recent record → cleanup/journal. Check zero-byte, collisions, traversal, cap directory containment, storage errors and cancellation. Never remove unrelated `.part` files.
## prepare-native-test-build
Build both frontends first. Use committed npm/Cargo lockfiles and Cargo --locked. Run backend tests; compile Tauri on each native runner; retrieve installers from private draft releases (Actions artifacts for PR/public builds); real iPhone/Android LAN test on user's PC. Keep signing secrets outside repo. A successful build doesn't prove device compatibility.
