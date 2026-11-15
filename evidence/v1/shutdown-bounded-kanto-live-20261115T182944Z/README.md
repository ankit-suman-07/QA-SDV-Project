# Final d8c1f40 Kanto verification — resumed November 15, 2026

Actual operator-assisted run on the pinned d8c1f40 image passed three managed
stop/start cycles. [Independent review](independent-review.json) checks all three
source boundaries and exact complete event/Ditto properties, exit0 on every stop
and final cleanup, four completed-shutdown log entries, no old RuntimeError and
all old PIDs absent. 154 final twin samples keep vehicle-001 healthy/fault-free,
max gap0.335975s. Runner result counts148 before cleanup; six further snapshots
are retained. MQTT identity/QoS1/non-retain/source age/order independently checked.

This resolves the earlier d8c1f40 Kanto-pending checkpoint, without changing or
relabeling it. Same-device managed restart only, not remote LAN, automatic crash
restart or full V1 acceptance. Final combined verification is a separate run.
Dedicated namespace/new pilot name; normal sudo in operator terminal. Final pilot
remains stopped, descriptor retained; original services and Docker app-002 state
preserved. No merge/tag/release/approval or report/video work.
