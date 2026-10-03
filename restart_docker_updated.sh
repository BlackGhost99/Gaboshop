#!/bin/bash
# Restart Docker containers with latest fixes

echo "🔄 Stopping Docker containers..."
docker-compose down

echo "🧹 Cleaning up old images (optional)..."
# docker image prune -f

echo "🏗️ Building Docker images..."
docker-compose build --no-cache

echo "🚀 Starting services..."
docker-compose up -d

echo "⏳ Waiting for services to be ready..."
sleep 5

echo "✅ Done! Services are running:"
echo "   - Web API: http://localhost:8000"
echo "   - Frontend: http://localhost:5173"
echo "   - Redis: localhost:6379"
echo ""
echo "📝 Logs: docker-compose logs -f web"
