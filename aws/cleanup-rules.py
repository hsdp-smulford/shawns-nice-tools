#!/usr/bin/env python3

from hap.aws import AWS


def main():

    DRY_RUN = True
    
    aws = AWS(service="config")

    for region in aws.regions:
        aws.logger.info(f"Checking Config rules in {region}")
        matched_rules = []
        client = aws.get_client(service="config", region=region)
        paginator = client.get_paginator("describe_config_rules")  # Create paginator

        try:
            for page in paginator.paginate():
                matched_rules.extend([
                    rule['ConfigRuleName'] 
                    for rule in page['ConfigRules'] 
                    if not any(rule['ConfigRuleName'].startswith(prefix) for prefix in aws.config['exempt_rule_prefixes'])
                ])        
        except Exception as e:
            print(f"Error in region {region}: {e}")
        aws.logger.info(f"Matched rules in {region}: [{len(matched_rules)}]")
        aws.logger.debug(f"Matched rules in {region}: {matched_rules}")

        if matched_rules:
            for rule in matched_rules:
                aws.logger.info(f"{region}: Deleting Config rule {rule}")
                # client.delete_config_rule(ConfigRuleName=rule, DryRun=DRY_RUN)
                aws.logger.info(f"Deleted Config rule: {rule}")

if __name__ == "__main__":
    main()
