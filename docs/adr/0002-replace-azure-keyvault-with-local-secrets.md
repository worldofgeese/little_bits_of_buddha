# ADR 0002: Replace Azure Key Vault with Local File Secret Store

## Status
Accepted

## Date
2026-02-10

## Context

The project currently uses Azure Key Vault as its Dapr secret store (`azure-key-vault-secret-store`). This requires:
- Azure subscription and Key Vault instance
- Azure CLI authentication
- Network access to Azure services

For local development and self-hosted deployment on a home Tailnet, this adds unnecessary complexity and external dependencies.

## Decision

Replace Azure Key Vault with Dapr's **local file secret store** component. This:
- Stores secrets in a local JSON file
- Works identically via the Dapr secrets API
- Requires no external services or authentication
- Is appropriate for single-user, self-hosted deployments

### Secret file location
`secrets/secrets.json` (gitignored)

### Component configuration
`.dapr/components/local-secret-store.yaml`

## Consequences

### Positive
- No Azure dependency
- Works offline
- Simpler deployment
- Same Dapr API — code changes are minimal (just the store name)

### Negative
- Secrets stored on disk (acceptable for self-hosted single-user)
- Must ensure `secrets/` is gitignored

### Security considerations
- File permissions should restrict access to the running user
- For production multi-user deployments, consider HashiCorp Vault or similar

## Implementation

1. Create `.dapr/components/local-secret-store.yaml`
2. Create `secrets/secrets.json` template (gitignored)
3. Update `DAPR_STORE_NAME` in both services from `azure-key-vault-secret-store` to `local-secret-store`
4. Add `secrets/` to `.gitignore`
