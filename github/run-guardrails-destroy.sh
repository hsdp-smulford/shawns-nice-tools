#!/opt/homebrew/bin/bash -e
# shellcheck disable=SC2207,SC2016,SC2162
# Purpose: Get all accounts in the organization to run the `guardrails-destroy.yaml` workflow on
# Need help?: .github/workflows/run-guardrails-destroy.sh -h
#
# Variables
ACCOUNTS_TO_IGNORE="$(dirname "$0")/ignored-accounts.txt"
PROCESSED_ACCOUNTS="$(dirname "$0")/processed-accounts.txt"
NUMBER_OF_ACCOUNTS_TO_PROCESS=20
LOG_FILE=/var/log/hsp/run-guardrails-destroy.log
PAYER_ACCOUNTS=(532619675006 485027120931)
REPO=philips-internal/aft-custom-guardrails
WORKFLOW=guardrails-destroy.yaml
BRANCH=removing-guardrails-in-satellite-accts
AWS_REGIONS="" # Initialize AWS_REGIONS variable

# Helper
show_help() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Description:"
  echo "  This script triggers the '${WORKFLOW}' workflow for active AWS"
  echo "  accounts in the organization, excluding specified accounts."
  echo ""
  echo "Options:"
  echo "  -h, --help                    Show this help message and exit."
  echo "  -a, --accounts=<id1,id2,...>  Comma-separated list of account IDs to run the workflow on."
  echo "  -r, --regions=<region1,region2,...>  Specify a comma-separated list of AWS regions."
  echo "  -n, --number-of-accounts=<number>  Number of accounts to process (default: 20)."
  echo ""
  echo "Pre-requisites:"
  echo "  1. Logged in the AWS environment, with correct AWS_PROFILE & AWS_DEFAULT_REGION exported."
  echo "  2. BASH >= 4.0 for 'readarray' command."
  echo "  3. 'gh' CLI installed and authenticated."
  echo ""
  echo "Example:"
  echo "  sh .github/workflows/run-guardrails-destroy.sh"
  echo ""
}

# Function to check if an account has been processed or is ignored
has_been_processed_or_ignored() {
    local account_id=$1
    grep -q "^$account_id$" "$PROCESSED_ACCOUNTS" && return 0
    [[ -n "${IGNORED_ACCOUNTS_MAP[$account_id]}" ]] && return 0
    return 1
}
# Function to mark an account as processed
mark_as_processed() {
    local account_id=$1
    echo "$account_id" >> "$PROCESSED_ACCOUNTS"
}

# Make sure log directory exists
log_dir=$(dirname "$LOG_FILE")
if [ ! -d "$log_dir" ]; then
  mkdir -p "${log_dir}"
  echo "[$(date)]; Created log directory: ${log_dir}"
fi

# Make sure log file exists
if [[ ! -f $LOG_FILE ]]; then
  touch $LOG_FILE
fi
echo "[$(date)]; Logging message available at: ${LOG_FILE}" | tee -a $LOG_FILE

# Parse parameters
while [[ "$#" -gt 0 ]]; do
  case $1 in
    -h|--help) show_help; exit 0 ;;
    -a|--accounts=*) ACCOUNTS_PROVIDED="${1#*=}" ;;
    -r|--regions=*) AWS_REGIONS="${1#*=}" ;;
    -n|--number-of-accounts=*) NUMBER_OF_ACCOUNTS_TO_PROCESS="${1#*=}" ;;
    *) echo "Unknown option: $1" >&2; show_help; exit 1 ;;
  esac
  shift
done

# Make the processed accounts file exists
if [ ! -f "$PROCESSED_ACCOUNTS" ]; then
    touch "$PROCESSED_ACCOUNTS"
fi
echo "[$(date)]; Accounts already processed will be tracked: ${PROCESSED_ACCOUNTS}]"  | tee -a $LOG_FILE


# Validate AWS Regions
if [[ -n "$AWS_REGIONS" ]]; then
    IFS=',' read -r -a regions_array <<< "$AWS_REGIONS"
    for region in "${regions_array[@]}"; do
        if ! [[ $region =~ ^[a-z]+-[a-z]+-[0-9]+$ ]]; then
            echo "Invalid AWS region format: $region" >&2
            exit 1
        fi
    done
fi

# Verify that both AWS_PROFILE & AWS_DEFAULT_REGION are set outside of invocation.
if [ -z "$AWS_PROFILE" ] || [ -z "$AWS_DEFAULT_REGION" ]; then
  echo "[$(date)]; ERROR; Either AWS_PROFILE or AWS_DEFAULT_REGION is not set. Please set both and try again." | tee -a $LOG_FILE
  exit 1
