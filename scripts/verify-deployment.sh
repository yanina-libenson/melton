#!/bin/bash
# Script to verify Melton deployment on Render.com

set -e

echo "=========================================="
echo "Melton Deployment Verification"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check endpoint
check_endpoint() {
    local url=$1
    local name=$2

    echo -n "Checking $name... "

    if curl -s -f -o /dev/null -w "%{http_code}" "$url" | grep -q "200\|301\|302"; then
        echo -e "${GREEN}✓ OK${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        return 1
    fi
}

# Function to check JSON endpoint
check_json_endpoint() {
    local url=$1
    local name=$2

    echo -n "Checking $name... "

    response=$(curl -s "$url")
    if echo "$response" | grep -q "status\|healthy"; then
        echo -e "${GREEN}✓ OK${NC}"
        echo "  Response: $response"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo "  Response: $response"
        return 1
    fi
}

echo "1. Checking DNS Resolution"
echo "-------------------------------------------"
echo "Frontend (meltonagents.com):"
nslookup meltonagents.com | grep -A 2 "Name:" || echo -e "${RED}DNS not configured${NC}"
echo ""
echo "API (api.meltonagents.com):"
nslookup api.meltonagents.com | grep -A 2 "Name:" || echo -e "${RED}DNS not configured${NC}"
echo ""

echo "2. Checking SSL Certificates"
echo "-------------------------------------------"
check_endpoint "https://meltonagents.com" "Frontend SSL"
check_endpoint "https://api.meltonagents.com" "Backend SSL"
echo ""

echo "3. Checking API Endpoints"
echo "-------------------------------------------"
check_json_endpoint "https://api.meltonagents.com/health" "Health Check"
check_json_endpoint "https://api.meltonagents.com" "Root Endpoint"
echo ""

echo "4. Checking API Documentation"
echo "-------------------------------------------"
check_endpoint "https://api.meltonagents.com/docs" "Swagger UI"
check_endpoint "https://api.meltonagents.com/redoc" "ReDoc"
echo ""

echo "5. Checking Frontend"
echo "-------------------------------------------"
check_endpoint "https://meltonagents.com" "Frontend Home"
check_endpoint "https://www.meltonagents.com" "Frontend WWW"
echo ""

echo "6. Checking CORS (from frontend to backend)"
echo "-------------------------------------------"
echo -n "Testing CORS... "
curl -s -H "Origin: https://meltonagents.com" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS https://api.meltonagents.com/health | grep -q "access-control" && \
     echo -e "${GREEN}✓ OK${NC}" || echo -e "${RED}✗ FAILED${NC}"
echo ""

echo "=========================================="
echo "Verification Complete"
echo "=========================================="
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Test user registration at https://meltonagents.com"
echo "2. Create a test agent"
echo "3. Test agent conversations"
echo "4. Check logs in Render dashboard"
echo "5. Set up monitoring and alerts"
echo ""
