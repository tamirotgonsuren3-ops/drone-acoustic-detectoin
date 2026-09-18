#!/usr/bin/env bash
set -euo pipefail

MQTT_USER="tamir"
MQTT_PASS="@ns!bl3"
MQTT_PORT=1883
BIND_ADDR="0.0.0.0"
CONF_DIR="/var/snap/mosquitto/common"
PASSWORD_FILE="$CONF_DIR/password_file"
CONF_FILE="$CONF_DIR/mosquitto.conf"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}   SoundSense MQTT Server Setup${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

if [ "$(id -u)" -ne 0 ]; then
    echo -e "${RED}This script needs root. Run with sudo:${NC}"
    echo -e "  ${BOLD}sudo bash $0${NC}"
    exit 1
fi

echo -e "${YELLOW}[1/4] Creating password file...${NC}"
mosquitto_passwd -c -b "$PASSWORD_FILE" "$MQTT_USER" "$MQTT_PASS"
chmod 600 "$PASSWORD_FILE"
echo -e "  User: ${GREEN}$MQTT_USER${NC}"

echo -e "${YELLOW}[2/4] Writing config...${NC}"
cat > "$CONF_FILE" << EOF
listener $MQTT_PORT $BIND_ADDR
allow_anonymous false
password_file $PASSWORD_FILE
persistence true
persistence_location /var/snap/mosquitto/common/
log_dest file /var/snap/mosquitto/common/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information
max_queued_messages 1000
max_inflight_messages 20
EOF
echo -e "  Config: ${GREEN}$CONF_FILE${NC}"

echo -e "${YELLOW}[3/4] Restarting mosquitto...${NC}"
snap restart mosquitto
sleep 2

echo -e "${YELLOW}[4/4] Testing connection...${NC}"
if mosquitto_pub -t test/setup -m "ok" -h localhost -p "$MQTT_PORT" -u "$MQTT_USER" -P "$MQTT_PASS" 2>/dev/null; then
    echo -e "  ${GREEN}Connection OK${NC}"
else
    echo -e "  ${RED}Connection FAILED - check logs${NC}"
    exit 1
fi

IP_ADDR=$(hostname -I 2>/dev/null | awk '{print $1}')
[ -z "$IP_ADDR" ] && IP_ADDR="<this-machine-ip>"

echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}   MQTT Server Credentials${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "  ${BOLD}Server Address:${NC}  ${GREEN}$IP_ADDR${NC}"
echo -e "  ${BOLD}Port:${NC}            ${GREEN}$MQTT_PORT${NC}"
echo -e "  ${BOLD}Username:${NC}        ${GREEN}$MQTT_USER${NC}"
echo -e "  ${BOLD}Password:${NC}        ${GREEN}$MQTT_PASS${NC}"
echo -e "  ${BOLD}Protocol:${NC}        ${GREEN}TCP${NC}"
echo ""
echo -e "${CYAN}----------------------------------------${NC}"
echo -e "  ${BOLD}Connect URL:${NC}"
echo -e "  ${GREEN}tcp://$IP_ADDR:$MQTT_PORT${NC}"
echo -e "  ${GREEN}mqtt://$IP_ADDR:$MQTT_PORT${NC}"
echo -e "${CYAN}----------------------------------------${NC}"
echo ""
echo -e "  ${BOLD}Web App (SoundSense):${NC}"
echo -e "  Server:   ${GREEN}$IP_ADDR${NC}"
echo -e "  Port:     ${GREEN}$MQTT_PORT${NC}"
echo -e "  User:     ${GREEN}$MQTT_USER${NC}"
echo -e "  Password: ${GREEN}$MQTT_PASS${NC}"
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${YELLOW}Use these credentials in SoundSense app!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
