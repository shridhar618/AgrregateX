# AgrregateX — next phase recommendation

Do not rerun current 10M loader. It batches 100k INSERT statements server-side, but one outer transaction wraps all batches, index rebuild and rollup construction. It then full-scans/group-bys orders for daily_product and hourly_category. Cancellation occurred in hourly_category. Atomicity is preserved, but locks/open transaction lasted minutes and rollback took time. WAL/checkpoint logs show heavy write volume; post-event samples cannot identify CPU vs I/O as sole bottleneck.

Phase 01 should implement a staged idempotent loader: commit batches to staging keyed by deterministic source ID/run ID; reject conflicting duplicate payloads; validate counts, skew/checksum; build indexes once. During activation, pause writes or capture deltas. Build rollups from one consistent snapshot, validate against source, atomically swap. Never disable triggers while accepting writes without catch-up. Persist safe checkpoints and resume. Measure load, index, each GROUP BY, WAL, checkpoints, disk, cgroup RAM, CPU and locks separately.

Preserve current 1M volume; test on separate fresh volume or isolated clone. Obtain official schema/generator. Expand isolation checks to 100 identities. Run matched 1M/10M experiments only after loader/recovery improvements and fresh resource checks. Rebuild currently requires downtime.
