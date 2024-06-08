FROM node:16-buster-slim

# Install necessary tools
RUN apt-get update && \
    apt-get install -y unzip curl git ca-certificates jq && \
    rm -rf /var/lib/apt/lists/*

# Add GitHub's public key to known hosts
RUN mkdir -p  ~/.ssh && \
    ssh-keyscan -t rsa github.com >> ~/.ssh/known_hosts && \
    chown -R root:root ~/.ssh && \
    chmod 700 ~/.ssh && \
    chmod 600 ~/.ssh/known_hosts
