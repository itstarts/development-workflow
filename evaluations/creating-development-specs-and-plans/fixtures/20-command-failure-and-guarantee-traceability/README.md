# Fictional durable order archive service

This fixture is used only to evaluate technical specification quality.

The approved stack is Python 3.14, the standard `sqlite3` driver, SQLite 3.46 in WAL mode, one local API process, and one in-process background archive worker. `PUT /orders/{orderId}` synchronously saves an editable order. `POST /order-archives` starts one background archive job and `GET /order-archives/{jobId}` exposes its status.

Every write carries `expectedRevision`. A background job reads a fixed order snapshot, performs slow archive serialization outside a transaction, then persists the completed archive. The implementation must distinguish a stale snapshot from a local database persistence failure. Clients must receive stable HTTP status, error code, current revision when reachable, and a terminal job status. The repository has no implementation yet; the technical specification owns the precise transaction, locking, failure-classification, rollback, and automated-test contract.
