# Dir Cleaner — Documentație completă

> **Versiune**: 1.0 • **Stack**: FastAPI + HTMX (UI) • Container: Python 3.12-slim (non-root recomandat)

---

## 1) Ce face aplicația

Aplicația scanează un director de bază (Base Path) și listează subdirectoarele cu:
- dimensiune totală (human readable + bytes),
- număr fișiere / subfoldere,
- marcaj „gol” (fără conținut),
- număr fișiere „vechi” (mai vechi decât `UNUSED_DAYS`).

Din UI poți selecta directoare și:
- **Mută în carantină** (recomandat; recuperabil),
- **Șterge definitiv** (operație ireversibilă).

**După acțiune** aplicația rescanează automat. UI are **sortare** pe coloane, **tema dark/light** (toggle) și **selector de sursă** (alegere rapidă între căile definite în `PATH_CHOICES`).

---

## 2) Arhitectură & fișiere

```
app/
 ├─ main.py            # rute FastAPI (UI + API); fără autentificare
 ├─ scanner.py         # scanare, statistici, mutare/ștergere + audit
 ├─ templates/
 │   └─ index.html     # UI: HTMX + JS (sortare, selecție, acțiuni sus/jos, rescan)
 └─ static/            # assets static (opțional)
Dockerfile              # imaginea container
docker-compose.yml      # rulare locală / on-prem
```

---

## 3) Variabile de mediu (config)

| Variabilă | Implicit | Descriere |
|---|---:|---|
| `BASE_PATH` | `/data` | Director de bază implicit pentru scanare |
| `PATH_CHOICES` | `BASE_PATH` | Listă de surse selectabile în UI, separate prin virgulă (ex.: `/data/movie/,/data/series/`) |
| `QUARANTINE_PATH` | *(gol)* | Dacă e setată, „Mută în carantină” operează aici |
| `SIZE_THRESHOLD_MB` | `50` | Prag sub care folderul e marcat „mic” |
| `UNUSED_DAYS` | `90` | Zile peste care fișierele sunt considerate „vechi” |
| `SCAN_DEPTH` | `1` | Adâncime scanare în subfoldere |
| `EXCLUDES` | *(gol)* | Virgule, pattern simplu (substring) pentru excluderi |
| `AUDIT_LOG` | `/var/log/dir-cleaner/audit.log` | Scriere evenimente MOVE/DELETE/ERROR |

> **Notă**: aplicația limitează operațiile la `base_path` (validare "subarbore").

---

## 4) Rulare cu Docker Compose

1. **Completați** volume și env în `docker-compose.yml`:

```yaml
environment:
  BASE_PATH: /data
  PATH_CHOICES: "/data/movie/,/data/series/"
  QUARANTINE_PATH: /quarantine
  SIZE_THRESHOLD_MB: "50"
  UNUSED_DAYS: "90"
  SCAN_DEPTH: "1"
  EXCLUDES: ".git,node_modules,.cache"
  AUDIT_LOG: "/var/log/dir-cleaner/audit.log"
volumes:
  - /path/mergerfs:/data:rw
  - /path/quarantine:/quarantine:rw
```

2. **Permisiuni** (mergerfs/OMV tipic): dacă directoarele sunt `root:users` (GID 100) cu `2775`, rulați containerul cu **GID=100** sau dați ACL corespunzător.

```yaml
# Recomandat pe mergerfs:
user: "10001:100"     # UID appuser, GID=users (100)
# sau (test) permissive: chmod -R 0777 pe folderele montate
```

3. **Porniți**:
```bash
docker compose up --build -d
# UI: http://HOST:8080
```

---

## 5) Flux UI — utilizare

1. **Alege Sursa** din dropdown (config în `PATH_CHOICES`). Se copiază în `Path de bază` și pornește scan automat.
2. **Filtre**: ajustați prag mărime, zile vechi, adâncime, excluderi.
3. **Scanează** → Tabel cu rezultate.
4. **Sortare**: click pe antet (Mărime, Fișiere, Subfoldere, Gol, Vechi, Path). A doua apăsare inversează direcția.
5. **Selectați rândurile** dorite (checkbox pe linie). Numărul selecțiilor apare în barele de acțiuni **sus** și **jos**.
6. **Acțiune**: „Mută în carantină” sau „Șterge definitiv”. După execuție → **rescan automat**.
7. **Tema**: buton 🌙/☀️ comută dark/light (persistă în `localStorage`).

---

## 6) Pipeline GitHub Actions (build & push în GHCR)

