# Nyaa Comments Scraper

A Python script that monitors Nyaa.si torrents for new comments and sends
real-time notifications to Discord. Supports both listing pages and individual
torrent monitoring.

> [!NOTE]
>
> This project was developed with AI assistance. All code and functionality
> have been thoroughly tested and inspected to ensure reliability and correctness.

## Features

- **Dual Mode Support**: Monitor entire listing pages or specific torrent pages
- **Discord Notifications**: Rich embed notifications with user avatars and roles
  (Trusted/Uploader)
- **Smart Tracking**: Only notifies about new comments, stores history in local JSON database
- **Rate Limit Handling**: Automatic Discord API rate limit management
- **Cookie Support**: Optional authentication via Netscape-format cookies
- **GitHub Actions**: Automated monitoring with scheduled workflow (every 5 minutes)
- **Progress Bars**: Real-time progress indicators for scraping operations

## Installation

### Requirements

- Python 3.10+
- Dependencies:
  ```bash
  pip install typer pydantic requests beautifulsoup4 alive-progress
  ```

### Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/nyaa_comments.git
   cd nyaa_comments
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Command Line

Basic usage with Discord webhook:

```bash
python nyaa_comments.py "https://nyaa.si/?f=0&c=0_0&q=anime" --webhook "YOUR_DISCORD_WEBHOOK_URL"
```

Monitor a specific torrent:

```bash
python nyaa_comments.py "https://nyaa.si/view/2008634"
```

Initialize database without notifications:

```bash
python nyaa_comments.py "https://nyaa.si/?f=0&c=0_0&q=anime" --dump-comments
```

With custom cookies file:

```bash
python nyaa_comments.py "https://nyaa.si/?f=0&c=0_0&q=anime" --cookies "/path/to/cookies.txt"
```

### Configuration Options

#### **Discord Webhook** (priority order)

1. `--webhook` CLI argument
2. `.secrets.json` file: `{"discord_webhook_url": "..."}`
3. `DISCORD_WEBHOOK_URL` environment variable

#### **Arguments**

- `base_url` (required): Nyaa.si URL to scrape (listing or torrent page)

#### **Options**

- `--webhook TEXT`: Discord webhook URL
- `--dump-comments`: Initialize database without sending notifications
- `--cookies TEXT`: Path to Netscape-format cookies file
- `--help`: Show help message

## GitHub Actions Setup

This repository includes a workflow that automatically monitors Nyaa.si every 5 minutes.

### Setup Instructions

1. Go to your repository **Settings** → **Secrets and variables** → **Actions**

2. Add the following **secrets**:
   - `DISCORD_WEBHOOK_URL`: Your Discord webhook URL
   - `NYAA_URL`: The Nyaa.si URL to monitor

3. The workflow will:
   - Run automatically every 5 minutes
   - Can be triggered manually from Actions tab
   - Caches database privately (not committed to repo)
   - Prevents concurrent runs

### Manual Workflow Trigger

You can manually trigger the workflow with options:
- Check "Initialize database without sending notifications" to use `--dump-comments` mode

## How It Works

1. **Scraping**: Fetches torrent listings or individual torrent pages from Nyaa.si
2. **Comment Detection**: Identifies torrents with comments and their counts
3. **Comparison**: Compares current comments with stored database
4. **Notification**: Sends Discord embeds for new comments only
5. **Storage**: Updates local `database.json` with all comments

## Database Structure

The script maintains a `database.json` file:

```json
{
  "1234567": [
    {
      "id": 123,
      "pos": 1,
      "timestamp": 1697123456,
      "user": {
        "username": "user123",
        "image": "https://example.com/avatar.jpg"
      },
      "message": "Thanks for the upload!"
    }
  ]
}
```

Where `1234567` is your torrent listing ID in Nyaa.

## Discord Embed Features

Each notification includes:
- Torrent title with link
- Comment text
- Username with avatar
- User role badge (Trusted/Uploader)
- Timestamp
- Direct link to comment

## Security Notes

- The `database.json` is excluded from git via `.gitignore`
- In GitHub Actions, database is cached privately
- Secrets are stored in GitHub Secrets, not in code
- Cookie files are never committed to repository

## License

See [LICENSE](LICENSE) file for details.
