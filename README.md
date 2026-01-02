# Telegram Sport Challenge Bot

A dockerized Python application (FastAPI) for a Telegram Sport Challenge Bot.

## Features
- Strava Integration
- Weighted Score Calculation
- Leaderboard

## Deployment

### GitHub Actions
This repository includes a GitHub Actions workflow that automatically builds and pushes the Docker image to the **GitHub Container Registry (GHCR)**.

- **Trigger:** Pushes to the `main` branch or manual execution via the "Actions" tab.
- **Image:** `ghcr.io/<owner>/family-sport-challenge-bot:latest`

### Configuration
The application is configured via environment variables. Create a `.env` file in the root directory:

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# Strava
STRAVA_CLIENT_ID=your_strava_id
STRAVA_CLIENT_SECRET=your_strava_secret
STRAVA_REDIRECT_URI=https://your-domain.com/strava/auth
WEBHOOK_VERIFY_TOKEN=your_secure_token

# Optional Sync Settings (YYYY-MM-DD)
STRAVA_SYNC_START_DATE=2024-01-01
STRAVA_SYNC_END_DATE=2024-12-31
```

### Running with Docker Compose
To build and run the bot locally:

```bash
docker-compose up -d --build
```

To run using the image built by GitHub Actions, update your `docker-compose.yml` to use the image from GHCR:

```yaml
services:
  bot:
    image: ghcr.io/<owner>/family-sport-challenge-bot:latest
    ports:
      - "8000:8000"
    env_file:
      - .env
    restart: always
```