else
  echo "[$(date)]; AWS_PROFILE: $AWS_PROFILE; AWS_DEFAULT_REGION: $AWS_DEFAULT_REGION" | tee -a $LOG_FILE
fi

# Get current account for validation
CURRENT_ACCOUNT=$(aws sts get-caller-identity --query Account --output text)

# Check if the current account is in the MANAGEMENT_ACCOUNTS array
if ! [[ " ${PAYER_ACCOUNTS[*]} " =~ $CURRENT_ACCOUNT ]]; then
  echo "[$(date)]; ERROR; This script must be run from a payer account. Currently running from account: $CURRENT_ACCOUNT" | tee -a $LOG_FILE
  exit 1
else
  echo "[$(date)]; Confirmed that the script is running from a management account: $CURRENT_ACCOUNT" | tee -a $LOG_FILE
fi

# Determine accounts to process
if [[ -z "$ACCOUNTS_PROVIDED" ]]; then
  # Retrieve all active accounts if no accounts are provided
  # TODO: May need to paginate, someday.
  ALL_ACCOUNT_IDS=($(aws organizations list-accounts -query 'Accounts[?Status==`ACTIVE`].Id' --output text))
  ALL_ACCOUNT_IDS=($(printf "%s\n" "${ALL_ACCOUNT_IDS[@]}" | sort -n))
  ACCOUNT_IDS=("${ALL_ACCOUNT_IDS[@]}")
else
  # Use provided accounts
  IFS=',' read -r -a ACCOUNT_IDS <<< "$ACCOUNTS_PROVIDED"
fi
echo "[$(date)]; Account IDs discovered [${#ACCOUNT_IDS[@]}]: ${ACCOUNT_IDS[*]}"

# Read ignored accounts
declare -A IGNORED_ACCOUNTS_MAP
while IFS= read -r line; do
    IGNORED_ACCOUNTS_MAP["$line"]=1
done < "$ACCOUNTS_TO_IGNORE"
echo "[$(date)]; Ignoring the following accounts [${#IGNORED_ACCOUNTS_MAP[@]}]: ${!IGNORED_ACCOUNTS_MAP[*]}" | tee -a $LOG_FILE

# Filter accounts to process, excluding ignored and already processed accounts
FILTERED_ACCOUNT_IDS=()
for account_id in "${ACCOUNT_IDS[@]}"; do
    if ! has_been_processed_or_ignored "$account_id"; then
        FILTERED_ACCOUNT_IDS+=("$account_id")
    fi
    # Break if we've reached the desired number of accounts to process
    [[ "${#FILTERED_ACCOUNT_IDS[@]}" -eq "$NUMBER_OF_ACCOUNTS_TO_PROCESS" ]] && break
done

echo "[$(date)]; Accounts to run the guardrails-destroy workflow on [${#FILTERED_ACCOUNT_IDS[@]}]: ${FILTERED_ACCOUNT_IDS[*]}" | tee -a $LOG_FILE

# ARE YOU REAAAALLYYY SURE?
echo "You are about to proceed with the destruction on ${#FILTERED_ACCOUNT_IDS[@]} accounts. Are you sure? (y/N) "
read -p "Confirm: " confirm && [[ $confirm == [yY] ]] || exit 1

# Call the GH pipeline
for account_id in "${FILTERED_ACCOUNT_IDS[@]}"; do
    if [[ -n "$AWS_REGIONS" ]]; then
        if ! output=$(gh workflow run $WORKFLOW -R $REPO -r $BRANCH -f account_id="${account_id}" -f aws_regions="${AWS_REGIONS}" 2>&1); then
            echo "[$(date)]; Error triggering ${WORKFLOW} for account: $account_id. Error: $output" | tee -a $LOG_FILE
            continue
        fi
    else
        if ! output=$(gh workflow run $WORKFLOW -R $REPO -r $BRANCH -f account_id="${account_id}" 2>&1); then
            echo "[$(date)]; Error triggering ${WORKFLOW} for account: $account_id. Error: $output" | tee -a $LOG_FILE
            continue
        fi
    fi
    mark_as_processed "$account_id"
    echo "[$(date)]; Successfully triggered ${WORKFLOW}, from ${BRANCH}, on account: $account_id. Output: $output" | tee -a $LOG_FILE
done
