---
title: Quick Start
description: Get Bifrost running in 5 minutes with Docker
---

Get Bifrost up and running with Docker in just 5 minutes. This guide walks you through installation, creating your first workflow, and building a simple form.

## Prerequisites

- Docker Desktop (24+)
- Git
- 5 minutes of your time

## Step 1: Clone the Repository

```bash
git clone https://github.com/jackmusick/bifrost-api.git
cd bifrost-api
```

## Step 2: Start the Local Environment

The easiest way to get started is using Docker Compose:

```bash
# Start Bifrost (Azurite + Workflow Engine)
docker compose up
```

Wait for the output to show:
```
✓ Azurite is running on http://localhost:10002
✓ Functions runtime is ready
```

## Step 3: Verify Everything is Running

Test the health endpoint:

```bash
curl http://localhost:7071/api/health
```

You should get:
```json
{"status": "healthy"}
```

## Step 4: Create Your First Workflow

Create a file `workspace/hello_world.py`:

```python
from bifrost import workflow, param

@workflow(
    name="hello_world",
    description="Say hello to someone",
    category="examples"
)
@param("name", "string", label="Your name", required=True)
@param("greeting", "string", label="Greeting", default_value="Hello")
async def hello_world(context, name: str, greeting: str = "Hello"):
    """A simple workflow that greets someone."""
    return {
        "message": f"{greeting}, {name}!",
        "executed_by": context.user_id
    }
```

## Step 5: Test Your Workflow

Execute the workflow via curl:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "x-functions-key: test" \
  -H "X-Organization-Id: test-org-active" \
  -d '{"name": "Alice", "greeting": "Welcome"}' \
  http://localhost:7071/api/workflows/hello_world
```

Response:
```json
{
  "message": "Welcome, Alice!",
  "executed_by": "test-user"
}
```

## Step 6: View All Workflows

List all discovered workflows:

```bash
curl -H "x-functions-key: test" \
     -H "X-Organization-Id: test-org-active" \
     http://localhost:7071/api/discovery
```

You'll see your workflow registered with all its metadata:

```json
{
  "workflows": [
    {
      "name": "hello_world",
      "description": "Say hello to someone",
      "category": "examples",
      "parameters": [
        {
          "name": "name",
          "type": "string",
          "label": "Your name",
          "required": true
        },
        {
          "name": "greeting",
          "type": "string",
          "label": "Greeting",
          "default_value": "Hello"
        }
      ]
    }
  ]
}
```

## Next Steps

- **Build Your First Form**: [Creating Forms Tutorial](/tutorials/creating-forms/) - Learn how to create dynamic forms powered by your workflows
- **OAuth Integration**: [OAuth Setup](/tutorials/oauth-integration/) - Connect to Microsoft Graph, HaloPSA, or other services
- **Workflow Development**: [Complete Workflow Guide](/guides/workflows/writing-workflows/) - Master advanced workflow patterns
- **Deployment**: [Azure Setup](/guides/deployment/azure-setup/) - Deploy to production on Azure

## Common Issues

**Port 7071 already in use?**
```bash
# Find and kill the process
lsof -i :7071
kill -9 <PID>
```

**Docker not starting?**
```bash
# Rebuild the image
docker compose build --no-cache
docker compose up
```

**Workflow not found?**
- Make sure the file is in the `workspace/` directory
- Restart Docker for decorator changes to take effect
- Check the logs: `docker compose logs functions`

## Full Example Repository

The bifrost-api repository includes example workflows in the `platform/` directory. Check those out for more inspiration!

```bash
# View example workflows
ls platform/examples/
```

That's it! You now have a working Bifrost environment. Ready to dive deeper? Check out the [Building Your First Workflow](/tutorials/first-workflow/) tutorial.
