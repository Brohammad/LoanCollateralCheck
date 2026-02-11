# Deployment Guide - AI Agent System

Complete guide for deploying the AI Agent System to various environments.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Development](#local-development)
3. [Docker Deployment](#docker-deployment)
4. [Kubernetes Deployment](#kubernetes-deployment)
5. [Helm Deployment](#helm-deployment)
6. [Environment Configuration](#environment-configuration)
7. [Database Setup](#database-setup)
8. [Monitoring Setup](#monitoring-setup)
9. [Security Configuration](#security-configuration)
10. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software
- **Docker**: 20.10+ and Docker Compose 2.0+
- **Kubernetes**: 1.24+ (for K8s deployment)
- **Helm**: 3.10+ (for Helm deployment)
- **kubectl**: Matching your cluster version
- **Python**: 3.11+ (for local development)

### Required Accounts/Keys
- **Google Cloud**: For Gemini API access
- **Container Registry**: Docker Hub, GCR, ECR, or ACR
- **Domain**: For production deployment with HTTPS

---

## Local Development

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/ai-agent.git
cd ai-agent
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
cp .env.example .env
```

Edit `.env`:
```bash
# Required
GOOGLE_API_KEY=your-google-api-key-here
SECRET_KEY=your-secret-key-min-32-characters

# Optional
GENERATION_MODEL=gemini-2.0-flash-exp
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### 4. Initialize Database
```bash
python scripts/init_db.py
```

### 5. Run Application
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Access Application
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

---

## Docker Deployment

### Development Mode (Hot Reload)

```bash
# Build and run with docker-compose
docker-compose -f docker-compose.dev.yml up --build

# Or individually
docker build -f Dockerfile.dev -t ai-agent:dev .
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your-key \
  -v $(pwd)/app:/app/app \
  ai-agent:dev
```

**Access:**
- Application: http://localhost:8000
- Redis Commander: http://localhost:8081

### Production Mode

```bash
# Build production image
docker build -t ai-agent:latest .

# Run with docker-compose (includes monitoring)
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f app
```

**Access:**
- Application: http://localhost:8000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)
- Jaeger UI: http://localhost:16686
- Redis: localhost:6379

### Push to Registry

```bash
# Tag image
docker tag ai-agent:latest your-registry.com/ai-agent:latest
docker tag ai-agent:latest your-registry.com/ai-agent:v1.0.0

# Push to registry
docker push your-registry.com/ai-agent:latest
docker push your-registry.com/ai-agent:v1.0.0
```

---

## Kubernetes Deployment

### 1. Build and Push Image

```bash
# Build
docker build -t your-registry.com/ai-agent:v1.0.0 .

# Push
docker push your-registry.com/ai-agent:v1.0.0
```

### 2. Create Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### 3. Create Secrets

**Option A: Manual (base64 encoding)**

```bash
# Encode secrets
echo -n "your-google-api-key" | base64
echo -n "your-secret-key-min-32-chars" | base64

# Edit k8s/secrets.yaml with encoded values
kubectl apply -f k8s/secrets.yaml
```

**Option B: From literal values**

```bash
kubectl create secret generic ai-agent-secrets \
  --from-literal=GOOGLE_API_KEY=your-google-api-key \
  --from-literal=SECRET_KEY=your-secret-key-min-32-chars \
  --namespace=ai-agent
```

**Option C: From files**

```bash
kubectl create secret generic ai-agent-secrets \
  --from-file=GOOGLE_API_KEY=./secrets/google-api-key.txt \
  --from-file=SECRET_KEY=./secrets/secret-key.txt \
  --namespace=ai-agent
```

### 4. Apply Configuration

```bash
# ConfigMap
kubectl apply -f k8s/configmap.yaml

# Persistent Volume Claims
kubectl apply -f k8s/pvc.yaml

# Redis
kubectl apply -f k8s/redis-deployment.yaml

# Application
kubectl apply -f k8s/deployment.yaml

# Service
kubectl apply -f k8s/service.yaml

# Ingress (update domain in file first)
kubectl apply -f k8s/ingress.yaml

# HPA (Horizontal Pod Autoscaler)
kubectl apply -f k8s/hpa.yaml

# Network Policy (optional)
kubectl apply -f k8s/networkpolicy.yaml
```

### 5. Apply All at Once

```bash
kubectl apply -f k8s/
```

### 6. Verify Deployment

```bash
# Check pods
kubectl get pods -n ai-agent

# Check services
kubectl get svc -n ai-agent

# Check ingress
kubectl get ingress -n ai-agent

# Check HPA
kubectl get hpa -n ai-agent

# View logs
kubectl logs -f deployment/ai-agent-app -n ai-agent

# Describe pod
kubectl describe pod <pod-name> -n ai-agent
```

### 7. Access Application

```bash
# Port forward (for testing)
kubectl port-forward svc/ai-agent-service 8000:80 -n ai-agent

# Access via Ingress (after DNS setup)
curl https://api.yourdomain.com/health
```

---

## Helm Deployment

### 1. Update values.yaml

Edit `helm/ai-agent/values.yaml`:

```yaml
image:
  repository: your-registry.com/ai-agent
  tag: "v1.0.0"

ingress:
  hosts:
    - host: api.yourdomain.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: ai-agent-tls
      hosts:
        - api.yourdomain.com

secrets:
  googleApiKey: "your-google-api-key"
  secretKey: "your-secret-key-min-32-chars"
```

### 2. Install Chart

```bash
# Create namespace
kubectl create namespace ai-agent

# Install with Helm
helm install ai-agent ./helm/ai-agent \
  --namespace ai-agent \
  --values helm/ai-agent/values.yaml \
  --set secrets.googleApiKey=your-google-api-key \
  --set secrets.secretKey=your-secret-key

# Or with custom values file
helm install ai-agent ./helm/ai-agent \
  --namespace ai-agent \
  --values ./helm/ai-agent/values-production.yaml
```

### 3. Upgrade Deployment

```bash
helm upgrade ai-agent ./helm/ai-agent \
  --namespace ai-agent \
  --values helm/ai-agent/values.yaml
```

### 4. Rollback

```bash
# List releases
helm history ai-agent -n ai-agent

# Rollback to previous version
helm rollback ai-agent -n ai-agent

# Rollback to specific revision
helm rollback ai-agent 2 -n ai-agent
```

### 5. Uninstall

```bash
helm uninstall ai-agent -n ai-agent
```

---

## Environment Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_API_KEY` | Yes | - | Google Gemini API key |
| `SECRET_KEY` | Yes | - | JWT secret (min 32 chars) |
| `ENVIRONMENT` | No | production | Environment name |
| `LOG_LEVEL` | No | INFO | Logging level |
| `GENERATION_MODEL` | No | gemini-2.0-flash-exp | LLM model |
| `REDIS_URL` | No | - | Redis connection URL |
| `CORS_ALLOWED_ORIGINS` | No | * | Allowed CORS origins |

### Production Environment Variables

```bash
# .env.production
ENVIRONMENT=production
LOG_LEVEL=INFO
GOOGLE_API_KEY=your-production-key
SECRET_KEY=your-production-secret-min-32-chars
REDIS_URL=redis://ai-agent-redis:6379/0
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
ENABLE_METRICS=true
ENABLE_TRACING=true
```

### Staging Environment Variables

```bash
# .env.staging
ENVIRONMENT=staging
LOG_LEVEL=DEBUG
GOOGLE_API_KEY=your-staging-key
SECRET_KEY=your-staging-secret-min-32-chars
REDIS_URL=redis://redis:6379/0
CORS_ALLOWED_ORIGINS=https://staging.yourdomain.com
```

---

## Database Setup

### SQLite (Development)

Automatically created on first run:

```bash
python scripts/init_db.py
```

### PostgreSQL (Production)

**1. Deploy PostgreSQL on Kubernetes:**

```yaml
# postgres-deployment.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: ai-agent
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
        - name: postgres
          image: postgres:15-alpine
          env:
            - name: POSTGRES_DB
              value: aiagent
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: postgres-secrets
                  key: username
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secrets
                  key: password
          volumeMounts:
            - name: postgres-storage
              mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
    - metadata:
        name: postgres-storage
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 20Gi
```

**2. Run migrations:**

```bash
# Update DATABASE_URL in ConfigMap
kubectl set env deployment/ai-agent-app -n ai-agent \
  DATABASE_URL=postgresql://user:pass@postgres:5432/aiagent

# Run migration job
kubectl apply -f k8s/migration-job.yaml
```

---

## Monitoring Setup

### Prometheus

**Access Prometheus:**
```bash
kubectl port-forward svc/prometheus 9090:9090 -n ai-agent
```

Visit: http://localhost:9090

**Sample Queries:**
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

### Grafana

**Access Grafana:**
```bash
kubectl port-forward svc/grafana 3000:3000 -n ai-agent
```

Visit: http://localhost:3000 (admin/admin)

**Import Dashboards:**
1. Go to Dashboards → Import
2. Upload files from `monitoring/grafana/dashboards/`
3. Select Prometheus data source

### Jaeger Tracing

**Access Jaeger:**
```bash
kubectl port-forward svc/jaeger 16686:16686 -n ai-agent
```

Visit: http://localhost:16686

---

## Security Configuration

### 1. Generate Strong Secrets

```bash
# Generate SECRET_KEY (32+ characters)
openssl rand -hex 32

# Generate API keys
python -c "import secrets; print('sk_' + secrets.token_urlsafe(32))"
```

### 2. Configure TLS/HTTPS

**Option A: cert-manager (Kubernetes)**

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
EOF
```

Ingress will automatically get TLS certificate.

**Option B: Manual Certificate**

```bash
# Create TLS secret
kubectl create secret tls ai-agent-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  --namespace=ai-agent
```

### 3. Network Policies

Already configured in `k8s/networkpolicy.yaml`. Apply:

```bash
kubectl apply -f k8s/networkpolicy.yaml
```

### 4. RBAC (Role-Based Access Control)

```bash
# Create ServiceAccount with limited permissions
kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: ai-agent-sa
  namespace: ai-agent
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: ai-agent-role
  namespace: ai-agent
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: ai-agent-rolebinding
  namespace: ai-agent
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: ai-agent-role
subjects:
  - kind: ServiceAccount
    name: ai-agent-sa
    namespace: ai-agent
EOF
```

---

## Troubleshooting

### Common Issues

#### 1. Pod CrashLoopBackOff

```bash
# Check logs
kubectl logs <pod-name> -n ai-agent

# Describe pod
kubectl describe pod <pod-name> -n ai-agent

# Common causes:
# - Missing secrets
# - Invalid configuration
# - Database connection issues
# - Insufficient resources
```

#### 2. ImagePullBackOff

```bash
# Check if image exists
docker pull your-registry.com/ai-agent:v1.0.0

# Verify image pull secret
kubectl get secret regcred -n ai-agent

# Create image pull secret if needed
kubectl create secret docker-registry regcred \
  --docker-server=your-registry.com \
  --docker-username=your-username \
  --docker-password=your-password \
  --namespace=ai-agent
```

#### 3. Health Check Failing

```bash
# Test health endpoint
kubectl exec -it <pod-name> -n ai-agent -- curl localhost:8000/health

# Check readiness probe configuration
kubectl get pod <pod-name> -n ai-agent -o yaml | grep -A 10 readinessProbe
```

#### 4. Redis Connection Issues

```bash
# Test Redis connectivity
kubectl exec -it <pod-name> -n ai-agent -- nc -zv ai-agent-redis 6379

# Check Redis logs
kubectl logs deployment/ai-agent-redis -n ai-agent

# Test Redis from application pod
kubectl exec -it <app-pod> -n ai-agent -- redis-cli -h ai-agent-redis ping
```

#### 5. High Memory Usage

```bash
# Check resource usage
kubectl top pods -n ai-agent

# Increase memory limits in deployment
kubectl set resources deployment/ai-agent-app -n ai-agent \
  --limits=memory=8Gi --requests=memory=2Gi

# Or edit deployment
kubectl edit deployment ai-agent-app -n ai-agent
```

### Debugging Commands

```bash
# Get all resources
kubectl get all -n ai-agent

# Check events
kubectl get events -n ai-agent --sort-by='.lastTimestamp'

# Exec into pod
kubectl exec -it <pod-name> -n ai-agent -- /bin/bash

# View pod YAML
kubectl get pod <pod-name> -n ai-agent -o yaml

# Check resource quotas
kubectl describe resourcequota -n ai-agent

# Check network policies
kubectl get networkpolicy -n ai-agent

# Test DNS resolution
kubectl exec -it <pod-name> -n ai-agent -- nslookup ai-agent-redis
```

### Performance Tuning

#### 1. Optimize Resource Allocation

```yaml
resources:
  requests:
    cpu: "1000m"    # Start here
    memory: "2Gi"   # Start here
  limits:
    cpu: "4000m"    # Prevent runaway
    memory: "8Gi"   # Prevent OOM
```

#### 2. Adjust HPA Settings

```bash
# Scale based on load
kubectl autoscale deployment ai-agent-app -n ai-agent \
  --cpu-percent=70 \
  --min=3 \
  --max=20
```

#### 3. Enable HTTP/2

Update Ingress annotations:

```yaml
nginx.ingress.kubernetes.io/http2-push-preload: "true"
```

---

## Backup and Restore

### Backup Application Data

```bash
# Backup PVC data
kubectl exec -it <pod-name> -n ai-agent -- tar czf /tmp/backup.tar.gz /app/data
kubectl cp ai-agent/<pod-name>:/tmp/backup.tar.gz ./backup-$(date +%Y%m%d).tar.gz

# Backup with Velero (recommended)
velero backup create ai-agent-backup \
  --include-namespaces ai-agent \
  --wait
```

### Restore Application Data

```bash
# Restore PVC data
kubectl cp ./backup-20240211.tar.gz ai-agent/<pod-name>:/tmp/backup.tar.gz
kubectl exec -it <pod-name> -n ai-agent -- tar xzf /tmp/backup.tar.gz -C /

# Restore with Velero
velero restore create --from-backup ai-agent-backup
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build and push Docker image
        run: |
          docker build -t ${{ secrets.REGISTRY }}/ai-agent:${{ github.ref_name }} .
          docker push ${{ secrets.REGISTRY }}/ai-agent:${{ github.ref_name }}
      
      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/ai-agent-app \
            ai-agent=${{ secrets.REGISTRY }}/ai-agent:${{ github.ref_name }} \
            -n ai-agent
```

---

## Summary

✅ **Local Development**: Virtual environment + uvicorn  
✅ **Docker**: Development and production compose files  
✅ **Kubernetes**: Full manifests with ConfigMaps, Secrets, PVCs, HPA  
✅ **Helm**: Complete chart for easy deployment  
✅ **Monitoring**: Prometheus, Grafana, Jaeger integrated  
✅ **Security**: TLS, secrets management, network policies  
✅ **Scaling**: HPA, resource limits, anti-affinity  

For issues, check logs and refer to the [Troubleshooting](#troubleshooting) section.
