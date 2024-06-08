# aft-hsp-core-infra

## Purpose

This repo is to manage persistent, stateful IaC for HSP CloudOps Team

## Testing Workflows

You can test workflows locally prior to checking in your code by using [act-cli](https://nektosact.com/introduction.html). While not in the official doumentaion, on macos you can install act using brew:

```shell
brew install act
```

Once installed, build a local image adding any dependencies as required to the [Dockerfile](./Dockerfile):

```shell
docker build -t act:dev .
```

You can then test all the workflows using you local environment:

```shell
act -P ubuntu-latest=act:dev --pull=false
```

You can also specify an event and a specific workflow:

```shell
act pull_request -P ubuntu-latest=act:dev --pull=false -W .github/workflows/terraform-validate.yml
```

Specify which tests to run:

```shell
act pull_request -P ubuntu-latest=act:dev --pull=false -W .github/workflows/test-workflows.yaml -j test-helm-module-scanning -j test-tf-module-docs