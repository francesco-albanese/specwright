| Severity | Concern | Location | Why | Fix |
| --- | --- | --- | --- | --- |
| CRITICAL | secret leak | src/auth/login.ts:42 | API key hardcoded; example uses `key \| value` separator. | Move key to env var ANTHROPIC_API_KEY. Rotate the leaked key. |
| CRITICAL | data loss | src/db/migrate.ts:88 | Migration drops table without backup. | Add explicit backup step before DROP TABLE. |
| HIGH | missing acceptance criterion | src/api/route.ts:19 | Endpoint does not enforce auth. | Add bearer-token check; return 401 on missing header. |
| HIGH | test couples to internals | tests/auth.test.ts:30 | Test asserts on mock invocations rather than the public response. | Rewrite to assert on the 200 / 401 HTTP response shape. |
| MEDIUM | complexity | src/api/handler.ts:41 | Cyclomatic complexity 18 exceeds threshold of 10. | Extract the validation branch into a helper. |
| MEDIUM | complexity | src/service/sync.ts:42-58 | Block performs three responsibilities; hard to test. | Split into parse / transform / write helpers. |
| LOW | naming | src/util/format.ts:12 | Variable `tmp` is unclear. | Rename to `formattedRow`. |

What next?
[1] auto-fix all CRITICAL
[2] CRITICAL + HIGH
[3] pick individually
[4] file as new beads tasks
[5] skip
