# Deployment Quick Reference

Quick command reference for deploying and managing the AI Agent System.

## Docker Commands

### Build
```bash
# Development
docker build -f Dockerfile.dev -t ai-agent:dev .

# Production
docker build -t ai-agent:latest .

# Multi-platform
docker buildx build --platform linux/amd64,linux/arm64 -t ai-agent:latest .
```

### Run
```bash
# Single container
docker run -d -p 8000:8000 \
  -e GOOGLE_API_KEY=your-key \
  -e SECRET_KEY=your-secret \
  ai-agent:latest

# With docker-compose (production)
docker-compose up -d

# With docker-compose (development)
docker-compose -f docker-compose.dev.yml up --build
```

### Manage
```bash
# View logs
docker logs -f <container-id>
docker-compose logs -f app

# Execute command in container
docker exec -it <container-id> bash

# Stop and remove
docker-compose down
docker-compose down -v  # Also remove volumes
```

---

## Kubernetes Commands

### Apply Resources
```bash
# Apply all manifests
kubectl apply -f k8s/

# Apply specific resource
kubectl apply -f k8s/deployment.yaml

# Apply with namespace
kubectl apply -f k8s/ -n ai-agent
```

### View Resources
```bash
# Get all resources
kubectl get all -n ai-agent

# Get specific resources
kubectl get pods -n ai-agent
kubectl get svc -n ai-agent
kubectl get ingress -n ai-agent
kubectl get hpa -n ai-agent

# Describe resource
kubectl describe pod <pod-name> -n ai-agent

# View logs
kubectl logs -f <pod-name> -n ai-agent
kubectl logs -f deployment/ai-agent-app -n ai-agent

# Get events
kubectl get events -n ai-agent --sort-by='.lastTimestamp'
```

### Scale
```bash
# Manual scaling
kubectl scale deployment ai-agent-app --replicas=5 -n ai-agent

# View HPA status
kubectl get hpa -n ai-agent
kubectl describe hpa ai-agent-hpa -n ai-agent
```

### Debug
```bash
# Execute command in pod
kubectl exec -it <pod-name> -n ai-agent -- bash

# Port forward
kubectl port-forward svc/ai-agent-service 8000:80 -n ai-agent

# Test connectivity
kubectl exec -it <pod-name> -n ai-agent -- curl http://localhost:8000/health
```

### Update
```bash
# Update image
kubectl set image deployment/ai-agent-app \
  ai-agent=your-registry.com/ai-agent:v1.0.1 \
  -n ai-agent

# Rollout status
kubectl rollout status deployment/ai-agent-app -n ai-agent

# Rollback
kubectl rollout undo deployment/ai-agent-app -n ai-agent

# Rollback to specific revision
kubectl rollout undo deployment/ai-agent-app --to-revision=2 -n ai-agent
```

### Delete
```bash
# Delete specific resource
kubectl delete -f k8s/deployment.yaml

# Delete all resources in namespace
kubectl delete all --all -n ai-agent

# Delete namespace (and all resources)
kubectl delete namespace ai-agent
```

---

## Helm Commands

### Install
```bash
# Install chart
helm install ai-agent ./helm/ai-agent \
  --namespace ai-agent \
  --create-namespace

# Install with values file
helm install ai-agent ./helm/ai-agent \
  --namespace ai-agent \
  --values ./helm/ai-agent/values-production.yaml

# Install with overrides
helm install ai-agent ./helm/ai-agent \
  --namespace ai-agent \
  --set image.tag=v1.0.0 \
  --set secrets.googleApiKey=your-key \
  --set secrets.secretKey=your-secret
```

### Upgrade
```bash
# Upgrade release
helm upgrade ai-agent ./helm/ai-agent \
  --namespace ai-agent

# Upgrade with new values
helm upgrade ai-agent ./helm/ai-agent \
  --namespace ai-agent \
  --set image.tag=v1.0.1 \
  --reuse-values

# Upgrade and wait
helm upgrade ai-agent ./helm/ai-agent \
  --namespace ai-agent \
  --wait \
  --timeout 5m
```

