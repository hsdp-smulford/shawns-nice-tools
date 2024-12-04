#!/usr/bin/env python3

import boto3
from dataclasses import dataclass, field
import logging
import logging.config
import tomli
from datetime import datetime

def load_config():
    with open('config.toml', 'rb') as f:
        return tomli.load(f)

def assume_role(session, role_arn, role_session_name='AWSAFT-Session'):
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
    payer_session = boto3.Session(profile_name=payer_profile_name)
    organizations_client = payer_session.client('organizations')
    paginator = organizations_client.get_paginator('list_accounts')
    all_account_ids = []
    for page in paginator.paginate():
        for account in page['Accounts']:
            if account['Status'] == 'ACTIVE' and account['Id'] not in ignored_account_ids:
                all_account_ids.append(account['Id'])
    return sorted(all_account_ids)

@dataclass
class Base:
    lambda_suffix: str
    regions: list
    role_name: str
    management_account_ids: list
    payer_profile_name: str
    session: boto3.Session = None
    account_ids: list = field(default_factory=list)
    ignored_account_ids: list = field(default_factory=list)

    def __post_init__(self):
        # Directly use payer profile for session
        session = boto3.Session()
        payer_session = boto3.Session(profile_name=self.payer_profile_name)
        current_account = session.client('sts').get_caller_identity()['Account']
        logger.info(f"Current account: {current_account}")

        if current_account in self.management_account_ids:
            management_role_arn = f"arn:aws:iam::{current_account}:role/{self.role_name}"
            logger.info(f"Assuming role {self.role_name} in management account {current_account}")
            self.session = assume_role(session, management_role_arn)
        else:
            logger.warning(f"Current account {current_account} is not in the list of management accounts. Proceeding without assuming role.")
            self.session = session

@dataclass
class AwsAccount:
    account_id: str
    lambda_suffix: str
    regions: list
    role_name: str
    management_account_ids: list
    payer_profile_name: str
    session: boto3.Session

    def __str__(self):
        return f'AwsAccount(account_id={self.account_id})'

    def list_lambdas(self):
        # Assume `AWSAFTExecution` role in the target account (for role chaining)
        role_name = "AWSAFTExecution"
        role_arn = f"arn:aws:iam::{self.account_id}:role/{role_name}"
        logger.info(f"Assuming {role_name} role in account {self.account_id}")
        target_session = assume_role(self.session, role_arn)

        lambdas = []
        for region in self.regions:
            logger.info(f"Checking region {region} in account {self.account_id}")
            lambda_client = target_session.client('lambda', region_name=region)
            paginator = lambda_client.get_paginator('list_functions')
            for page in paginator.paginate():
                for func in page['Functions']:
                    if func['FunctionName'].endswith(self.lambda_suffix):
                        lambdas.append(func['FunctionName'])
        return lambdas


def main():
    logging.config.fileConfig('logging.conf')
    global logger
    logger = logging.getLogger(__name__)

    logger.info('Starting find-lambdas.py')

    config = load_config()

    # Query active accounts once
    active_account_ids = query_active_accounts(config['aws']['payer_profile_name'], config['aws'].get('ignored_account_ids', []))
    logger.info(f"Discovered active account IDs [{len(active_account_ids)}]: {active_account_ids}")

    # Initialize the base class, which will handle account querying if necessary
    base = Base(
        lambda_suffix=config['aws']['lambda_suffix'],
        regions=config['aws']['regions'],
        role_name=config['aws']['role_name'],
        management_account_ids=config['aws']['management_account_ids'],
        payer_profile_name=config['aws']['payer_profile_name'],
        account_ids=active_account_ids,
        ignored_account_ids=config['aws'].get('ignored_account_ids', [])
    )

    # Create AWS account objects
    aws_accounts = [
        AwsAccount(
            account_id=account_id,
            lambda_suffix=base.lambda_suffix,
            regions=base.regions,
            role_name=base.role_name,
            management_account_ids=base.management_account_ids,
            payer_profile_name=base.payer_profile_name,
            session=base.session
        )
        for account_id in base.account_ids if account_id not in base.ignored_account_ids
    ]

    # print it.
    for account in aws_accounts:
        lambdas = account.list_lambdas()
        for lambda_name in lambdas:
            logger.info(f"Found Lambda in {account.account_id}: {lambda_name}")


if __name__ == '__main__':
    main()