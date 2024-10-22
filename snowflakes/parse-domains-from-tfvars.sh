#!/usr/bin/env python3 

import hcl2
import json

# GLOBALS
INPUT_FILENAME = './domains.tfvars'
OUTPUT_FILENAME = './domains.json'

def parse_tfvars_file(filename):
    with open(filename, 'r') as file:
        obj = hcl2.load(file)
        return obj.get('custom_domains', {})  # Using 'custom_domains'

def format_output(data):
    formatted_data = {}
    
    for domain_name, details in data.items():
        base_domain = domain_name.split(".")[0]
        account_id = details.get('account_id')
        
        if account_id:
            if account_id not in formatted_data:
                formatted_data[account_id] = []
            formatted_data[account_id].append(base_domain)

    # Sort both account IDs and their respective domains
    sorted_data = {account_id: sorted(domains) for account_id, domains in sorted(formatted_data.items())}
    
    return sorted_data

def main():
    data = parse_tfvars_file(INPUT_FILENAME)
    formatted_data = format_output(data)

    # Write the formatted output to domains.json
    with open(OUTPUT_FILENAME, 'w') as outfile:
        json.dump(formatted_data, outfile, indent=4)

    # Print the output to the console as well
    print(json.dumps(formatted_data, indent=4))

    # Summary
    total_account_ids = len(formatted_data)
    total_domains = sum(len(domains) for domains in formatted_data.values())

    print(f"\nTotal Account IDs: {total_account_ids}")
    print(f"Total Domains: {total_domains}")

if __name__ == "__main__":
    main()
