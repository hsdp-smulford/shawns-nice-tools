#!/usr/bin/env python3

from hap.aws import AWS
from botocore.exceptions import ClientError

def main():
    """
    Main function to check and delete AWS Config rules that are not exempt and not in the process of being deleted.
    For each region, it retrieves the Config rules, filters them based on the state and exempt prefixes,
    and deletes the rules along with any associated RemediationConfiguration.
    """
    # Initialize the AWS class for the 'config' service
    aws = AWS(service="config")
    
    # Iterate over all regions
    for region in aws.regions:
        aws.logger.info(f"Checking Config rules in {region}")
        matched_rules = []
        
        # Create a client for the 'config' service in the current region
        client = aws.get_client(service="config", region=region)
        
        # Create a paginator to handle large sets of Config rules
        paginator = client.get_paginator("describe_config_rules")

        try:
            # Paginate through all Config rules in the current region
            for page in paginator.paginate():
                matched_rules.extend([
                    rule['ConfigRuleName'] 
                    for rule in page['ConfigRules'] 
                    # Filter out rules that are in the process of being deleted and exempt rules
                    if rule['ConfigRuleState'] != "DELETING" and not any(rule['ConfigRuleName'].startswith(prefix) for prefix in aws.config['exempt_rule_prefixes'])
                ])     
        except Exception as e:
            print(f"Error in region {region}: {e}")
        
        aws.logger.info(f"Matched rules in {region}: [{len(matched_rules)}]")
        aws.logger.debug(f"Matched rules in {region}: {matched_rules}")

        if matched_rules:
            for rule in matched_rules:
                aws.logger.info(f"{region}: Deleting Config rule: {rule}")
                try:
                    # Attempt to delete any associated RemediationConfiguration first
                    client.delete_remediation_configuration(ConfigRuleName=rule)
                    aws.logger.info(f"{region}: Deleted RemediationConfiguration for rule: {rule}")
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchRemediationConfigurationException':
                        aws.logger.info(f"{region}: No RemediationConfiguration found for rule: {rule}")
                    else:
                        aws.logger.error(f"{region}: Error deleting RemediationConfiguration for rule: {rule}: {e}")
                        continue

                try:
                    # Delete the Config rule
                    client.delete_config_rule(ConfigRuleName=rule)
                    aws.logger.info(f"{region}: Deleted Config rule: {rule}")
                except ClientError as e:
                    aws.logger.error(f"{region}: Error deleting Config rule: {rule}: {e}")

if __name__ == "__main__":
    main()