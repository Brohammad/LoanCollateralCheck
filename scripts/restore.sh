#!/bin/bash
# Restore Script for AI Agent System

set -e

# Configuration
NAMESPACE="${NAMESPACE:-ai-agent}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
BACKUP_NAME="$1"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AI Agent Restore Script ===${NC}"

# Check if backup name provided
if [ -z "$BACKUP_NAME" ]; then
    echo -e "${RED}Error: Please provide backup name${NC}"
    echo "Usage: $0 <backup-name>"
    echo ""
    echo "Available backups:"
    
    if command -v velero &> /dev/null; then
        velero backup get
    else
        ls -1 $BACKUP_DIR/*.tar.gz 2>/dev/null | sed 's|.*/||' | sed 's|\.tar\.gz||' || echo "No backups found"
    fi
    exit 1
fi

# Check if Velero is available
if command -v velero &> /dev/null && velero backup get $BACKUP_NAME &> /dev/null; then
    echo -e "${YELLOW}Using Velero for restore...${NC}"
    echo -e "${RED}WARNING: This will restore the entire namespace $NAMESPACE${NC}"
    read -p "Continue? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo "Restore cancelled"
        exit 0
    fi
    
    velero restore create --from-backup $BACKUP_NAME --wait
    
    echo -e "${GREEN}✓ Velero restore completed${NC}"
    
    # Describe restore
    velero restore describe $BACKUP_NAME-$(date +%Y%m%d%H%M%S)
    
elif command -v kubectl &> /dev/null; then
    echo -e "${YELLOW}Using kubectl for restore...${NC}"
    
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_NAME.tar.gz"
    
    if [ ! -f "$BACKUP_FILE" ]; then
        echo -e "${RED}Error: Backup file not found: $BACKUP_FILE${NC}"
        exit 1
    fi
    
    echo -e "${RED}WARNING: This will overwrite existing data in namespace $NAMESPACE${NC}"
    read -p "Continue? (yes/no): " CONFIRM
    
    if [ "$CONFIRM" != "yes" ]; then
        echo "Restore cancelled"
        exit 0
    fi
    
    # Extract backup
    TEMP_DIR=$(mktemp -d)
    echo "Extracting backup to $TEMP_DIR..."
    tar xzf "$BACKUP_FILE" -C "$TEMP_DIR"
    
    # Find the backup directory
    BACKUP_PATH=$(find "$TEMP_DIR" -type d -name "ai-agent-backup-*" | head -1)
    
    if [ -z "$BACKUP_PATH" ]; then
        echo -e "${RED}Error: Invalid backup archive${NC}"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Scale down deployment
    echo "Scaling down deployment..."
    kubectl scale deployment -n $NAMESPACE --all --replicas=0 || true
    sleep 10
    
    # Restore Kubernetes resources
    if [ -f "$BACKUP_PATH/k8s-resources.yaml" ]; then
        echo "Restoring Kubernetes resources..."
        kubectl apply -f "$BACKUP_PATH/k8s-resources.yaml" || true
    fi
    
    # Wait for pods to be ready
    echo "Waiting for pods to be ready..."
    sleep 20
    
    # Restore PVC data
    echo "Restoring PVC data..."
    for BACKUP_FILE in "$BACKUP_PATH"/*.tar.gz; do
        if [ -f "$BACKUP_FILE" ]; then
            PVC_NAME=$(basename "$BACKUP_FILE" .tar.gz)
            echo "  Restoring PVC: $PVC_NAME"
            
            # Find pod using this PVC
            POD=$(kubectl get pods -n $NAMESPACE -o json | \
                jq -r ".items[] | select(.spec.volumes[]?.persistentVolumeClaim.claimName == \"$PVC_NAME\") | .metadata.name" | head -1)
            
            if [ -n "$POD" ]; then
                # Wait for pod to be ready
                kubectl wait --for=condition=ready pod/$POD -n $NAMESPACE --timeout=60s || true
                
                # Get mount path
                MOUNT_PATH=$(kubectl get pod $POD -n $NAMESPACE -o json | \
                    jq -r ".spec.containers[0].volumeMounts[] | select(.name == \"data\" or .name == \"logs\") | .mountPath" | head -1)
                
                if [ -n "$MOUNT_PATH" ]; then
                    # Copy backup to pod
                    kubectl cp "$BACKUP_FILE" $NAMESPACE/$POD:/tmp/$PVC_NAME.tar.gz
                    
                    # Extract in pod
                    kubectl exec -n $NAMESPACE $POD -- tar xzf /tmp/$PVC_NAME.tar.gz -C /
                    kubectl exec -n $NAMESPACE $POD -- rm /tmp/$PVC_NAME.tar.gz
                    
                    echo -e "${GREEN}  ✓ Restored $PVC_NAME${NC}"
                fi
            fi
        fi
    done
    
    # Restore database (if PostgreSQL)
    if [ -f "$BACKUP_PATH/database.sql" ]; then
        echo "Restoring PostgreSQL database..."
        DB_POD=$(kubectl get pods -n $NAMESPACE -l app=postgres -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)
        
        if [ -n "$DB_POD" ]; then
            kubectl wait --for=condition=ready pod/$DB_POD -n $NAMESPACE --timeout=60s || true
            kubectl exec -n $NAMESPACE $DB_POD -i -- psql -U aiagent aiagent < "$BACKUP_PATH/database.sql"
            echo -e "${GREEN}  ✓ Database restored${NC}"
        fi
    fi
    
    # Scale up deployment
    echo "Scaling up deployment..."
    kubectl scale deployment ai-agent-app -n $NAMESPACE --replicas=3
    
    # Wait for pods to be ready
    echo "Waiting for application to be ready..."
    kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=ai-agent -n $NAMESPACE --timeout=120s
    
    # Cleanup
    rm -rf "$TEMP_DIR"
    
    echo -e "${GREEN}✓ Restore completed${NC}"
    
else
    echo -e "${RED}Error: Neither Velero nor kubectl is available${NC}"
    exit 1
fi

# Verify restore
echo ""
echo -e "${YELLOW}Verifying restore...${NC}"
kubectl get pods -n $NAMESPACE
echo ""
kubectl get pvc -n $NAMESPACE

echo ""
echo -e "${GREEN}Restore completed successfully!${NC}"
echo -e "${YELLOW}Please verify application functionality${NC}"
