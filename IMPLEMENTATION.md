# Movies API — Implementation Guide

Stack: **Python 3.12 + FastAPI + uvicorn + prometheus-client**

## Prerequisites

Install these once on your workstation:

| Tool | Version | Install |
|------|---------|---------|
| Docker | ≥ 24 | [docs.docker.com](https://docs.docker.com/get-docker/) |
| k3d | ≥ 5 | `brew install k3d` |
| kubectl | ≥ 1.28 | `brew install kubectl` |
| kustomize | ≥ 5 | `brew install kustomize` |
| Python | ≥ 3.9 | for running tests locally |

---

## One-time cluster setup

### 1. Create the k3d cluster

```bash
k3d cluster create movies \
  --port "8080:80@loadbalancer" \
  --port "3000:3000@loadbalancer" \
  --port "9090:9090@loadbalancer"
```

### 2. Install the Prometheus Operator

```bash
kubectl apply --server-side -f \
  https://github.com/prometheus-operator/prometheus-operator/releases/latest/download/bundle.yaml

# Wait for operator to be ready
kubectl wait --for=condition=available \
  deployment/prometheus-operator -n default --timeout=120s
```

### 3. Create the Grafana admin secret

The secret is **not** committed to the repo. Create it manually before deploying:

```bash
kubectl create namespace monitoring 2>/dev/null || true

kubectl create secret generic grafana-admin \
  --from-literal=password=admin \
  --namespace monitoring
```

Use a stronger password in any non-throwaway environment.

### 5. Apply the full stack

```bash
kubectl apply -k k8s/overlays/dev
```

Wait for everything to be ready:

```bash
kubectl rollout status deployment/movies-api -n movies
kubectl rollout status deployment/grafana -n monitoring
```

### 6. Port-forward Grafana (if not using load balancer port)

```bash
kubectl port-forward svc/grafana 3000:3000 -n monitoring &
```

Open Grafana at <http://localhost:3000> (anonymous viewer, or admin/admin).

---

## Inner loop (iterate on every change)

### Step 1 — Make a change

Edit source under `src/movies_api/`, manifests under `k8s/`, or data under `src/data/`.

### Step 2 — Bump the version

Update the version tag you will use for this build:

```bash
export VERSION=1.0.1      # or whatever semver you want
```

### Step 3 — Build the image

```bash
docker build --build-arg MOVIES_VERSION=${VERSION} -t movies-api:${VERSION} .
```

### Step 4 — Load the image into k3d and deploy

```bash
k3d image import movies-api:${VERSION} -c movies

# Update the image tag in the dev overlay, then apply
kustomize build k8s/overlays/dev | \
  kubectl set image deployment/movies-api \
    movies-api=movies-api:${VERSION} -n movies --local -f - | \
  kubectl apply -f -
```

Or, if you edited kustomization.yaml to set `newTag: ${VERSION}`:

```bash
# Edit k8s/overlays/dev/kustomization.yaml: newTag: 1.0.1
kustomize build k8s/overlays/dev | kubectl apply -f -
```

Wait for rollout:

```bash
kubectl rollout status deployment/movies-api -n movies --timeout=60s
```

### Step 5 — Verify the version is live

```bash
curl -s http://localhost:8080/version
# → 1.0.1
```

### Step 6 — Run validation tests

Install the replay tool once:

```bash
pip install httpx PyYAML
```

Run functional contract tests against the cluster:

```bash
python tools/replay/main.py validate --base-url http://localhost:8080
```

All scenarios must show `✓`.

Run the benchmark (30 s, 50 concurrent workers):

```bash
python tools/replay/main.py benchmark --base-url http://localhost:8080
```

Targets:
- p95 `/api/movies` < 50 ms
- p95 `/api/movies/{id}` < 10 ms
- ≥ 500 RPS with < 1% error rate

### Step 7 — Inspect the Grafana dashboard

Open <http://localhost:3000> → Dashboards → **Movies API**.

The dashboard shows request rate, error rate, p50/p95 latency per endpoint, and dataset size.

### Step 8 — Iterate

Repeat steps 1–7 for the next change.

---

## Running unit + integration tests locally

```bash
cd src

# First time: create venv and install deps
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install \
  "fastapi>=0.111.0" "uvicorn[standard]>=0.30.0" \
  "prometheus-client>=0.20.0" "pydantic>=2.7.0" \
  "pytest>=8.0.0" "httpx>=0.27.0" "pytest-cov>=5.0.0" "anyio>=4.0.0"

# Run tests (from src/)
PYTHONPATH=. .venv/bin/pytest tests/ -v
```

Coverage target: ≥ 80% (currently 88%).

---

## Dependency audit

```bash
cd src
.venv/bin/pip install pip-audit
.venv/bin/pip-audit
```

---

## Configuration reference

| Env var | CLI flag | Default | Purpose |
|---------|----------|---------|---------|
| `MOVIES_DATA_DIR` | `--movies-data-dir` | `/data` | Path to JSON data files |
| `MOVIES_LOG_LEVEL` | `--movies-log-level` | `info` | Log level: debug/info/warn/error |
| `MOVIES_PORT` | `--movies-port` | `8080` | HTTP listen port |
| `MOVIES_VERSION` | — | `1.0.0` | Semver returned by `/version` |

Precedence (highest wins): CLI flags → environment variables → built-in defaults.

---

## API quick reference

| Endpoint | Notes |
|----------|-------|
| `GET /api/movies` | `q`, `genre`, `year`, `rating`, `actorId`, `pageNumber`, `pageSize` |
| `GET /api/movies/{id}` | id format `tt########` |
| `GET /api/actors` | `q`, `pageNumber`, `pageSize` |
| `GET /api/actors/{id}` | id format `nm########` |
| `GET /api/genres` | array of strings |
| `GET /healthz` | plaintext `pass` |
| `GET /readyz` | 200 when data loaded, 503 before |
| `GET /version` | plaintext semver |
| `GET /metrics` | Prometheus exposition |
| `GET /swagger` | Swagger UI |
| `GET /swagger/v1/swagger.json` | OpenAPI 3 document |

---

## Project structure

```
src/
  movies_api/        FastAPI application
    config.py        Config (env + CLI flags)
    models.py        Pydantic response models
    store.py         In-memory data store
    metrics.py       Prometheus metrics
    logging_config.py  JSON structured logging
    middleware.py    Metrics + access-log middleware
    main.py          App factory + entrypoint
    routes/          HTTP handlers
  tests/             Unit + integration tests
  data/              Seed data (movies, actors, ratings JSON)
  pyproject.toml

tools/
  replay/
    main.py          Replay + benchmark CLI
    scenarios/
      baseline.yaml  Functional contract test scenarios
      benchmark.yaml Load-test targets

k8s/
  base/              Kustomize base (all resources)
  overlays/dev/      Dev overlay (image tag, debug logging)

Dockerfile           Multi-stage Python 3.12 image
```
