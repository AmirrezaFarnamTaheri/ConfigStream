# GitHub Actions failure review — 2026-09-23

This review covers 17 failed runs returned by the recent Actions history, from
2026-09-21 through 2026-09-23. A failed run is evidence of a failed workflow,
not necessarily a distinct defect. Cancelled and intentionally skipped runs are
excluded. Run pages and their annotations were checked where available. The
user supplied the candidate and diagnostic artifacts for runs 35886483930
and 35813615380, the live smoke artifact for 35885481460, plus five
production validation artifacts. GitHub API metadata became
available later in the review, but log and artifact downloads still timed out
at the Actions storage hosts.

## Recent action pin and validation cluster

| Run | Workflow | Observed failure |
| --- | --- | --- |
| [35886483924](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35886483924) | CI | All three Python jobs failed at action pin validation. |
| [35886483930](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35886483930) | Config's Stream | Static validation failed; the downstream merge also could not download the source matrix that the skipped matrix job never produced. |
| [35885989067](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35885989067) | CI, Dependabot PR | All three Python jobs failed; the PR changed an action pin while the manifest was stale. |
| [35885989091](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35885989091) | Config's Stream, Dependabot PR | Static and unit validation failed before downstream jobs ran. |
| [35885857855](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35885857855) | CI | All three Python jobs failed. Local reproduction at this revision shows manifest drift. |
| [35885857971](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35885857971) | Config's Stream | Static validation failed and the absent source matrix caused an additional downstream failure. |
| [35886564696](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35886564696) | Dependabot Supply Chain Evidence | `Refresh evidence on the Dependabot head branch` failed after PR #635 merged and its head ref disappeared; stale-ref 404 is the most likely cause. |

At commit `4698fd45b`, `python scripts/validate_action_pins.py` reproduced
manifest errors: missing entries for action versions now used by workflows,
two mismatched `deploy-pages` references, and four unused old entries. The
manifest was reconciled with the immutable workflow SHAs. The `deploy-pages`
SHA is the upstream v5.0.1 release commit. The validator now passes for all
81 external action references. This removes the demonstrated early validation
blocker; a new remote run is still required to verify the full workflows.

The supplied `pipeline-evidence-35886483930-1.zip` confirms that the missing
source matrix in that run followed early validation failure. No shard ran;
source coverage was 0, and the release gate correctly rejected an empty
`proxies.json`. The merge gate should not be weakened.

The same artifact shows a separate native output defect: both
`singbox-dns-hardened.json` and `singbox-vpn-dns-hardened.json` fail because
their DNS rules reference `geosite-category-ads-all` while their routes define
no rule sets. The split generator now adds the shared rule set definitions to
both profiles, with a valid download detour. A structural regression test
covers both profiles. A native `sing-box check` on a fresh candidate is still
needed because the validator binary is unavailable in this local environment.

PR #635 merged at 16:06:58 UTC. The evidence run started later, and the
Dependabot head ref now returns HTTP 404. The exact historical error log is
unavailable, but the refresh script would have raised on that response before
its stale-run check could finish. It now treats 404
for that exact ref lookup as an already-deleted branch and exits without
writing. Other API errors still fail the job. A regression test covers this
case.

## Scheduled pipeline and live smoke cluster

| Run | Workflow | Evidence available |
| --- | --- | --- |
| [35885481460](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35885481460) | Live smoke | Both bounded source attempts fetched and parsed 16 configs, but none passed the Go tester; enforcement failed. |
| [35852907912](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35852907912) | Config's Stream | Failed; job detail unavailable. |
| [35813615380](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35813615380) | Config's Stream | All 153 shard jobs completed; output contract, native validation, and release gate failed. |
| [35793830361](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35793830361) | Config's Stream | Failed; job detail unavailable. |
| [35752821423](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35752821423) | Config's Stream | All 153 shard jobs completed; merge, diagnosis, and publication job failed. |
| [35707834299](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35707834299) | Config's Stream | Failed; job detail unavailable. |
| [35682470215](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35682470215) | Config's Stream | Failed; job detail unavailable. |
| [35665388186](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35665388186) | Config's Stream | Failed; job detail unavailable. |
| [35634602112](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35634602112) | Config's Stream | One shard reported an artifact download 403 and missing output; merge, diagnosis, and publication also failed. |
| [35584077124](https://github.com/AmirrezaFarnamTaheri/ConfigStream/actions/runs/35584077124) | Config's Stream | Failed; job detail unavailable. |

The 35813615380 evidence contains 5,251 proxies, including 2,539 working.
Its native checks fail only the two hardened Sing-box profiles fixed above.
Its output contract also rejects WireGuard records in `proxies.json` and
`protocols/wireguard.list.json`: URL query aliases such as `publickey`,
`presharedkey`, and WARP noise controls leak into `details`, while `mtu`
remains a string. The parser now publishes canonical fields, converts numeric
options, and discards unsupported query aliases. The schema recognizes
canonical `allowed_ips` and `persistent_keepalive` used by converters.

The live smoke evidence shows two admitted HTTPS sources fetched and parsed,
with 16 configs tested per attempt. Output generation completed, but the Go
tester recorded TLS errors, timeouts, connection errors, and WireGuard peer
failures; zero proxies were verified working. `selected_source=none` follows
from failed probes. This evidence does not establish a deterministic code
defect or justify weakening the live status gate. A fresh run is needed to
assess current source health and runner connectivity.

The recurring scheduled failures predate the action pin drift. The 403 on run
35634602112 is direct evidence of an artifact transport failure in that run,
not proof that all scheduled runs share that cause. No release or Pages
readiness claim follows from the local checks.

Five supplied `production-validation-*.zip` artifacts from a different commit
all report the same single pytest failure among 1,134 tests: an older test
expects `all_sources.npvt.nekobox.json` to be a top-level array, but the file
is an object with `outbounds`. The current repository output matrix and wiki
specify the object format, and the failing test file is absent at commit
`4698fd45b`. These artifacts establish a repeated failure in that validation
environment, but do not justify changing the current NekoBox format.

## Verification and remaining evidence

- `python scripts/validate_action_pins.py`: passed, 81 of 81 external actions pinned.
- `python scripts/verify_repository.py --profile static`: passed.
- Full repository profile reached output-matrix validation and stopped because
  its isolated child Python environment cannot import `pydantic`; this is a
  local dependency gap, not a demonstrated repository contract failure.
- Focused action pin, live smoke workflow, Dependabot evidence, DNS profile,
  and parser regression tests: 36 passed.
- Reparsed all 60 WireGuard URLs in the supplied 35813615380 candidate
  artifact; all 60 passed the WireGuard details schema after normalization.
- `flake8` and targeted `mypy` passed on the changed Python source files.
- Full pytest could not collect in the local Python environment because its
  installed dependencies lack `sniffio`, which is already declared in the
  project dependencies. This is a local environment limitation, not an
  established CI failure.

Rerun CI and Config's Stream on these fixes to verify the new pin set,
WireGuard contract, and native output remotely. A fresh live smoke run is
needed to assess current network reachability and source health.
