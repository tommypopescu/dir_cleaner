# Dir Cleaner (FastAPI)

Aplicație web containerizată pentru scanarea și curățarea directoarelor mici/goale sau cu fișiere vechi. Include UI simplu (HTMX), container Docker și pipeline-uri pentru deploy **fără SSH**:
- **Azure DevOps** (`azure-pipelines.yml`) → build în ACR + deploy în **Azure Container Apps** (ACA)
- **GitLab CI** (`.gitlab-ci.yml`) → build în GitLab Registry + deploy în ACA

## Rulare locală
```bash
docker compose up --build -d
open http://localhost:8080
```

## Variabile de mediu
- `BASE_PATH` (default `/data`)
- `QUARANTINE_PATH` (dacă e setat, mută în carantină)
- `SIZE_THRESHOLD_MB` (default `50`)
- `UNUSED_DAYS` (default `90`)
- `SCAN_DEPTH` (default `1`)
- `EXCLUDES` (ex: `.git,node_modules,.cache`)
- `BASIC_AUTH_USER` / `BASIC_AUTH_PASS`
- `AUDIT_LOG` (default `/var/log/dir-cleaner/audit.log`)

## Azure DevOps (fără SSH)
1. Creează **Service connection** `$(AZURE_SVC_CONN)` (OIDC sau secret SP) către subscription-ul Azure.
2. Setează Variable Group/Library sau Pipeline vars:
   - `ACR_NAME`, `RESOURCE_GROUP`, `ACA_NAME`.
3. Rulează pipeline-ul; imaginea se construiește în **ACR Tasks** și se face update la Container App.

## GitLab CI (alternativ)
Defineste variabile de proiect: `AZ_CLIENT_ID`, `AZ_CLIENT_SECRET`, `AZ_TENANT_ID`, `ACR_NAME`, `RESOURCE_GROUP`, `ACA_NAME`.

## Securitate
- Operații limitate la `BASE_PATH`.
- Container non-root.
- Audit log la delete/move.
- Recomandat: folosește **carantina**.
