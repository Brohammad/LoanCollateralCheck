#!/bin/bash
# Database Migration Script for AI Agent System

set -e

# Configuration
NAMESPACE="${NAMESPACE:-ai-agent}"
DEPLOYMENT="${DEPLOYMENT:-ai-agent-app}"
DATABASE_URL="${DATABASE_URL}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AI Agent Database Migration ===${NC}"

# Check if running in Kubernetes
if command -v kubectl &> /dev/null; then
    echo -e "${YELLOW}Running migration in Kubernetes...${NC}"
    
    # Get the first pod
    POD=$(kubectl get pods -n $NAMESPACE -l app.kubernetes.io/name=ai-agent -o jsonpath='{.items[0].metadata.name}')
    
    if [ -z "$POD" ]; then
        echo -e "${RED}Error: No pods found in namespace $NAMESPACE${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Using pod: $POD${NC}"
    
    # Run migration
    kubectl exec -n $NAMESPACE $POD -- python -c "
from database.init_db import init_database
from database.db_manager import DatabaseManager

print('Initializing database...')
init_database()

print('Running migrations...')
db = DatabaseManager()

# Check if tables exist
tables = db.execute('SELECT name FROM sqlite_master WHERE type=\"table\"').fetchall()
print(f'Found {len(tables)} tables: {[t[0] for t in tables]}')

print('Migration completed successfully!')
"
    
    echo -e "${GREEN}✓ Migration completed${NC}"
    
else
    # Running locally
    echo -e "${YELLOW}Running migration locally...${NC}"
    
    if [ -z "$DATABASE_URL" ]; then
        echo -e "${YELLOW}DATABASE_URL not set, using default SQLite database${NC}"
        DATABASE_URL="sqlite:///./data/dev.db"
    fi
    
    python3 << END
from database.init_db import init_database
from database.db_manager import DatabaseManager
import os

os.environ['DATABASE_URL'] = '$DATABASE_URL'

print('Initializing database...')
init_database()

print('Running migrations...')
db = DatabaseManager()

# Check if tables exist
tables = db.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()
print(f'Found {len(tables)} tables: {[t[0] for t in tables]}')

print('Migration completed successfully!')
END
    
    echo -e "${GREEN}✓ Migration completed${NC}"
fi
