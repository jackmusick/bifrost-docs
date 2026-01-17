#!/bin/bash

# Bifrost Docs - Environment Setup Script
# Generates secure secrets and configures the environment

set -e

echo "🚀 Bifrost Docs Setup"
echo "===================="
echo ""

# Check if .env already exists
if [ -f .env ]; then
    echo "⚠️  .env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Copy example env file
cp .env.example .env
echo "✓ Created .env from .env.example"

# Generate secure random values
generate_secret() {
    openssl rand -base64 32 | tr -d '/+=' | head -c 32
}

generate_password() {
    openssl rand -base64 24 | tr -d '/+='
}

# Generate secrets
BIFROST_DOCS_SECRET_KEY=$(generate_secret)
POSTGRES_PASSWORD=$(generate_password)
MINIO_ROOT_PASSWORD=$(generate_password)

# Update .env with generated values
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed requires different syntax
    sed -i '' "s|^BIFROST_DOCS_SECRET_KEY=.*|BIFROST_DOCS_SECRET_KEY=${BIFROST_DOCS_SECRET_KEY}|" .env
    sed -i '' "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" .env
    sed -i '' "s|^MINIO_ROOT_PASSWORD=.*|MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}|" .env
else
    sed -i "s|^BIFROST_DOCS_SECRET_KEY=.*|BIFROST_DOCS_SECRET_KEY=${BIFROST_DOCS_SECRET_KEY}|" .env
    sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" .env
    sed -i "s|^MINIO_ROOT_PASSWORD=.*|MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}|" .env
fi

echo "✓ Generated secure secrets"

# Domain configuration for WebAuthn
echo ""
echo "WebAuthn Configuration"
echo "----------------------"
echo "WebAuthn requires knowing the domain where the app will be accessed."
echo ""
echo "Common options:"
echo "  1. localhost (default - for local development)"
echo "  2. Custom domain (e.g., docs.example.com)"
echo ""
read -p "Enter domain [localhost]: " DOMAIN
DOMAIN=${DOMAIN:-localhost}

# Determine origin based on domain
if [ "$DOMAIN" = "localhost" ]; then
    ORIGIN="http://localhost:3000"
else
    read -p "Use HTTPS? (Y/n): " use_https
    if [[ "$use_https" =~ ^[Nn]$ ]]; then
        ORIGIN="http://${DOMAIN}"
    else
        ORIGIN="https://${DOMAIN}"
    fi
fi

# Update WebAuthn configuration
if [[ "$OSTYPE" == "darwin"* ]]; then
    sed -i '' "s|^BIFROST_DOCS_WEBAUTHN_RP_ID=.*|BIFROST_DOCS_WEBAUTHN_RP_ID=${DOMAIN}|" .env
    sed -i '' "s|^BIFROST_DOCS_WEBAUTHN_ORIGIN=.*|BIFROST_DOCS_WEBAUTHN_ORIGIN=${ORIGIN}|" .env
    sed -i '' "s|^BIFROST_DOCS_CORS_ORIGINS=.*|BIFROST_DOCS_CORS_ORIGINS=${ORIGIN}|" .env
else
    sed -i "s|^BIFROST_DOCS_WEBAUTHN_RP_ID=.*|BIFROST_DOCS_WEBAUTHN_RP_ID=${DOMAIN}|" .env
    sed -i "s|^BIFROST_DOCS_WEBAUTHN_ORIGIN=.*|BIFROST_DOCS_WEBAUTHN_ORIGIN=${ORIGIN}|" .env
    sed -i "s|^BIFROST_DOCS_CORS_ORIGINS=.*|BIFROST_DOCS_CORS_ORIGINS=${ORIGIN}|" .env
fi

echo "✓ Configured WebAuthn for ${DOMAIN}"

# Optional: OpenAI API key for vector search
echo ""
echo "Vector Search Configuration (Optional)"
echo "---------------------------------------"
echo "Vector search requires an OpenAI API key for embeddings."
echo "You can skip this and add it later to .env"
echo ""
read -p "Enter OpenAI API key (or press Enter to skip): " OPENAI_KEY

if [ -n "$OPENAI_KEY" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^BIFROST_DOCS_OPENAI_API_KEY=.*|BIFROST_DOCS_OPENAI_API_KEY=${OPENAI_KEY}|" .env
    else
        sed -i "s|^BIFROST_DOCS_OPENAI_API_KEY=.*|BIFROST_DOCS_OPENAI_API_KEY=${OPENAI_KEY}|" .env
    fi
    echo "✓ Configured OpenAI API key"
else
    echo "⏭  Skipped OpenAI configuration (vector search will be disabled)"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Generated credentials (saved in .env):"
echo "  POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}"
echo "  MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}"
echo ""
echo "Next steps:"
echo "  1. Review .env and adjust any settings"
echo "  2. Run ./debug.sh to start the development environment"
echo "  3. Access the app at ${ORIGIN}"
echo ""
