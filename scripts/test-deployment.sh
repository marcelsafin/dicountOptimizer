#!/bin/bash
# End-to-end deployment test script
# This script tests a deployed Cloud Run service to verify it's working correctly
#
# Usage:
#   ./scripts/test-deployment.sh [SERVICE_URL]
#
# If SERVICE_URL is not provided, it will be fetched from gcloud
#
# Requirements: 9.5, 10.6

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SERVICE_URL="${1:-}"
REGION="${REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-shopping-optimizer}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Shopping Optimizer - Deployment Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get service URL if not provided
if [ -z "$SERVICE_URL" ]; then
    echo -e "${YELLOW}Fetching service URL...${NC}"
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)" 2>/dev/null || echo "")
    
    if [ -z "$SERVICE_URL" ]; then
        echo -e "${RED}Error: Could not get service URL${NC}"
        echo "Provide it manually: ./scripts/test-deployment.sh https://your-service-url"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Service URL: $SERVICE_URL${NC}"
fi

echo ""
echo "Testing service at: $SERVICE_URL"
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to run tests
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_status="${3:-200}"
    
    echo -e "${YELLOW}Testing: $test_name${NC}"
    
    # Run the test
    HTTP_STATUS=$(curl -s -o /tmp/test_response.json -w "%{http_code}" "$test_command" || echo "000")
    
    if [ "$HTTP_STATUS" = "$expected_status" ]; then
        echo -e "${GREEN}✓ PASSED${NC} (HTTP $HTTP_STATUS)"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        
        # Show response if it's JSON
        if [ -f /tmp/test_response.json ]; then
            if command -v jq &> /dev/null; then
                echo "Response:"
                cat /tmp/test_response.json | jq '.' 2>/dev/null || cat /tmp/test_response.json
            fi
        fi
    else
        echo -e "${RED}✗ FAILED${NC} (Expected HTTP $expected_status, got HTTP $HTTP_STATUS)"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        
        # Show error response
        if [ -f /tmp/test_response.json ]; then
            echo "Response:"
            cat /tmp/test_response.json
        fi
    fi
    
    echo ""
}

# Test 1: Basic health check
run_test "Basic Health Check" "$SERVICE_URL/health" 200

# Test 2: Detailed health check
run_test "Detailed Health Check" "$SERVICE_URL/health/detailed" 200

# Test 3: Metrics summary
run_test "Metrics Summary" "$SERVICE_URL/metrics/summary" 200

# Test 4: Full metrics
run_test "Full Metrics" "$SERVICE_URL/metrics" 200

# Test 5: Prometheus metrics
echo -e "${YELLOW}Testing: Prometheus Metrics${NC}"
HTTP_STATUS=$(curl -s -o /tmp/test_response.txt -w "%{http_code}" "$SERVICE_URL/metrics/prometheus" || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC} (HTTP $HTTP_STATUS)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    
    # Verify it's in Prometheus format
    if grep -q "^# HELP" /tmp/test_response.txt; then
        echo "Format: Valid Prometheus text format"
    else
        echo -e "${YELLOW}⚠ Warning: Response doesn't look like Prometheus format${NC}"
    fi
else
    echo -e "${RED}✗ FAILED${NC} (Expected HTTP 200, got HTTP $HTTP_STATUS)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""

# Test 6: API endpoint with sample request
echo -e "${YELLOW}Testing: API Optimization Endpoint${NC}"

# Create test request
TEST_REQUEST='{
  "location": "55.6761,12.5683",
  "meals": ["taco", "pasta"],
  "preferences": {
    "maximize_savings": true,
    "minimize_stores": false,
    "prefer_organic": false
  }
}'

HTTP_STATUS=$(curl -s -o /tmp/test_response.json -w "%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$TEST_REQUEST" \
    "$SERVICE_URL/api/optimize" || echo "000")

