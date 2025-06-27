#!/bin/bash

# GitHub Secrets Update Script
# Updates Claude AI OAuth credentials from ~/.claude/.credentials.json to GitHub repository secrets

set -e

CREDENTIALS_FILE="$HOME/.claude/.credentials.json"

# Check if credentials file exists
if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo "Error: Credentials file not found at $CREDENTIALS_FILE"
    exit 1
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed. Please install jq first."
    exit 1
fi

# Check if gh is available
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is required but not installed. Please install gh first."
    exit 1
fi

echo "Reading Claude credentials from $CREDENTIALS_FILE..."

# Extract values from credentials.json
ACCESS_TOKEN=$(jq -r '.claudeAiOauth.accessToken' "$CREDENTIALS_FILE")
REFRESH_TOKEN=$(jq -r '.claudeAiOauth.refreshToken' "$CREDENTIALS_FILE")
EXPIRES_AT=$(jq -r '.claudeAiOauth.expiresAt' "$CREDENTIALS_FILE")

# Validate extracted values
if [ "$ACCESS_TOKEN" = "null" ] || [ "$REFRESH_TOKEN" = "null" ] || [ "$EXPIRES_AT" = "null" ]; then
    echo "Error: Failed to extract valid credentials from $CREDENTIALS_FILE"
    exit 1
fi

echo "Updating GitHub repository secrets..."

# Update GitHub secrets
gh secret set CLAUDE_ACCESS_TOKEN --body "$ACCESS_TOKEN"
echo "✓ Updated CLAUDE_ACCESS_TOKEN"

gh secret set CLAUDE_REFRESH_TOKEN --body "$REFRESH_TOKEN"
echo "✓ Updated CLAUDE_REFRESH_TOKEN"

gh secret set CLAUDE_EXPIRES_AT --body "$EXPIRES_AT"
echo "✓ Updated CLAUDE_EXPIRES_AT"

echo ""
echo "All secrets updated successfully!"
echo ""
echo "Current secrets:"
gh secret list