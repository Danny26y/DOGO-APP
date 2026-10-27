# DOGO Backend

Backend API foundation for the DOGO Web MVP. The repository is being built in reviewable milestones from the requirements in the DOGO Master Document.

## Current status

Phase A discovery, foundation, logistics, catalog/inventory, carts/orders-in-pending-payment, and selected audit logging are implemented to varying degrees. Payment verification, fulfillment, KYB documents, and operational integrations remain incomplete. See `docs/REQUIREMENTS_TRACEABILITY.md`.

## Local setup

Copy `.env.example` to `.env`, then run `docker compose up --build`. Compose applies migrations before starting the API, which is available on port 8000 with interactive docs at `/docs`. For local Python development, install `requirements.lock`, apply migrations with `alembic upgrade head`, then run `uvicorn app.main:app --reload`. Run quality checks with `pytest -q -p no:cacheprovider` and `ruff check app tests`.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Requirements traceability](docs/REQUIREMENTS_TRACEABILITY.md)
- [Open decisions](docs/OPEN_DECISIONS.md)
- [Initial API contract](docs/API_CONTRACT.md)
- [Frontend handoff](docs/FRONTEND_HANDOFF.md)
- [Security](docs/SECURITY.md)
- [Database](docs/DATABASE.md)
- [Testing](docs/TESTING.md)
- [Team workflow](docs/TEAM_WORKFLOW.md)
- [Deployment](docs/DEPLOYMENT.md)

This is an MVP foundation, not a production-ready logistics or commerce platform. Payment, dispatch, GPS, KYB document storage, and settlement integrations are not active.
