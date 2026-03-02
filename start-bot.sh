#!/bin/bash
# Start Gork Telegram Bot (Node.js)

# Load environment variables
if [ -f .env ]; then
  export $(cat .env | grep -v '^#' | xargs)
fi

echo "Starting Gork Telegram Bot..."
node standalone-bot.mjs
