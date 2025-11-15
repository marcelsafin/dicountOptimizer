#!/bin/bash
# Type checking script for CI/CD pipeline
# This script validates type coverage for all refactored modules

set -e  # Exit on error

echo "=========================================="
echo "Running Type Checking Validation"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall success
OVERALL_SUCCESS=true

# Function to run mypy on a module
check_module() {
    local module_path=$1
    local module_name=$2
    
    echo "Checking ${module_name}..."
    if mypy "${module_path}" --show-error-codes --pretty; then
        echo -e "${GREEN}✓ ${module_name} passed type checking${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ ${module_name} failed type checking${NC}"
        echo ""
        OVERALL_SUCCESS=false
        return 1
    fi
}

# Check all refactored modules with strict type checking
echo "Phase 1: Domain Layer (Strict Type Checking)"
echo "--------------------------------------------"
check_module "agents/discount_optimizer/domain/" "Domain Models"

echo "Phase 2: Infrastructure Layer (Strict Type Checking)"
echo "----------------------------------------------------"
check_module "agents/discount_optimizer/infrastructure/" "Infrastructure Repositories"

echo "Phase 3: Configuration & Logging (Strict Type Checking)"
echo "-------------------------------------------------------"
check_module "agents/discount_optimizer/config.py" "Configuration"
check_module "agents/discount_optimizer/logging.py" "Logging"

echo "Phase 4: Agent Layer (Strict Type Checking)"
echo "-------------------------------------------"
check_module "agents/discount_optimizer/agents/" "ADK Agents"

echo "Phase 5: Services Layer (Strict Type Checking)"
echo "----------------------------------------------"
check_module "agents/discount_optimizer/services/" "Business Services"

echo "Phase 6: Factory (Strict Type Checking)"
echo "---------------------------------------"
check_module "agents/discount_optimizer/factory.py" "Agent Factory"

echo ""
echo "=========================================="
echo "Type Checking Summary"
echo "=========================================="

if [ "$OVERALL_SUCCESS" = true ]; then
    echo -e "${GREEN}✓ All refactored modules passed strict type checking!${NC}"
    echo ""
    echo "Modules checked:"
    echo "  - Domain layer (models, protocols, exceptions)"
    echo "  - Infrastructure layer (repositories)"
    echo "  - Configuration and logging"
    echo "  - Agent layer (ADK agents)"
    echo "  - Services layer (business logic)"
    echo "  - Factory (dependency injection)"
    echo ""
    echo "Type coverage: 100% for refactored modules"
    exit 0
else
    echo -e "${RED}✗ Some modules failed type checking${NC}"
    echo ""
    echo "Please fix the type errors above before committing."
    exit 1
fi
