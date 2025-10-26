---
title: Set Up GitHub Actions CI/CD
description: Automate the deployment of Bifrost using GitHub Actions workflows
---

# Set Up GitHub Actions CI/CD

This guide covers using GitHub Actions to deploy your Azure Function repo automatically.

## Table of Contents

- [Requirements](#setup-requirements)
- [Guide](#guide)

## Requirements

Before using GitHub Actions, you should have already forked both the [API](https://github.com/jackmusick/bifrost-api) and [Client](https://github.com/jackmusick/bifrost-client) repos.

## Guide

GitHub Actions needs secrets to deploy to Azure. Configure them:

In Azure, you'll want to download (Get Publishing Profile) from your Azure Functions app and copy the contents of that file to your clipboard. Then in GitHub:

1. Go to your Bifrost API repo -> Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add these secrets:

| Name                                | Value               | Description                        |
| ----------------------------------- | ------------------- | ---------------------------------- |
| `AZURE_FUNCTIONAPP_NAME`            | `bifrost-api-xxxxx` | Your Function App name             |
| `AZURE_FUNCTIONAPP_PUBLISH_PROFILE` | XML from step 1     | Publish profile for authentication |

This should immediately begin deploying your Azure Function app. You can view this under Actions.