### Manage
```bash
# List releases
helm list -n ai-agent
helm list --all-namespaces

# Get release status
helm status ai-agent -n ai-agent

# Get release values
helm get values ai-agent -n ai-agent

# Get release manifest
helm get manifest ai-agent -n ai-agent

# View history
helm history ai-agent -n ai-agent
```

### Rollback
```bash
# Rollback to previous version
helm rollback ai-agent -n ai-agent

# Rollback to specific revision
helm rollback ai-agent 2 -n ai-agent

# Dry run rollback
helm rollback ai-agent --dry-run -n ai-agent
```

### Uninstall
```bash
# Uninstall release
helm uninstall ai-agent -n ai-agent

# Uninstall and keep history
helm uninstall ai-agent -n ai-agent --keep-history
```

### Test/Debug
```bash
# Dry run install
helm install ai-agent ./helm/ai-agent \
  --dry-run --debug \
  --namespace ai-agent

# Template (render without installing)
helm template ai-agent ./helm/ai-agent \
  --namespace ai-agent

# Lint chart
helm lint ./helm/ai-agent

# Package chart
helm package ./helm/ai-agent
```

---

## Monitoring Commands

### Prometheus
```bash
# Port forward Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n ai-agent

# View Prometheus config
kubectl get configmap prometheus-config -n ai-agent -o yaml
```

**Sample Queries:**
```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])

# P95 latency
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Memory usage
container_memory_usage_bytes{pod=~"ai-agent-.*"}
```

### Grafana
```bash
# Port forward Grafana
kubectl port-forward svc/grafana 3000:3000 -n ai-agent

# Default credentials: admin/admin
```

### Jaeger
```bash
# Port forward Jaeger
kubectl port-forward svc/jaeger 16686:16686 -n ai-agent
```

### Logs
```bash
# Stream logs
kubectl logs -f deployment/ai-agent-app -n ai-agent

# Logs from all pods
kubectl logs -l app.kubernetes.io/name=ai-agent -n ai-agent --tail=100

# Previous container logs (if crashed)
kubectl logs <pod-name> -n ai-agent --previous
```

---

## Backup & Restore

### Backup
```bash
# Using custom script
./scripts/backup.sh

# Using Velero
velero backup create ai-agent-backup \
  --include-namespaces ai-agent \
  --wait

# List backups
velero backup get
```

### Restore
```bash
# Using custom script
./scripts/restore.sh ai-agent-backup-20240211_143022

# Using Velero
velero restore create --from-backup ai-agent-backup --wait

# List restores
velero restore get
```

---

## Security Commands

### Secrets Management
```bash
# Create secret from literal
kubectl create secret generic ai-agent-secrets \
  --from-literal=GOOGLE_API_KEY=your-key \
  --from-literal=SECRET_KEY=your-secret \
  -n ai-agent

# Create secret from file
kubectl create secret generic ai-agent-secrets \
  --from-file=GOOGLE_API_KEY=./google-api-key.txt \
  -n ai-agent

# View secret (base64 encoded)
kubectl get secret ai-agent-secrets -n ai-agent -o yaml

# Decode secret
kubectl get secret ai-agent-secrets -n ai-agent \
  -o jsonpath='{.data.GOOGLE_API_KEY}' | base64 -d
```

### TLS/Certificates
```bash
# Create TLS secret
kubectl create secret tls ai-agent-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  -n ai-agent

# View certificate
kubectl get secret ai-agent-tls -n ai-agent \
  -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -text -noout
```

### Network Policies
```bash
# Apply network policy
kubectl apply -f k8s/networkpolicy.yaml

# View network policies
kubectl get networkpolicy -n ai-agent

# Describe policy
kubectl describe networkpolicy ai-agent-app-policy -n ai-agent
```

---

## Troubleshooting Commands

