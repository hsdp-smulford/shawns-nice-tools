#!/usr/bin/env python3

import logging
import logging.config
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import boto3
import tomli
from rich import box
from rich.console import Console
from rich.table import Table


# Load configuration from config.toml
def load_config():
    """Loads configuration from the config.toml file."""
    with open('config.toml', 'rb') as f:
        return tomli.load(f)

def assume_role(session, role_arn, role_session_name='AWSAFT-Session'):
    """
    Assumes an IAM role and returns a new boto3 session with the role's credentials.

    Args:
        session: The current boto3 session.
        role_arn: The ARN of the role to assume.
        role_session_name: The name for the assumed role session.

    Returns:
        A new boto3 session with the assumed role's credentials.
    """
    sts_client = session.client('sts')
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName=role_session_name
    )
    credentials = response['Credentials']
    return boto3.Session(
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )

def query_active_accounts(payer_profile_name, ignored_account_ids):
    """
    Queries AWS Organizations for all active accounts, excluding ignored ones.

    Args:
        payer_profile_name: The AWS profile name for the payer account.
        ignored_account_ids: A list of account IDs to ignore.

    Returns:
        A sorted list of active account IDs.
    """
    payer_session = boto3.Session(profile_name=payer_profile_name)
    organizations_client = payer_session.client('organizations')
    paginator = organizations_client.get_paginator('list_accounts')
    all_account_ids = []
    for page in paginator.paginate():
        for account in page['Accounts']:
            if account['Status'] == 'ACTIVE' and account['Id'] not in ignored_account_ids:
                all_account_ids.append(account['Id'])
    return sorted(all_account_ids)

def get_account_name(account_id, session):
    """
    Fetches the account name from AWS Organizations.

    Args:
        account_id: The ID of the account.
        session: The boto3 session.

    Returns:
        The name of the account.
    """
    organizations_client = session.client('organizations')
    response = organizations_client.describe_account(AccountId=account_id)
    return response['Account']['Name']

def format_region_name(region):
    """
    Converts an AWS region name to a shortened format.

    Args:
        region: The AWS region name (e.g., ap-northeast-1).

    Returns:
        The shortened region name (e.g., apne1).
    """
    return region.replace("north", "n") \
                 .replace("south", "s") \
                 .replace("east", "e") \
                 .replace("west", "w") \
                 .replace("central", "c") \
                 .replace("-", "")

def count_lambdas_in_region(session, region, lambda_suffix):
    """
    Counts the number of Lambda functions with a matching suffix in a specific region.

    Args:
        session: The boto3 session.
        region: The AWS region name.
        lambda_suffix: The suffix to match against Lambda function names.

    Returns:
        A tuple containing the region name and the count of matching Lambda functions.
    """
    lambda_client = session.client('lambda', region_name=region)
    lambdas_count = 0
    paginator = lambda_client.get_paginator('list_functions')
    for page in paginator.paginate():
        for func in page['Functions']:
            if func['FunctionName'].endswith(lambda_suffix):
                lambdas_count += 1
    return region, lambdas_count

def list_lambdas(account_id, lambda_suffix, regions, session):   
    """
    Lists Lambda functions with a matching suffix in all specified regions.

    Args:
        account_id: The ID of the account.
        lambda_suffix: The suffix to match against Lambda function names.
        regions: A list of AWS region names.
        session: The boto3 session.

    Returns:
        A dictionary containing the count of matching Lambda functions in each region.
    """
    lambdas_count = {} 
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(count_lambdas_in_region, session, region, lambda_suffix) for region in regions]
        for future in as_completed(futures):
            region, count = future.result()
            lambdas_count[region] = count
            logger.debug(f"Account ID: {account_id}; Region: {region}; Matching Lambdas: {count}")

    return lambdas_count

def main():
    """
    Main function to orchestrate the Lambda discovery process.

    1. Loads configuration.
    2. Determines target account IDs.
    3. Sets up the output table.
    4. Processes each account concurrently to find matching Lambdas.
    5. Prints the results table.
    """
    logging.config.fileConfig('logging.conf')
    global logger
    logger = logging.getLogger(__name__)

    logger.info('Starting Lambda discovery')
    config = load_config()

    # Determine target account IDs
    if config['aws'].get('account_ids'):
        active_account_ids = config['aws']['account_ids']
        logger.info(f"Using specified account IDs [{len(active_account_ids)}]: {active_account_ids}")
    else:
        # If not specified, query active accounts
        active_account_ids = query_active_accounts(config['aws']['payer_profile_name'], config['aws'].get('ignored_account_ids', []))
        logger.info(f"Discovered active account IDs [{len(active_account_ids)}]: {active_account_ids}")

    # Prepare the output table
    console = Console()
    table = Table(title=f"Matching Lambda Summary, {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", show_header=True, header_style="bold magenta", box=box.ROUNDED)
    table.add_column("Account ID", justify="center", style="dim", width=12)
    table.add_column("Account Name", justify="left", style="dim") # Left justify and no truncation
    
    # Dynamically add region columns
    for region in config['aws']['regions']:
        table.add_column(format_region_name(region), justify="center", style="dim")

    # Process each account concurrently
    with ThreadPoolExecutor() as executor:
        futures = []
        for account_id in active_account_ids:
            futures.append(executor.submit(process_account, account_id, config, table))
        for future in as_completed(futures):
            future.result()  # Get the result to propagate any exceptions

    # Print the results table
    console.print(table)

def process_account(account_id, config, table):
    """
    Processes a single account to find matching Lambdas and update the table.

    Args:
        account_id: The ID of the account to process.
        config: The loaded configuration from config.toml.
        table: The Rich Table instance to update with the results.
    """
    payer_session = boto3.Session(profile_name=config['aws']['payer_profile_name'])
    try:
        account_name = get_account_name(account_id, payer_session)
        row = [account_id, f"[bold white]{account_name}[/]" ]

        # Assume roles for access
        session = boto3.Session()
        current_account_id = session.client('sts').get_caller_identity()['Account']

        # Assume AWSAFTAdmin role in the management account
        if current_account_id in config['aws'].get('management_account_ids', []):
            admin_role_arn = f"arn:aws:iam::{current_account_id}:role/{config['aws']['management_role_name']}"
            session = assume_role(session, admin_role_arn)
            logger.debug(f"Assumed AWSAFTAdmin role in management account: {current_account_id}")

        # Assume AWSAFTExecution role in the target account
        execution_role_arn = f"arn:aws:iam::{account_id}:role/{config['aws']['execution_role_name']}"
        session = assume_role(session, execution_role_arn)
        logger.debug(f"Assumed AWSAFTExecution role in target account: {account_id}")

        # Get Lambda counts for all regions
        lambdas_count_dict = list_lambdas(account_id, config['aws']['lambda_suffix'], config['aws']['regions'], session)
    except Exception as e:
        logger.error(f"Error processing account {account_id}: {e}")
        row = [account_id, "Error", *["N/A" for _ in config['aws']['regions']]]  
        table.add_row(*row, style="red")  # Add the error row and return
        return

    # Add counts to the row, format based on count value
    for region in config['aws']['regions']:
        count = lambdas_count_dict.get(region, 0)
        row.append(f"[bold blue]{count}[/]" if count > 0 else "[dim grey]-[/]") # Highlight > 0, use "-" for 0

    table.add_row(*row) 

if __name__ == '__main__':
    main()