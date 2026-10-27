# Deployment

The target is provider-neutral containers. Compose starts PostgreSQL, runs a one-shot migration service, then starts the API. Production deployments should run migrations once as a release job before scaling API instances; do not run migrations independently in every replica. Configure health checks, structured request-ID logs, CORS, backups/restore, staging smoke tests, and rollback on the hosting platform. No cloud resources or secrets are provisioned. Supply secrets through the platform secret manager; never bake them into images.