> Dacă folosești GHCR: verifică Settings → Packages ale org/repo și permite publicarea imaginii.

Exemplu `.github/workflows/build-push.yml`:

```yaml
name: Build and Push (GHCR)

on:
  push:
    branches: [ "main", "master" ]
  workflow_dispatch:

permissions:
  contents: read
  packages: write

jobs:
  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Log in to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.repository_owner }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build & Push
        uses: docker/build-push-action@v6
        with:
          context: .
          file: ./Dockerfile
          push: true
          tags: |
            ghcr.io/${{ github.repository_owner }}/dir-cleaner:latest
            ghcr.io/${{ github.repository_owner }}/dir-cleaner:${{ github.sha }}
```

**Pull local din GHCR** (dacă pachetul e privat):
```bash
echo <PAT_read_packages> | docker login ghcr.io -u <user> --password-stdin
# în compose setează image: ghcr.io/<owner>/dir-cleaner:latest
```

---

## 7) Lucru cu Git & VS Code

### A. Încărcare proiect în repo (o dată)
```bash
git init
git add .
git commit -m "initial import"
git branch -M master   # sau main
git remote add origin https://github.com/<org>/<repo>.git
git push -u origin master
```

### B. Workflow nu pornește?
- Verifică fișierul în `.github/workflows/*.yml` pe **același branch** (`main`/`master`).
- În YAML: `on.push.branches: ["main","master"]` sau branch-ul tău real.
- Settings → Actions → General → „Allow GitHub Actions to run this repository”.
- Fă un commit gol pentru trigger:
```bash
git commit --allow-empty -m "trigger actions"
git push
```

### C. Pull Request (PR) din VS Code
1. **Creează branch**: *Git: Create Branch…* → `feat/ui-dark-source-select`  
2. Fă modificări → **Commit**.  
3. **Publish Branch** → **Create Pull Request** (titlu + descriere) → **Create**.  
4. După review, **Merge** în `master/main`.

### D. Pull Request din CLI
```bash
git checkout -b feat/ui-dark-source-select
git add -A
git commit -m "feat(ui): dark theme + source select + auto-rescan"
git push -u origin feat/ui-dark-source-select
# deschide PR din UI GitHub (Compare & pull request)
```

---

## 8) Permisiuni & storage — note practice

- **MergerFS/OMV**: volume tipice `root:users` (GID 100), mod `2775`.  
  Rulați containerul cu `user: "10001:100"` (UID aplicație, GID=users) **sau** set ACL pentru UID-ul procesului:
  ```bash
  setfacl -R -m u:10001:rwx /path/mergerfs
  setfacl -R -d -m u:10001:rwx /path/mergerfs
  ```
- **NFS**: dacă există `root_squash`, rularea ca root nu ajută. Folosiți UID/GID care au drepturi pe export **sau** cereți `no_root_squash`.
- **SELinux**: montați cu `:z`/`:Z` dacă folosiți Fedora/RHEL (etichetare corectă).

---

## 9) Troubleshooting rapid

- „**Nu pornește workflow**”: corectează `on.push.branches` și verifică tab **Actions**.
- „**failed to read dockerfile**”: rulezi `docker compose` din alt director sau `file:` din workflow arată într-o cale inexistentă.
- „**pull access denied for dir-cleaner:local**”: nu ai build local; rulează `docker compose build` sau setează `image:` către GHCR.
- „**Permission denied** la mutare/ștergere”: verifică `id` în container, `mount` și `ls -la`. Pe mergerfs tipic → `user: "10001:100"`.
- UI arată **JSON brut**: asigură-te că încarci HTMX real (CDN) și că formularul are `hx-get="/api/scan"` + `hx-swap="none"`.

---

## 10) Securitate (on‑prem/LAN)

- Fără autentificare. Ține aplicația în LAN/VPN.  
- Recomandat: folosește **carantina** în loc de ștergere definitivă în producție.  
- Păstrează fișierul `AUDIT_LOG` pe volum persistent.

---

## 11) Extensii posibile

- Export CSV/JSON al rezultatelor scanării.  
- Scheduler raport săptămânal (scan only).  
- Politici pe extensii (skip `.srt`, `.config`, etc.).  
- Integrare OIDC la nivel de reverse proxy (dacă expui extern).

---

**Contact & întreținere**
- Scanarea se face cu `os.walk` + statistici; pentru volume foarte mari se poate introduce parallelism (ThreadPool) sau caching incremental.
- Versiuni librării: vezi `requirements.txt`. Containerul e bazat pe `python:3.12-slim`.
