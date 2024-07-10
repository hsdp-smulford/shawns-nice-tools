#!/opt/homebrew/bin/bash -e

# Purpose: Get all accounts in the organization to run the `guardrails-destroy.yaml` workflow on
# Pre-requisites:
#   1. Already logged in the AWS environment
#   2. Running BASH < 4.0, needed for readarray command
#   3. Have the gh cli installed and authenticated, needed to trigger the workflow
# Usage: sh .github/workflows/run-guardrails-destroy.sh

echo "Current shell: $SHELL"
echo "Bash version: $BASH_VERSION"

# Variables
AWS_PROFILE=dev-payer
AWS_DEFAULT_REGION=us-east-1
ACCOUNTS_TO_IGNORE="run-guardrails-destroy-ignored-accounts.txt"
LOG_FILE=/var/log/hsp/run-guardrails-destroy.log
PAYER_ACCOUNTS=(532619675006 485027120931)

REPO=philips-internal/aft-custom-guardrails
WORKFLOW=guardrails-destroy.yaml
BRANCH=removing-guardrails-in-satellite-accts
#AWS_REGIONS="us-east-1" # Optional: If you want to run the workflow in specific regions

# Set AWS CLI profile and region
export AWS_PROFILE=$AWS_PROFILE
export AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION

CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

log_dir=$(dirname "$LOG_FILE")
if [ -d "$log_dir" ]; then
  echo "Log directory exists: ${log_dir}"
else
  mkdir -p "${log_dir}"
fi

if [[ ! -f $LOG_FILE ]]; then
  touch $LOG_FILE
fi

echo "Logging message available at: ${LOG_FILE}"

# Check if the current account is in the MANAGEMENT_ACCOUNTS array
if ! [[ " ${PAYER_ACCOUNTS[*]} " =~ $CURRENT_ACCOUNT ]]; then
  echo "[$(date)]; ERROR; This script must be run from a payer account. Currently running from account: $CURRENT_ACCOUNT" | tee -a $LOG_FILE
  exit 99
else
  echo "[$(date)]; Confirmed that the script is running from a management account: $CURRENT_ACCOUNT" | tee -a $LOG_FILE
fi

readarray -t IGNORED_ACCOUNTS < "$ACCOUNTS_TO_IGNORE"
IGNORED_ACCOUNTS=($(printf "%s\n" "${IGNORED_ACCOUNTS[@]}" | sort -n))
echo "[$(date)]; Ignoring the following accounts [${#IGNORED_ACCOUNTS[@]}]: ${IGNORED_ACCOUNTS[*]}" | tee -a $LOG_FILE

# Create an associative array to efficiently check ignored accounts
declare -A IGNORED_ACCOUNTS_MAP
for id in "${IGNORED_ACCOUNTS[@]}"; do
    IGNORED_ACCOUNTS_MAP["$id"]=1
done

ALL_ACCOUNT_IDS=($(aws organizations list-accounts --no-paginate --query 'Accounts[].Id' --output text))
ALL_ACCOUNT_IDS=($(printf "%s\n" "${ALL_ACCOUNT_IDS[@]}" | sort -n))
echo "[$(date)]; Found accounts in the organization [${#ALL_ACCOUNT_IDS[@]}]: ${ALL_ACCOUNT_IDS[*]}" | tee -a $LOG_FILE

# Filter out ignored accounts
ACCOUNT_IDS=()
for id in "${ALL_ACCOUNT_IDS[@]}"; do
    if [[ ! ${IGNORED_ACCOUNTS_MAP[$id]} ]]; then
        ACCOUNT_IDS+=("$id")
    fi
done
echo "[$(date)]; Accounts to run the guardrails-destroy workflow on [${#ACCOUNT_IDS[@]}]: ${ACCOUNT_IDS[*]}" | tee -a $LOG_FILE

echo "[$(date)]; Triggering the guardrails-destroy workflow on all non-ignored accounts" | tee -a $LOG_FILE
for account_id in "${ACCOUNT_IDS[@]}"; do
    #gh workflow run $WORKFLOW -R $REPO -r $BRANCH -f account_id=$account_id
    # gh workflow run $WORKFLOW -R $REPO -r $BRANCH -f account_id=$account_id -f aws_regions=$AWS_REGIONS
    echo "[$(date)]; Triggered ${WORKFLOW}, from ${BRANCH}, on account: $account_id" | tee -a $LOG_FILE
done
