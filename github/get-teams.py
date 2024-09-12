#!/usr/bin/env python3

import os
from getpass import getpass
import requests
import yaml

# Replace with your personal access token and organization name
PAT = os.environ.get('PAT', None)
if PAT is None:
    PAT = getpass('Enter your GitHub personal access token: ')

# TODO: Add variable for organization name if this is ever used again.
GH_ORG = os.environ.get('GH_ORG', 'philips-internal')

# GitHub API endpoint to list all teams in the organization
teams_url = f'https://api.github.com/orgs/{GH_ORG}/teams'

# Headers for the API request
headers = {
    'Authorization': f'token {PAT}',
    'Accept': 'application/vnd.github.v3+json'
}

# Function to get the list of teams
def get_teams():
    teams = []
    url = teams_url
    
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        teams.extend(response.json())
        url = response.links.get('next', {}).get('url')
    
    return [{'name': team['name'], 'slug': team['slug']} for team in teams]

# Function to get the repositories and roles for a team
def get_team_repos(team_slug):
    url = f'https://api.github.com/orgs/{GH_ORG}/teams/{team_slug}/repos'
    repos = []
    
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        repos.extend(response.json())
        url = response.links.get('next', {}).get('url')
    
    return repos

# Function to get the maintainers for a team
def get_team_maintainers(team_slug):
    url = f'https://api.github.com/orgs/{GH_ORG}/teams/{team_slug}/members?role=maintainer'
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# Function to get all members of a team
def get_team_members(team_slug):
    url = f'https://api.github.com/orgs/{GH_ORG}/teams/{team_slug}/members'
    members = []
    
    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        members.extend(response.json())
        url = response.links.get('next', {}).get('url')
    
    return members

# Main function to gather data and format it in YAML
def main():
    teams = get_teams()
    data = {}

    for team in teams:
        # TODO: Add variables for names if this is ever used again.
        if team['name'].startswith('fiesta-aft') or 'fiesta-foundation' in team['name']:
            repos = get_team_repos(team['slug'])
            maintainers = get_team_maintainers(team['slug'])
            members = get_team_members(team['slug'])

            data[team['name']] = {
                'write': [repo['full_name'] for repo in repos if repo['permissions']['push']],
                'read': [repo['full_name'] for repo in repos if repo['permissions']['pull']],
                'admin': [repo['full_name'] for repo in repos if repo['permissions']['admin']],
                'maintainers': [maintainer['login'] for maintainer in maintainers],
                'members': [member['login'] for member in members],
                'repos': [repo['full_name'] for repo in repos]
            }

    # Convert the data to YAML format
    yaml_data = yaml.dump(data, default_flow_style=False)
    print(yaml_data)

if __name__ == '__main__':
    main()