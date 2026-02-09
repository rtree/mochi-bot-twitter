#!/bin/bash
# Deploy script for mochi-bot-twitter
# Usage: ./deploy.sh

set -e

REMOTE_HOST="ubuntu@cheque.arkt.me"
REMOTE_PORT="22345"
REMOTE_PATH="operations/mochi-bot-twitter"

echo "🚀 Deploying mochi-bot-twitter to production..."

# Execute git pull on remote server
ssh -p ${REMOTE_PORT} ${REMOTE_HOST} "cd ${REMOTE_PATH} && git pull -v"

echo "✅ Deployment completed!"
