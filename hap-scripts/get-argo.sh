#!/bin/zsh

# This script retrieves ArgoCD credentials and opens ArgoCD in the Brave browser.

# Define colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
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

# Function to get ArgoCD credentials
get_argocd_credentials() {
  echo -e "${YELLOW}Retrieving ArgoCD credentials... 🕵️${NC}"

  argocd_endpoint=$(kubectl get ingress argocd-server -n argocd -o jsonpath='{.spec.rules[0].host}')
  argocd_password=$(kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath='{.data.password}' | base64 -d)

  echo -e "${GREEN}ArgoCD credentials retrieved. ✅${NC}"
}

# Function to open ArgoCD in the browser
open_argocd() {
  echo -e "${GREEN}Opening ArgoCD in the browser... 🚀${NC}"

  echo "${argocd_password}" | pbcopy
  echo -e "Log into ArgoCD as: ${BLUE}admin${NC}; password is saved to clipboard. 📋"

  open -a "Brave Browser.app" "http://$argocd_endpoint"
}

# Main script execution
get_argocd_credentials
open_argocd