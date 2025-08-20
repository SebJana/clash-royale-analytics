# Complete Setup and Usage Tutorial

This tutorial will guide you through setting up and using the Clash Royale Analytics system from start to finish.

## Prerequisites

- Docker and Docker Compose installed on your system
- Clash Royale API key(s) from https://developer.clashroyale.com
- Basic knowledge of command line operations

## Step 1: Get Clash Royale API Keys

1. Visit https://developer.clashroyale.com
2. Create an account or log in
3. Create a new API key with your public IP address
4. Copy your API key (starts with "ey...")

**Note**: You can create two keys if you want to separate data scraping from on-demand queries, or use the same key for both.

## Step 2: Clone and Setup

```bash
# Clone the repository
git clone https://github.com/SebJana/clash-royale-analytics.git
cd clash-royale-analytics

# Create environment configuration
cp .env.example .env  # If example exists, or create manually
```

## Step 3: Configure Environment

Create a `.env` file in the project root with the following content:

```env
# MongoDB Credentials
MONGO_ROOT_USER=root
MONGO_ROOT_PWD=your_secure_root_password_here
MONGO_APP_DB=clash_royale
MONGO_APP_USER=data_scraper
MONGO_APP_PWD=your_secure_app_password_here
MONGO_INITDB_DATABASE=clash_royale
MONGO_HOST=mongo
MONGO_PORT=27017

# MongoDB Backup Configuration
BACKUP_HOUR=03
BACKUP_MINUTE=30
BACKUP_RETENTION_DAYS=7

# Clash Royale API Keys
DATA_SCRAPER_API_KEY=your_api_key_here
APP_API_KEY=your_api_key_here
```

**Replace the following values:**
- `your_secure_root_password_here` - Strong password for MongoDB root user
- `your_secure_app_password_here` - Strong password for application database user  
- `your_api_key_here` - Your Clash Royale API key(s)

## Step 4: Start the System

```bash
# Start all services in the background
docker compose up -d

# Check that all services are running
docker compose ps
```

You should see 4 services running:
- `mongo` - MongoDB database
- `mongo-backup` - Backup service
- `data_scraper` - Battle log collector
- `api` - REST API service

## Step 5: Verify Setup

### Check API Health
```bash
curl http://localhost:8000/ping
```
Expected response: `{"message":"pong"}`

### Check Logs
```bash
# Check API logs
docker compose logs api

# Check data scraper logs
docker compose logs data_scraper

# Check all logs
docker compose logs
```

## Step 6: Start Tracking Players

### Add Your First Player

Find a Clash Royale player tag (including yours). Player tags look like `#YYRJQY28`.

```bash
# Add a player to tracking (replace with actual player tag)
curl -X POST "http://localhost:8000/tracked-players/%23YYRJQY28"
```

**Note**: The `#` symbol must be URL-encoded as `%23`.

### Verify Player Was Added
```bash
curl http://localhost:8000/tracked-players
```

## Step 7: Wait for Data Collection

The data scraper runs every hour and collects battle logs for tracked players. Wait at least 1-2 hours after adding players before expecting data.

### Monitor Data Collection
```bash
# Watch data scraper logs
docker compose logs -f data_scraper
```

You should see logs like:
```
[INFO] Starting new data scraping cycle...
[INFO] Found 1 tracked players: {'#YYRJQY28'}
[INFO] Running data scraping cycle for Player #YYRJQY28 ...
```

## Step 8: Query Your Data

### Get Player Statistics
```bash
curl "http://localhost:8000/player-stats/%23YYRJQY28"
```

### Get Recent Battles
```bash
# Get last 5 battles
curl "http://localhost:8000/battles/%23YYRJQY28/last/5"
```

### Get Card Information
```bash
curl "http://localhost:8000/cards"
```

### Analyze Unique Decks
```bash
curl -X POST "http://localhost:8000/decks/unique" \
  -H "Content-Type: application/json" \
  -d '{"player_tag": "#YYRJQY28", "start_date": "2024-01-01", "end_date": "2024-12-31"}'
```

## Step 9: Advanced Usage Examples

### Tracking Multiple Players

You can track as many players as you want:

```bash
# Add multiple players
curl -X POST "http://localhost:8000/tracked-players/%23PLAYER1"
curl -X POST "http://localhost:8000/tracked-players/%23PLAYER2"
curl -X POST "http://localhost:8000/tracked-players/%23PLAYER3"

# List all tracked players
curl "http://localhost:8000/tracked-players"
```

### Analyzing Player Performance

```bash
# Get comprehensive player stats
curl "http://localhost:8000/player-stats/%23YYRJQY28" | jq '
{
  name: .name,
  trophies: .trophies,
  best_trophies: .bestTrophies,
  wins: .wins,
  losses: .losses,
  win_rate: (.wins / (.wins + .losses) * 100),
  three_crown_wins: .threeCrownWins
}'
```

