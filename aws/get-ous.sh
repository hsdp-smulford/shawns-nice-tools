#!/bin/bash

# Script: get-ous.sh
# Purpose: Get a tree-like structure of the OU structure
# Prerequisites: Must be targeting the account hosting the AWS Organization. If not, add appropriate roles.
# Invocation: ./get-ous.sh

# Color definitions for better visibility
COLOR_BLUE='\033[0;34m'
COLOR_GREEN='\033[0;32m'
COLOR_RED='\033[0;31m'
COLOR_RESET='\033[0m'

# Function to handle errors
handle_error() {
    local exit_code=$1
    local message=$2
    if [ "$exit_code" -ne 0 ]; then
        echo -e "${COLOR_RED}ERROR${COLOR_RESET}: $message"
        exit 1
    fi
}

# Function to recursively fetch OUs for a given parent ID
list_ous() {
    local parent_id=$1
    local indent=$2

    ous=$(aws organizations list-organizational-units-for-parent --parent-id "$parent_id" \
        --query 'OrganizationalUnits[*].[Id,Name]' --output text)

    handle_error $? "Failed to fetch OUs for parent ${parent_id}."

    if [ -z "$ous" ]; then
        return
    fi

    while IFS=$'\t' read -r ou_id ou_name; do
        echo -e "${indent}${COLOR_GREEN}${ou_id}${COLOR_RESET} [${COLOR_BLUE}${ou_name}${COLOR_RESET}]"
        list_ous "$ou_id" "$indent|  "
    done <<< "$ous"
}

root_account_id=$(aws organizations describe-organization --query 'Organization.MasterAccountId' --output text)
handle_error $? "Failed to retrieve the root account ID."

root_account_name=$(aws organizations describe-account --account-id "$root_account_id" --query 'Account.Name' --output text)
handle_error $? "Failed to retrieve the root account name."

# Start from the root
root_id=$(aws organizations list-roots --query 'Roots[0].Id' --output text)
handle_error $? "Failed to retrieve the root ID."

echo -e "${COLOR_BLUE}Root Account${COLOR_RESET}: ${root_account_name} [${root_account_id}]"
list_ous "$root_id" ""
