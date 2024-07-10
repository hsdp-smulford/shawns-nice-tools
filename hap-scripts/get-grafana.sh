#!/bin/zsh

# This script retrieves Grafana credentials and opens Grafana in the Brave browser.

# Define colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Check if required commands are available
for cmd in kubectl pbcopy open; do
  if ! command_exists $cmd; then
    echo -e "${RED}Error: $cmd is not installed 😢${NC}" >&2
    exit 1
  fi
done

# Function to get Grafana credentials
get_grafana_credentials() {
  echo -e "${GREEN}Retrieving Grafana credentials... 🕵️${NC}"

  grafana_endpoint=$(kubectl get ingress grafana -n grafana -o jsonpath='{.spec.rules[0].host}')
  grafana_username=$(kubectl get secret grafana -n grafana -o jsonpath='{.data.admin-user}' | base64 -d)
  grafana_password=$(kubectl get secret grafana -n grafana -o jsonpath='{.data.admin-password}' | base64 -d)

  echo -e "${GREEN}Grafana credentials retrieved. ✅${NC}"
}

# Function to open Grafana in the browser
open_grafana() {
  echo -e "${GREEN}Opening Grafana in the browser... 🚀${NC}"

  echo "${grafana_password}" | pbcopy
  echo -e "Log into Grafana as: ${BLUE}${grafana_username}${NC}; password is saved to clipboard. 📋"

  open "http://$grafana_endpoint"
}

# Main script execution
get_grafana_credentials
open_grafana