if [ "$HTTP_STATUS" = "200" ]; then
    echo -e "${GREEN}✓ PASSED${NC} (HTTP $HTTP_STATUS)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    
    # Verify response structure
    if command -v jq &> /dev/null; then
        SUCCESS=$(cat /tmp/test_response.json | jq -r '.success' 2>/dev/null || echo "false")
        
        if [ "$SUCCESS" = "true" ]; then
            echo "API Response: Success"
            
            # Show key metrics
            TOTAL_SAVINGS=$(cat /tmp/test_response.json | jq -r '.recommendation.total_savings' 2>/dev/null || echo "N/A")
            NUM_PURCHASES=$(cat /tmp/test_response.json | jq -r '.recommendation.purchases | length' 2>/dev/null || echo "N/A")
            
            echo "  - Total Savings: $TOTAL_SAVINGS"
            echo "  - Number of Purchases: $NUM_PURCHASES"
        else
            ERROR=$(cat /tmp/test_response.json | jq -r '.error' 2>/dev/null || echo "Unknown error")
            echo -e "${YELLOW}⚠ API returned success=false: $ERROR${NC}"
        fi
    fi
else
    echo -e "${RED}✗ FAILED${NC} (Expected HTTP 200, got HTTP $HTTP_STATUS)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    
    if [ -f /tmp/test_response.json ]; then
        echo "Response:"
        cat /tmp/test_response.json
    fi
fi

echo ""

# Test 7: Invalid request handling
echo -e "${YELLOW}Testing: Invalid Request Handling${NC}"

INVALID_REQUEST='{}'

HTTP_STATUS=$(curl -s -o /tmp/test_response.json -w "%{http_code}" \
    -X POST \
    -H "Content-Type: application/json" \
    -d "$INVALID_REQUEST" \
    "$SERVICE_URL/api/optimize" || echo "000")

if [ "$HTTP_STATUS" = "400" ]; then
    echo -e "${GREEN}✓ PASSED${NC} (HTTP $HTTP_STATUS - correctly rejected invalid request)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${YELLOW}⚠ WARNING${NC} (Expected HTTP 400, got HTTP $HTTP_STATUS)"
    echo "Service should return 400 for invalid requests"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""

# Performance test
echo -e "${YELLOW}Testing: Response Time${NC}"

START_TIME=$(date +%s%N)
curl -s -o /dev/null "$SERVICE_URL/health"
END_TIME=$(date +%s%N)

RESPONSE_TIME=$(( (END_TIME - START_TIME) / 1000000 ))

echo "Response time: ${RESPONSE_TIME}ms"

if [ "$RESPONSE_TIME" -lt 1000 ]; then
    echo -e "${GREEN}✓ PASSED${NC} (Response time < 1s)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
elif [ "$RESPONSE_TIME" -lt 3000 ]; then
    echo -e "${YELLOW}⚠ WARNING${NC} (Response time between 1-3s - acceptable but could be improved)"
    TESTS_PASSED=$((TESTS_PASSED + 1))
else
    echo -e "${RED}✗ FAILED${NC} (Response time > 3s - too slow)"
    TESTS_FAILED=$((TESTS_FAILED + 1))
fi

echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Service URL: $SERVICE_URL"
echo ""
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
SUCCESS_RATE=$(( TESTS_PASSED * 100 / TOTAL_TESTS ))

echo "Success Rate: ${SUCCESS_RATE}%"
echo ""

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "The deployment is working correctly."
    echo ""
    echo "Next steps:"
    echo "  1. Test the frontend: open $SERVICE_URL in a browser"
    echo "  2. Monitor logs: gcloud logging tail \"resource.type=cloud_run_revision\""
    echo "  3. Set up monitoring alerts"
    echo "  4. Configure custom domain (optional)"
    exit 0
else
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}Some tests failed ✗${NC}"
    echo -e "${RED}========================================${NC}"
    echo ""
    echo "Please review the failures above and check:"
    echo "  1. Service logs: gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=$SERVICE_NAME\" --limit=50"
    echo "  2. Service status: gcloud run services describe $SERVICE_NAME --region=$REGION"
    echo "  3. Dependencies: curl $SERVICE_URL/health/detailed"
    exit 1
fi