### Battle History Analysis

```bash
# Get last 20 battles and analyze win rate
curl "http://localhost:8000/battles/%23YYRJQY28/last/20" | jq '
.battles | 
group_by(.gameResult) | 
map({result: .[0].gameResult, count: length}) |
from_entries
'
```

## Step 10: Data Backup and Maintenance

### Manual Backup
```bash
# Trigger manual backup
docker compose exec mongo-backup /backup.sh
```

### Restore from Backup
```bash
# List available backups
ls db/backups/

# Restore specific backup (Linux/macOS)
cd db
./restore.sh ./backups/clash_royale_2024-01-15_03-30-00

# Restore specific backup (Windows PowerShell)
cd db
.\restore.ps1 .\backups\clash_royale_2024-01-15_03-30-00
```

### View Database Directly
```bash
# Connect to MongoDB
docker compose exec mongo mongosh clash_royale -u data_scraper -p your_secure_app_password_here

# Example queries in MongoDB shell
db.players.find()
db.battles.countDocuments()
db.battles.find({"referencePlayerTag": "#YYRJQY28"}).limit(5)
```

## Troubleshooting

### Common Issues

#### 1. API Returns 403 Forbidden
- Check your API key is correct in `.env`
- Verify your IP address is whitelisted for the API key
- Make sure you're using the correct API key format

#### 2. No Battle Data After Hours
- Check data scraper logs: `docker compose logs data_scraper`
- Ensure player tags are correct and players exist
- Verify API key has sufficient quota

#### 3. Services Won't Start
- Check Docker is running
- Verify `.env` file exists and has correct format
- Check port 8000 is not in use: `lsof -i :8000`

#### 4. Database Connection Issues
- Restart services: `docker compose restart`
- Check MongoDB logs: `docker compose logs mongo`
- Verify credentials in `.env` file

### Useful Commands

```bash
# Restart all services
docker compose restart

# Rebuild services after code changes
docker compose up --build -d

# Stop all services
docker compose down

# Remove all data (careful!)
docker compose down -v

# View real-time logs
docker compose logs -f

# Check service status
docker compose ps

# Execute command in container
docker compose exec api bash
docker compose exec mongo mongosh
```

## Performance Tips

### 1. Optimize Data Collection
- Don't track too many players initially (start with 5-10)
- Monitor API quota usage
- Adjust `COOL_DOWN_SLEEP_DURATION` if hitting rate limits

### 2. Database Performance
- Keep backup retention reasonable (7-14 days)
- Monitor disk space usage
- Consider using named volumes for better performance

### 3. Query Optimization
- Use specific date ranges for deck analysis
- Limit battle count queries to reasonable numbers
- Cache frequently accessed data in your applications

## Integration Examples

### Python Script Example
```python
import requests
import json

BASE_URL = "http://localhost:8000"

# Add player to tracking
def add_player(player_tag):
    encoded_tag = player_tag.replace('#', '%23')
    response = requests.post(f"{BASE_URL}/tracked-players/{encoded_tag}")
    return response.json()

# Get player battles
def get_battles(player_tag, count=10):
    encoded_tag = player_tag.replace('#', '%23')
    response = requests.get(f"{BASE_URL}/battles/{encoded_tag}/last/{count}")
    return response.json()

# Usage
add_player("#YYRJQY28")
battles = get_battles("#YYRJQY28", 5)
print(json.dumps(battles, indent=2))
```

### JavaScript/Node.js Example
```javascript
const axios = require('axios');

const BASE_URL = 'http://localhost:8000';

async function addPlayer(playerTag) {
    const encodedTag = playerTag.replace('#', '%23');
    const response = await axios.post(`${BASE_URL}/tracked-players/${encodedTag}`);
    return response.data;
}

async function getPlayerStats(playerTag) {
    const encodedTag = playerTag.replace('#', '%23');
    const response = await axios.get(`${BASE_URL}/player-stats/${encodedTag}`);
    return response.data;
}

// Usage
(async () => {
    await addPlayer('#YYRJQY28');
    const stats = await getPlayerStats('#YYRJQY28');
    console.log(JSON.stringify(stats, null, 2));
})();
```

## Next Steps

Once you have the system running and collecting data:

1. **Build Dashboards**: Create web interfaces to visualize the data
2. **Automate Analysis**: Write scripts to generate regular reports
3. **Extend Functionality**: Add new endpoints or data processing
4. **Scale Up**: Track more players and analyze larger datasets
5. **Integrate**: Connect with Discord bots, mobile apps, or other tools

The system provides a solid foundation for any Clash Royale analytics project!