### Pod Issues
```bash
# Describe pod
kubectl describe pod <pod-name> -n ai-agent

# Get pod events
kubectl get events --field-selector involvedObject.name=<pod-name> -n ai-agent

# Get pod YAML
kubectl get pod <pod-name> -n ai-agent -o yaml

# Check resource usage
kubectl top pod <pod-name> -n ai-agent
kubectl top pods -n ai-agent
```

### Service Issues
```bash
# Test service internally
kubectl run test-pod --image=curlimages/curl:latest --rm -it --restart=Never \
  -n ai-agent -- curl http://ai-agent-service/health

# View service endpoints
kubectl get endpoints ai-agent-service -n ai-agent

# Describe service
kubectl describe svc ai-agent-service -n ai-agent
```

### Ingress Issues
```bash
# Describe ingress
kubectl describe ingress ai-agent-ingress -n ai-agent

# View ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx

# Test ingress from outside
curl -v https://api.yourdomain.com/health
```

### DNS Issues
```bash
# Test DNS resolution
kubectl run test-dns --image=busybox:1.28 --rm -it --restart=Never \
  -n ai-agent -- nslookup ai-agent-service

# Check CoreDNS
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns
```

---

## Useful One-Liners

### Get pod IP addresses
```bash
kubectl get pods -n ai-agent -o wide
```

### Restart all pods
```bash
kubectl rollout restart deployment/ai-agent-app -n ai-agent
```

### Get all container images
```bash
kubectl get pods -n ai-agent -o jsonpath='{range .items[*]}{.spec.containers[*].image}{"\n"}{end}'
```

### Check resource requests/limits
```bash
kubectl describe nodes | grep -A 5 "Allocated resources"
```

### Get secret keys
```bash
kubectl get secret ai-agent-secrets -n ai-agent -o json | jq '.data | keys'
```

### Watch pod status
```bash
watch kubectl get pods -n ai-agent
```

### Get failed pods
```bash
kubectl get pods -n ai-agent --field-selector=status.phase=Failed
```

### Force delete pod
```bash
kubectl delete pod <pod-name> -n ai-agent --grace-period=0 --force
```

---

## Environment Variables

### Common Variables
```bash
export NAMESPACE=ai-agent
export KUBECONFIG=~/.kube/config
export HELM_RELEASE=ai-agent
```

### Quick Aliases
```bash
alias k='kubectl'
alias kn='kubectl -n ai-agent'
alias h='helm'
alias hl='helm list -n ai-agent'
alias kg='kubectl get'
alias kd='kubectl describe'
alias kl='kubectl logs -f'
```

---

## CI/CD

### GitHub Actions Secrets
```
GOOGLE_API_KEY_PRODUCTION
GOOGLE_API_KEY_STAGING
SECRET_KEY_PRODUCTION
SECRET_KEY_STAGING
REDIS_PASSWORD_PRODUCTION
KUBE_CONFIG_PRODUCTION
KUBE_CONFIG_STAGING
SLACK_WEBHOOK_URL
GITHUB_TOKEN (automatic)
```

### Manual Deployment
```bash
# Build and push
docker build -t your-registry.com/ai-agent:v1.0.0 .
docker push your-registry.com/ai-agent:v1.0.0

# Deploy with Helm
helm upgrade --install ai-agent ./helm/ai-agent \
  --namespace ai-agent \
  --set image.tag=v1.0.0 \
  --wait
```

---

## Quick Health Checks

### Application Health
```bash
# Local health check
curl http://localhost:8000/health

# Kubernetes health check
kubectl exec -it <pod-name> -n ai-agent -- curl http://localhost:8000/health

# External health check
curl https://api.yourdomain.com/health
```

### Component Health
```bash
# Check all pods
kubectl get pods -n ai-agent

# Check services
kubectl get svc -n ai-agent

# Check ingress
kubectl get ingress -n ai-agent

# Check HPA
kubectl get hpa -n ai-agent

# Check PVC
kubectl get pvc -n ai-agent
```

---

For comprehensive documentation, see:
- **Deployment Guide**: docs/DEPLOYMENT_GUIDE.md
- **System Architecture**: ARCHITECTURE.md
- **Security**: security/SECURITY.md
