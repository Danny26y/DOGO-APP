# Database

PostgreSQL is the proposed store. SQLAlchemy models and Alembic migrations will be used; production startup must not create tables automatically. Use timezone-aware timestamps, foreign keys, unique public references, tenant ownership columns, and indexes for tenant-scoped queries. Inventory updates require transactional concurrency protection; financial records are append-oriented events, not mutable wallet balance as accounting truth. Initial identity schema is in the foundation milestone; other entities are in `ARCHITECTURE.md` and traceability.

The current schema includes append-only `AuditLog` records for selected business mutations, with nullable user and tenant references to preserve history if accounts or organizations are removed. Financial provider events and invoice tables are still planned.
