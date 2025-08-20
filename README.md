# Clash Royale Analytics

A comprehensive data analytics system for Clash Royale that automatically tracks player battle logs, provides detailed statistics, and offers powerful querying capabilities through a REST API.

## 🚀 What Can You Do With This System?

This platform enables you to:
- **Track Players Automatically**: Monitor any Clash Royale player's battles 24/7
- **Analyze Performance**: Get detailed win rates, deck analysis, and progression tracking  
- **Study the Meta**: See what decks and strategies top players are using
- **Historical Analysis**: Query battle data across custom date ranges
- **Build Applications**: Use the REST API to create dashboards, bots, or mobile apps

📖 **[View Complete Capabilities Guide](CAPABILITIES.md)** - See everything you can accomplish

📚 **[API Documentation](API_DOCUMENTATION.md)** - Complete endpoint reference

🎯 **[Setup Tutorial](TUTORIAL.md)** - Step-by-step guide with examples

## Quick Start

### 1. Get API Keys
Get your API keys from the [official Clash Royale API](https://developer.clashroyale.com)

### 2. Setup Environment
```bash
cp .env.example .env
# Edit .env with your API keys and secure passwords
```

### 3. Start System
```bash
docker compose up -d
```

### 4. Add Players to Track
```bash
curl -X POST "http://localhost:8000/tracked-players/%23YYRJQY28"
```

### 5. Query Data
```bash
curl "http://localhost:8000/player-stats/%23YYRJQY28"
curl "http://localhost:8000/battles/%23YYRJQY28/last/10"
```

## Architecture

- **Data Scraper**: Continuously collects battle logs every hour
- **REST API**: FastAPI service providing data access endpoints  
- **MongoDB**: Scalable database with optimized indexing
- **Backup System**: Automated daily backups with retention policies
- **Docker Deployment**: Complete containerized setup

## Setup

### 1. Environment Configuration

Create a `.env` file in the project root with the following configuration:

```env
# MongoDB Credentials
MONGO_ROOT_USER=root
MONGO_ROOT_PWD=YOUR_SECURE_ROOT_PASSWORD
MONGO_APP_DB=clash_royale
MONGO_APP_USER=data_scraper
MONGO_APP_PWD=YOUR_SECURE_USER_PASSWORD
MONGO_INITDB_DATABASE=clash_royale
MONGO_HOST=mongo
MONGO_PORT=27017

# MongoDB Backup Configuration
BACKUP_HOUR=03
BACKUP_MINUTE=30
BACKUP_RETENTION_DAYS=7

# Clash Royale API Keys
DATA_SCRAPER_API_KEY = ey31asd23...
APP_API_KEY = ey41eas...
```

### Environment Variables Explained

#### MongoDB Configuration
- `MONGO_ROOT_USER`: MongoDB root administrator username (default: `root`)
- `MONGO_ROOT_PWD`: Secure password for the MongoDB root user
- `MONGO_APP_DB`: Database name for the application (default: `clash_royale`)
- `MONGO_APP_USER`: Application user for database operations (default: `data_scraper`)
- `MONGO_APP_PWD`: Secure password for the application user
- `MONGO_INITDB_DATABASE`: Database to initialize with the application user (must match `MONGO_APP_DB`)
- `MONGO_HOST`: Hostname of the MongoDB service (default: mongo when running in Docker Compose)
- `MONGO_PORT`: Port number where MongoDB is exposed (default: 27017)


#### Backup Configuration
- `BACKUP_HOUR`: Hour (0-23) when daily backups run (default: `03` = 3 AM)
- `BACKUP_MINUTE`: Minute (0-59) when daily backups run (default: `30`)
- `BACKUP_RETENTION_DAYS`: Number of days to keep backup files (default: `7`)

#### Clash Royale API Keys
- `DATA_SCRAPER_API_KEY`: API Key used to run the cyclic tracking and refreshing of selected player(s)
- `APP_API_KEY`: API Key used to query on-demand data for an active user

It’s possible to use the same key for both parameters/roles, but for modulation purposes and to comply with the request limitations stated by Clash Royale, it’s advised to use separate keys. Get your API Keys from the official Clash Royale API website: https://developer.clashroyale.com

### 2. Docker Setup

Start all services by running:

```bash
docker compose up -d
```

### 3. Restoring Data

Example Commands for restoring data 

#### On Linux/macOS/WSL
```bash
cd db
./restore.sh ./backups/clash_royale_YYYY-MM-DD_HH-MM-SS
```

#### On Windows PowerShell
```bash
cd db
.\restore.ps1 .\backups\clash_royale_YYYY-MM-DD_HH-MM-SS
```