# Repository instructions

- Follow module boundaries in `docs/ARCHITECTURE.md`.
- Treat the traceability and open-decision documents as the source of implementation scope and unresolved business rules.
- Do not hardcode fares, commissions, provider secrets, or assumed payment success.
- Enforce organization membership and ownership on the server for every tenant resource.
- Add schema changes through Alembic migrations; never create production tables automatically.
- Keep external providers behind adapters and use sandbox credentials only.
- Update API and traceability documentation when public behavior changes.
- Do not claim a feature is complete unless its checks were run and observed.
