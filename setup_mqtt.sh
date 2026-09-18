#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}   Mosquitto WebSocket Setup${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}Root required. Run:${NC}"
    echo -e "  ${BOLD}sudo bash $0${NC}"
    exit 1
fi

MQTT_USER="tamir"
MQTT_PASS="@ns!bl3"
CONF_DIR="/var/snap/mosquitto/common"
CONF_FILE="$CONF_DIR/mosquitto.conf"
PASSWORD_FILE="$CONF_DIR/password_file"

# Step 1: password file
echo -e "${YELLOW}[1/3] Password file...${NC}"
if [ ! -f "$PASSWORD_FILE" ]; then
    mosquitto_passwd -c -b "$PASSWORD_FILE" "$MQTT_USER" "$MQTT_PASS"
    chmod 600 "$PASSWORD_FILE"
    echo -e "  ${GREEN}Created${NC}"
else
    echo -e "  ${GREEN}Exists${NC}"
fi

# Step 2: config
echo -e "${YELLOW}[2/3] Writing config with WebSocket support...${NC}"
cat > "$CONF_FILE" << 'EOF'
# TCP listener (for terminal mosquitto_pub/sub)
listener 1883 0.0.0.0

# WebSocket listener (for web browser)
listener 9001 0.0.0.0
protocol websockets

# Auth
allow_anonymous false
password_file /var/snap/mosquitto/common/password_file

# Persistence
persistence true
persistence_location /var/snap/mosquitto/common/

# Logging
log_dest file /var/snap/mosquitto/common/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information
log_type subscribe
log_type unsubscribe

# Limits
max_queued_messages 1000
max_inflight_messages 20
max_connections -1
EOF
echo -e "  ${GREEN}$CONF_FILE${NC}"

# Step 3: restart
echo -e "${YELLOW}[3/3] Restarting mosquitto...${NC}"
snap restart mosquitto
sleep 2

# Verify
echo ""
echo -e "${YELLOW}Verifying...${NC}"
ERRORS=0

if ss -tlnp | grep -q ":1883 "; then
    echo -e "  ${GREEN}TCP  1883 OK${NC}"
else
    echo -e "  ${RED}TCP  1883 FAILED${NC}"
    ERRORS=$((ERRORS+1))
fi

if ss -tlnp | grep -q ":9001 "; then
    echo -e "  ${GREEN}WS   9001 OK${NC}"
else
    echo -e "  ${RED}WS   9001 FAILED${NC}"
    ERRORS=$((ERRORS+1))
fi

# Test TCP auth
if mosquitto_pub -t test/setup -m "tcp_ok" -h localhost -p 1883 -u "$MQTT_USER" -P "$MQTT_PASS" 2>/dev/null; then
    echo -e "  ${GREEN}TCP auth OK${NC}"
else
    echo -e "  ${RED}TCP auth FAILED${NC}"
    ERRORS=$((ERRORS+1))
fi

# Get IP
IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$IP_ADDR" ] && IP_ADDR="<this-machine-ip>"

echo ""
echo -e "${CYAN}========================================${NC}"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}  ALL OK!${NC}"
else
    echo -e "${RED}  $ERRORS errors detected${NC}"
fi
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "  ${BOLD}Server:${NC}     ${GREEN}$IP_ADDR${NC}"
echo -e "  ${BOLD}TCP Port:${NC}   ${GREEN}1883${NC}  (terminal apps)"
echo -e "  ${BOLD}WS Port:${NC}    ${GREEN}9001${NC}  (web browser)"
echo -e "  ${BOLD}Username:${NC}   ${GREEN}$MQTT_USER${NC}"
echo -e "  ${BOLD}Password:${NC}   ${GREEN}$MQTT_PASS${NC}"
echo ""
echo -e "  ${BOLD}Web App MQTT Settings:${NC}"
echo -e "  Server: ${GREEN}$IP_ADDR${NC}"
echo -e "  Port:   ${GREEN}9001${NC}"
echo -e "  User:   ${GREEN}$MQTT_USER${NC}"
echo -e "  Pass:   ${GREEN}$MQTT_PASS${NC}"
echo ""
echo -e "${CYAN}========================================${NC}"
echo ""
