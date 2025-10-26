---
title: Deploy to Azure
description: Complete guide for deploying Bifrost to Azure infrastructure using ARM templates and Azure CLI
---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Infrastructure Overview](#infrastructure-overview)
- [Deployment Steps](#deployment-steps)
- [Post-Deployment Configuration](#post-deployment-configuration)

## Prerequisites

Before deploying to Azure, you need an active Azure Subscription.

### Required Permissions

Your Azure account needs these permissions:

- Create resource groups
- Create storage accounts
- Create function apps
- Create key vaults
- Create application insights
- Create static web apps

## Infrastructure Overview

The ARM template creates the following Azure resources:

- **Azure Functions (Flex Consumption Plan)** - Serverless backend runtime
- **Storage Account (Standard_LRS)** - Tables and file storage
- **Azure Key Vault** - Secure secrets management
- **Application Insights** - Performance monitoring and diagnostics
- **Static Web App** - React frontend hosting

## Deployment Steps

### Entra App Registration

1. Login to [Entra](https://entra.microsoft.com).
1. Navigate to App Registrations.
1. Click **New Registration**.

   - For the name, put whatever you want like `Bifrost Integrations` or `MyMSP Automation`.
   - For the account types, select Multitenant unless you do _NOT_ have customers or partners that need to login and run forms.
   - For the Redirect URI, select **Web** as the platform and type in the URL you intend to use for the application. This can be changed later. Example:

     `https://bifrost.mydomain.com/.auth/login/aad/callback`

   ![alt text](../../../../assets/azure-setup/image-1.png)

1. Under **Overview**, copy your Application ID. You'll need this later.
1. Under **Certificates & Secrets**, create a new client secret and copy this somewhere. You'll need this later.
1. Under **Authentication**, enable ID tokens.

   ![alt text](../../../../assets/azure-setup/image-2.png)

1. Under API Permissions, grant admin consent.

   ![alt text](../../../../assets/azure-setup/image-3.png)

### Send it!

Fork the [API](https://github.com/jackmusick/bifrost-api) and [Client](https://github.com/jackmusick/bifrost-client) repository.

![alt text](../../../../assets/azure-setup/image.png)

Use the below Deploy to Azure button to automatically setup all of your resources. Azure will ask you for the Entra ID Client ID and Secret you created above.

> Set a reminder to update renew your Client Secret and update it on the Static Web App's configuration page.

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fjackmusick%2Fbifrost-api%2Frefs%2Fheads%2Fmain%2Fdeployment%2Fazuredeploy.json)


## Next Steps

Setup [GitHub Actions](./github-actions.md) for automated deployment setup.
