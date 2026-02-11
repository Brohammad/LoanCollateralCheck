#!/bin/bash
# Backup Script for AI Agent System

set -e

# Configuration
NAMESPACE="${NAMESPACE:-ai-agent}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="ai-agent-backup-$TIMESTAMP"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AI Agent Backup Script ===${NC}"
echo -e "${YELLOW}Backup name: $BACKUP_NAME${NC}"

# Create backup directory
mkdir -p $BACKUP_DIR

# Check if Velero is available
if command -v velero &> /dev/null; then
    echo -e "${YELLOW}Using Velero for backup...${NC}"
    
    velero backup create $BACKUP_NAME \
        --include-namespaces $NAMESPACE \
        --wait
    
    echo -e "${GREEN}✓ Velero backup created: $BACKUP_NAME${NC}"
    
    # Describe backup
    velero backup describe $BACKUP_NAME
    
elif command -v kubectl &> /dev/null; then
    echo -e "${YELLOW}Using kubectl for backup...${NC}"
    
    # Create backup directory for this backup
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
    
    # Backup all resources
    echo "Backing up Kubernetes resources..."
    kubectl get all,configmap,secret,pvc,ingress,hpa,networkpolicy \
        -n $NAMESPACE -o yaml > "$BACKUP_DIR/$BACKUP_NAME/k8s-resources.yaml"
    
    # Backup PVC data
    echo "Backing up PVC data..."
    PVCS=$(kubectl get pvc -n $NAMESPACE -o jsonpath='{.items[*].metadata.name}')
    
    for PVC in $PVCS; do
        echo "  Backing up PVC: $PVC"
        
        # Find pod using this PVC
        POD=$(kubectl get pods -n $NAMESPACE -o json | \
            jq -r ".items[] | select(.spec.volumes[]?.persistentVolumeClaim.claimName == \"$PVC\") | .metadata.name" | head -1)
        
        if [ -n "$POD" ]; then
            # Get mount path
            MOUNT_PATH=$(kubectl get pod $POD -n $NAMESPACE -o json | \
                jq -r ".spec.containers[0].volumeMounts[] | select(.name == \"data\" or .name == \"logs\") | .mountPath" | head -1)
            
            if [ -n "$MOUNT_PATH" ]; then
                kubectl exec -n $NAMESPACE $POD -- tar czf /tmp/$PVC.tar.gz $MOUNT_PATH 2>/dev/null || true
                kubectl cp $NAMESPACE/$POD:/tmp/$PVC.tar.gz "$BACKUP_DIR/$BACKUP_NAME/$PVC.tar.gz"
                kubectl exec -n $NAMESPACE $POD -- rm /tmp/$PVC.tar.gz
                echo -e "${GREEN}  ✓ Backed up $PVC ($MOUNT_PATH)${NC}"
            fi
        fi
    done
    
    # Backup database (if PostgreSQL)
    DB_POD=$(kubectl get pods -n $NAMESPACE -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
    if [ -n "$DB_POD" ]; then
        echo "Backing up PostgreSQL database..."
        kubectl exec -n $NAMESPACE $DB_POD -- pg_dump -U aiagent aiagent > "$BACKUP_DIR/$BACKUP_NAME/database.sql"
        echo -e "${GREEN}  ✓ Database backed up${NC}"
    fi
    
    # Create backup metadata
    cat > "$BACKUP_DIR/$BACKUP_NAME/metadata.json" << EOF
{
  "timestamp": "$TIMESTAMP",
  "namespace": "$NAMESPACE",
  "backup_type": "kubectl",
  "pvcs_backed_up": $(echo $PVCS | wc -w),
  "kubernetes_version": "$(kubectl version --short 2>/dev/null | grep Server || echo 'unknown')"
}
EOF
    
    # Create tarball
    echo "Creating backup archive..."
    cd $BACKUP_DIR
    tar czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME/"
    rm -rf "$BACKUP_NAME/"
    cd - > /dev/null
    
    echo -e "${GREEN}✓ Backup completed: $BACKUP_DIR/$BACKUP_NAME.tar.gz${NC}"
    
else
    echo -e "${RED}Error: Neither Velero nor kubectl is available${NC}"
    exit 1
fi

# List backups
echo ""
echo -e "${YELLOW}Available backups:${NC}"
if command -v velero &> /dev/null; then
    velero backup get
else
    ls -lh $BACKUP_DIR/*.tar.gz 2>/dev/null || echo "No backups found"
fi

echo ""
echo -e "${GREEN}Backup completed successfully!${NC}"
