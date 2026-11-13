# Azure deployment runbook

The repository is ready for an Azure Container Apps or Azure Container
Instance deployment, but no Azure subscription or resource names are committed.
Create these resources before deployment:

1. Azure Container Registry for `deploy/Dockerfile`.
2. Azure Container Apps (or Container Instance) for the API.
3. Azure AI Search for the production hybrid index.
4. Azure AI Foundry model deployment for answer generation.

Provide the deployment environment with `RAG_API_KEYS`, the provider API key,
Azure AI Search endpoint/key, and Foundry endpoint/key. Never commit them.
The current local pgvector service remains the reproducible development backend.

## Provisioning

1. Create a resource group, Azure Container Registry, Container Apps environment,
   Azure AI Search service, and an Azure AI Foundry project/model deployment.
2. Create a Search index named `regulatory-rag` with key `chunk_id`, a vector
   field matching the selected embedding dimensions (384 for BGE), and filterable
   `tenant` and `effective_date` fields.
3. Put the endpoint/key/deployment values in Container Apps secrets, then map
   them to `AZURE_SEARCH_*` and `AZURE_FOUNDRY_*` environment variables. Set
   `RAG_LLM_PROVIDER=foundry` and `RAG_RETRIEVER=azure` after the index is loaded.
4. Build and push `deploy/Dockerfile`, deploy it to Container Apps, then call
   `/v1/health` and a tenant-scoped `/v1/ask`. Save the resulting trace screenshot
   as `docs/azure-trace.png`; it is intentionally not fabricated in this repo.

The application uses tenant filters in the Azure adapter; do not remove the
filterable fields or expose an unscoped Search query.
