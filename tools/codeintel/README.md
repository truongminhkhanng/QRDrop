# QRDrop project-local code intelligence

Node >=24 (already QRDrop's frontend build runtime), the project's TypeScript compiler, and built-in `node:sqlite`. No Python/global npm package, daemon, cloud, telemetry or database server. SQLite cache and JSON state are gitignored; rebuild from project files at any time.

```bash
npm ci
npm run codeintel -- status
npm run codeintel -- index
npm run codeintel -- update
npm run codeintel -- search start_verification
npm run codeintel -- explore "approval upload"
npm run codeintel -- callers authorize
npm run codeintel -- callees connect
npm run codeintel -- impact receive-area
npm run test:codeintel
```

All output is JSON. Source paths/ranges are for direct inspection. `status` reports initial existence, hashes, changed/deleted files, manifest/lock hashes, time, schema/tool version. Queries fail when stale. `update` reparses changed files only; a full index is used for initial/schema/tool-version change. Resolved edges are regenerated from saved edge drafts, not by reparsing unchanged files. `index` explicitly forces a full rebuild.

Storage: `.agent/codegraph.sqlite` tables `files`, `symbols`, `edges`, `edge_drafts`, `meta`; `.agent/codegraph-state.json` is informational. SQLite metadata is authoritative only about this derived cache. No source bodies or signatures/values are stored; line ranges point to real source. Search compares normalized symbol names/path/kind; it is not semantic embedding search. `explore` returns relevant symbols/files/edges/routes/tests/impact hints, not generated claims about business logic.

## Coverage and confidence
- TypeScript/TSX/JS: AST declarations, qualified methods, ranges, imports, exports, calls, JSX child components and constant className relationships.
- Rust: lexical fallback declarations/ranges, imports, call names and Axum route-to-handler patterns. Confidence ~0.4–0.75. NOT Rust AST/type checking; no reliable traits, implementations, macro expansion or method dispatch.
- CSS: selectors and custom-property declarations. Component→global selector matches are heuristic (~0.6); dynamic class expressions are omitted.
- JSON/TOML/YAML: key names only, never values.
- Imports resolved locally when unambiguous. Same-name call resolution is a hint, particularly cross-file; aliases/scopes may invalidate it. Unresolved `call:`, `import:`, `rust_module:`, `style:` targets remain explicitly unresolved.
- Test-to-source and recommended integration tests are hints, not confirmed test coverage. No complete inheritance/reference/config-consumer graph.

Use `rg` and real source for unsupported/ambiguous relationships. Do not patch from cache alone. UI: trace class/token declaration and all uses before changing shared styles. `explore` can return broad neighborhoods for broad terms; refine to a symbol/component.

## Security
Ignores symlinks, generated folders, history/semantic memory, env/key/credential files and large files. `.agent/codegraph-ignore` adds project-local glob rules. Sensitive config keys may be indexed as names; values are not. Manifest/lockfiles are hashed for freshness, not copied. Never pass real credentials as CLI queries. No network calls or source/path/query uploads.

## Self-test
Fixtures prove initial status/index, AST search/explore, component→style, real route/caller hints, same-size/same-mtime hash invalidation, changed-only update, no-op update, deletion and secret-value exclusion. Tests use temporary directories and delete their fixtures.
