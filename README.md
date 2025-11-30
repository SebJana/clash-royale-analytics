# Clash Royale Analytics

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

# Redis credentials
REDIS_PASSWORD=YOUR_SECURE_REDIS_PASSWORD

# JWT Secret for Admin Authentication
JWT_SECRET=YOUR_SECURE_JWT_SECRET_KEY

# Security Question Answers for Admin Access
MOST_ANNOYING_CARD="Card1"
MOST_SKILLFUL_CARD="Card2"
MOST_MOUSEY_CARD="Card3"

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

#### Redis credentials

- `REDIS_PASSWORD`: Secure password for the redis database

#### JWT Authentication

- `JWT_SECRET`: Secret key used for signing JWT tokens for admin authentication. Should be a long, random string for security.

#### Security Questions

- `MOST_ANNOYING_CARD`: Answer to the first security question for admin access (Most annoying card in Clash Royale)
- `MOST_SKILLFUL_CARD`: Answer to the second security question for admin access (Most skillful card in Clash Royale)
- `MOST_MOUSEY_CARD`: Answer to the third security question for admin access (Most 'mousey/cutie/sweet' card in Clash Royale)

**Note**: These security questions are used as a fun authentication method for admin operations like un-tracking players. They don't provide any real security, unless an actual non-guessable string is chosen for any of those answers.

#### Clash Royale API Keys

- `DATA_SCRAPER_API_KEY`: API Key used to run the cyclic tracking and refreshing of selected player(s)
- `APP_API_KEY`: API Key used to query on-demand data for an active user

It’s possible to use the same key for both parameters/roles, but for modulation purposes and to comply with the request limitations stated by Clash Royale, it’s advised to use separate keys. Get your API Keys from the official Clash Royale API website: https://developer.clashroyale.com

// TODO (potentially) add the option to use multiple keys with a key rotation for the Clash Royale API calls
Make it a shared module for both data scraping and the api

### 2. Docker Setup (Production)

Start all services by running:

```bash
docker compose up -d
```

### 2. Local Development Setup

For local development, you can run the frontend and backend separately:

#### Backend

Start all required docker services for the backend (api, mongo, redis)

#### Frontend

1. Navigate to the frontend directory:

   ```bash
   cd frontend
   ```

2. Install Node.js dependencies:

   ```bash
   npm install
   ```

3. Start the development server:

   ```bash
   npm start
   ```

   The frontend will be available at `http://localhost:5173`

**Note**: The Vite development server is configured to proxy `/api` requests to `http://localhost:8000`, so both services need to be running for local development.

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
