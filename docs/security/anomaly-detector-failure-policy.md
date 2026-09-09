# Anomaly detector failure policy

The source-volume anomaly detector is an advisory anti-poisoning control, not a release-authority boundary.

## Failure mode

If the detector's local SQLite state is unavailable or an anomaly check raises unexpectedly, source processing **fails open** for that check. The pipeline logs the detector failure and continues evaluating the source through the remaining parsing, validation, deduplication, testing, and release gates.

This is intentional: failing closed on a shared detector-state outage can suppress every source and turn a local observability/storage fault into a pipeline-wide availability failure.

## Security boundary

Fail-open does not mean a source bypasses the rest of the pipeline. Normal source parsing, schema/protocol validation, blocklists, tester stages, artifact validation, and release-readiness gates remain authoritative. A successful anomaly check can reject suspicious volume behavior; an unavailable anomaly detector cannot itself authorize publication.

## Change control

Changing this policy to fail closed requires an explicit architecture/security decision plus failure-mode tests demonstrating that a detector database outage cannot disable all healthy source processing. The existing failure-mode and anomaly tests intentionally lock the current fail-open contract.
