#!/bin/bash

# Clash Royale Analytics Setup Validation Script
# This script helps validate that your system is properly configured

echo "🔍 Clash Royale Analytics - Setup Validation"
echo "============================================="
echo

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "   Please copy .env.example to .env and configure it with your API keys"
    exit 1
fi

echo "✅ .env file found"

# Check if docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running!"
    echo "   Please start Docker and try again"
    exit 1
fi

echo "✅ Docker is running"

# Check if docker-compose is available
if ! command -v docker-compose > /dev/null 2>&1 && ! docker compose version > /dev/null 2>&1; then
    echo "❌ Docker Compose not found!"
    echo "   Please install Docker Compose and try again"
    exit 1
fi

echo "✅ Docker Compose is available"

# Check if services are running
echo
echo "🚀 Checking services status..."

if docker compose ps | grep -q "Up"; then
    echo "✅ Some services are running"
    
    # Check specific services
    if docker compose ps | grep -q "api.*Up"; then
        echo "✅ API service is running"
        
        # Test API health
        if curl -s http://localhost:8000/ping > /dev/null 2>&1; then
            echo "✅ API is responding at http://localhost:8000"
        else
            echo "⚠️  API service is running but not responding"
            echo "   Check logs with: docker compose logs api"
        fi
    else
        echo "❌ API service is not running"
    fi
    
    if docker compose ps | grep -q "data_scraper.*Up"; then
        echo "✅ Data scraper service is running"
    else
        echo "❌ Data scraper service is not running"
    fi
    
    if docker compose ps | grep -q "mongo.*Up"; then
        echo "✅ MongoDB service is running"
    else
        echo "❌ MongoDB service is not running"
    fi
    
else
    echo "❌ No services are running"
    echo "   Start services with: docker compose up -d"
    exit 1
fi

# Check for tracked players
echo
echo "👥 Checking tracked players..."
TRACKED_RESPONSE=$(curl -s http://localhost:8000/tracked-players 2>/dev/null)
if [ $? -eq 0 ]; then
    PLAYER_COUNT=$(echo "$TRACKED_RESPONSE" | grep -o '"count":[0-9]*' | cut -d: -f2)
    if [ "$PLAYER_COUNT" -gt 0 ] 2>/dev/null; then
        echo "✅ $PLAYER_COUNT player(s) currently being tracked"
        echo "   Players: $(echo "$TRACKED_RESPONSE" | grep -o '"tracked_players":\[[^]]*\]' | sed 's/"tracked_players":\[//; s/\]//; s/"//g')"
    else
        echo "⚠️  No players currently being tracked"
        echo "   Add players with: curl -X POST \"http://localhost:8000/tracked-players/%23PLAYERTAG\""
    fi
else
    echo "❌ Could not check tracked players (API not responding)"
fi

echo
echo "📊 System Status Summary:"
echo "========================"

# Overall status
if docker compose ps | grep -q "api.*Up" && curl -s http://localhost:8000/ping > /dev/null 2>&1; then
    echo "🟢 System is running and ready for use!"
    echo
    echo "Next steps:"
    echo "1. Add players to track: curl -X POST \"http://localhost:8000/tracked-players/%23PLAYERTAG\""
    echo "2. Check API documentation: See API_DOCUMENTATION.md"
    echo "3. Follow the tutorial: See TUTORIAL.md"
    echo
    echo "Useful commands:"
    echo "- View logs: docker compose logs"
    echo "- View API logs: docker compose logs api"
    echo "- View scraper logs: docker compose logs data_scraper"
    echo "- Restart services: docker compose restart"
else
    echo "🔴 System has issues that need to be resolved"
    echo
    echo "Troubleshooting:"
    echo "- Check all services: docker compose ps"
    echo "- View logs: docker compose logs"
    echo "- Restart services: docker compose restart"
    echo "- Rebuild services: docker compose up --build -d"
fi

echo