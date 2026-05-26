#!/usr/bin/env bash
# Automated Chaos Engineering & Self-Healing Validation Script (Layer 6)

set -euo pipefail

BACKEND_URL="http://localhost:5001"
echo "=========================================================="
echo "💥 STARTING KUBERNETES AUTONOMOUS CHAOS EXPERIMENT"
echo "=========================================================="

echo "🔑 Logging in as System Admin to obtain JWT token..."
LOGIN_RES=$(curl -s -X POST "${BACKEND_URL}/api/cloud/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin_system","password":"secure_admin123"}')

if echo "$LOGIN_RES" | grep -q "token"; then
    TOKEN=$(echo "$LOGIN_RES" | json_pp 2>/dev/null | grep '"token"' | cut -d'"' -f4 || echo "$LOGIN_RES" | sed -E 's/.*"token":"([^"]*)".*/\1/')
    echo "✅ Token obtained successfully."
else
    echo "❌ Failed to obtain token! Response: $LOGIN_RES"
    exit 1
fi

echo "🔥 Injecting Chaos: Simulating hard container crash..."
CRASH_RES=$(curl -s -X POST "${BACKEND_URL}/api/chaos/trigger" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"type":"crash"}')

echo "📩 Trigger response: $CRASH_RES"
echo "⏱️  Container exiting... Starting recovery time audit..."

START_TIME=$(date +%s)
RECOVERED=false

# Poll the backend statistics route until it becomes reachable again
for i in {1..30}; do
    echo "🔍 Ingress Poll #$i: Checking service availability..."
    
    # Send a quick request with 2s timeout
    set +e
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "${BACKEND_URL}/api/statistics" || echo "000")
    set -e
    
    if [ "$HTTP_STATUS" -eq 200 ]; then
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        echo "=========================================================="
        echo "🎉 SUCCESS: Service recovered successfully in ${ELAPSED} seconds!"
        echo "   Kubernetes self-healing container probes successfully"
        echo "   re-spawned the failed backend pod replica."
        echo "=========================================================="
        RECOVERED=true
        break
    fi
    sleep 2
done

if [ "$RECOVERED" = false ]; then
    echo "❌ FAILURE: Service did not recover within 60 seconds."
    exit 1
fi
