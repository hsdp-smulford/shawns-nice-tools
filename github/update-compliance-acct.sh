#!/bin/bash -e

# Variables
REPO=philips-internal/aft-custom-guardrails
WORKFLOW=guardrails-deployment.yaml
ACCOUNT_ID=""
REGIONS=""
ENVIRONMENT="$1"; shift

# Function to display the help message
function display_help() {
    echo "Usage: $0 [dev|prod] -r regions"
    echo
    echo "This script is used to update the compliance account in the AWS Control Tower"
    echo "environment for organization config rules."
    echo
    echo "Arguments:"
    echo "  dev|prod:  The environment to update the compliance account for."
    echo "  -r regions:  The regions to enable the config rules in, separated by commas; default is all regions."
    echo "  -h:  Display this help message."
    exit 1
}

# Check if the first argument is -h to display the help message
if [ "$1" == "-h" ]; then
    display_help
fi

# Determine the account ID based on the environment
case $ENVIRONMENT in
    dev)
        ACCOUNT_ID=767397720858
        BRANCH=develop
        ;;
    prod)
        ACCOUNT_ID=891377304704
        BRANCH=main
        ;;
    *)
        echo "Error: Invalid environment specified. Use 'dev' or 'prod'."
        display_help
        ;;
esac

# Check if REGIONS is provided and not empty
if [[ -n "$REGIONS" ]]; then
    # If REGIONS is provided, include it in the command
    gh workflow run "$WORKFLOW" \
      -R "$REPO" \
      -r "$BRANCH" \
      -f account_id="$ACCOUNT_ID" \
      -f aws_regions="$REGIONS"
else
    # If REGIONS is not provided, omit it from the command
    gh workflow run "$WORKFLOW" \
      -R "$REPO" \
      -r "$BRANCH" \
      -f account_id="$ACCOUNT_ID"
fi
