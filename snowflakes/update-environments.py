#!/usr/bin/env python3

import json
import os
import requests
import getpass

input_file = 'domains.json'
output_file = 'out.txt'
repo_name = 'philips-internal/hsp-aws-platform'
environment_suffix = 'custom-domains'
variable_name = 'DOMAINS_SUBDOMAINS'

# Initialize headers
def get_headers() -> dict:
    token = os.getenv('GITHUB_TOKEN', None)
    if not token:  
        token = getpass.getpass("Enter your GitHub token: ")
    if not token:
        raise Exception("GITHUB_TOKEN environment variable not set")
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

def load_accounts_with_domains(filename = input_file) -> dict:
    with open(filename, 'r') as file:
        return json.load(file)

def get_environments(headers: dict) -> list:
    environments = []
    url = f"https://api.github.com/repos/{repo_name}/environments"
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        environments.extend([env['name'] for env in data['environments']])
        url = response.links.get('next', {}).get('url')
    return environments

def create_environment(headers: dict, environment: str) -> bool:
    url = f"https://api.github.com/repos/{repo_name}/environments/{environment}"
    response = requests.put(url, headers=headers, json={})
    response.raise_for_status()
    return response.ok

def get_variables(headers: dict, environment: str) -> list:
    variables = []
    url = f"https://api.github.com/repos/{repo_name}/environments/{environment}/variables"
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        variables.extend([env['name'] for env in data['variables']])
        url = response.links.get('next', {}).get('url')
    return sorted(variables)

def get_values(headers: dict, environment: str, variable_name: str) -> list:
        url = f"https://api.github.com/repos/{repo_name}/environments/{environment}/variables/{variable_name}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return json.loads(data['value'])


def main():
    headers = get_headers()
    accounts_with_domains = load_accounts_with_domains()
    environments = get_environments(headers)

    for account_id, domains in accounts_with_domains.items():
        environment = f"{account_id}-{environment_suffix}"

        # set up environment
        environment_exist = environment in environments
        if environment_exist:
            print("Environment already exists: {}".format(environment))
        else:
            status = create_environment(headers, environment)
            print(f"Environment created: {environment}; Status: {status}")

        # set up variable
        variables = get_variables(headers, environment)
        existing_values = []
        variable_exists = variable_name in variables
        if variable_exists:
            print(f"Variable already exists: {variable_name}")
            existing_values = get_values(headers, environment, variable_name)
            values = sorted(list(set(existing_values) | set(domains)))
            print(f"Existing values: {existing_values}")
        else:
            print(f"Variable does not exist: {variable_name}")
            values = sorted(list(set(domains)))
        print(f"Setting variable; Environment: {environment}; variable: {variable_name}; values: {values}")
        

        # Set up values
        new_values = list(set(values) - set(existing_values))
        print(f"Setting variable; Environment: {environment}; variable: {variable_name}; values: {values}")

        if new_values:
          print(f"Found values to update: {new_values}")
          if variable_exists:
            url = f"https://api.github.com/repos/{repo_name}/environments/{environment}/variables/{variable_name}"
            response = requests.patch(url, headers=headers, json={"name": variable_name, "value": json.dumps(values)})
            response.raise_for_status()
            print(f"Variable updated: {response.ok}")
          else:
            url = f"https://api.github.com/repos/{repo_name}/environments/{environment}/variables"
            response = requests.post(url, headers=headers, json={"name": variable_name, "value": json.dumps(values)})
            response.raise_for_status()
            print(f"Variable created: {response.ok}")
        else:
          print(f"No new values to update")

if __name__ == "__main__":
    main()