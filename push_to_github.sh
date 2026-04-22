#!/bin/bash

# Healthcare Fraud Detection - GitHub Push Script
# Replace YOUR_USERNAME with your actual GitHub username

echo "Healthcare Fraud Detection - GitHub Push Script"
echo "=============================================="
echo ""

# Get GitHub username from user
read -p "Enter your GitHub username: " GITHUB_USERNAME

if [ -z "$GITHUB_USERNAME" ]; then
    echo "Error: GitHub username is required"
    exit 1
fi

# Repository name
REPO_NAME="healthcare-fraud-detection"

# Remote URL
REMOTE_URL="https://github.com/${GITHUB_USERNAME}/${REPO_NAME}.git"

echo "Setting up remote: ${REMOTE_URL}"
echo ""

# Check if remote already exists
if git remote get-url origin &>/dev/null; then
    echo "Remote 'origin' already exists. Updating..."
    git remote set-url origin "${REMOTE_URL}"
else
    echo "Adding remote 'origin'..."
    git remote add origin "${REMOTE_URL}"
fi

echo ""
echo "Remote configured successfully!"
echo ""
echo "Verifying remote:"
git remote -v
echo ""
echo "=============================================="
echo "Ready to push to GitHub!"
echo ""
echo "To push your code, run:"
echo "  git push -u origin main"
echo ""
echo "Or if you want to see what will be pushed first:"
echo "  git status"
echo "  git log --oneline"
echo ""
echo "Repository URL: ${REMOTE_URL}"
echo "=============================================="
