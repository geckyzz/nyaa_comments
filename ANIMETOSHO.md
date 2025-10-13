# AnimeTosho Scraper Documentation

## Overview

The AnimeTosho scraper is a separate script that monitors AnimeTosho comments and sends Discord notifications. It features keyword filtering, HTML to Markdown conversion, and uses a separate database file.

## Key Features

### 1. Keyword Filtering
Filter comments by torrent titles using multiple keywords:
```bash
python animetosho_scraper.py -k "[ToonsHub]" -k "[EMBER]" --webhook "URL"
```

### 2. Page Limit Control
- **Default**: 5 pages
- **Unlimited**: Set to 0 to scrape all available pages
- **Custom**: Any positive integer

```bash
# Scrape 10 pages
python animetosho_scraper.py --max-pages 10 --dump-comments

# Scrape all pages (unlimited)
python animetosho_scraper.py --max-pages 0 --dump-comments
```

### 3. HTML to Markdown Conversion
Comments are automatically converted from HTML to Markdown format:
- Links: `[text](url)`
- Line breaks: Preserved with double spaces
- Formatting: Bold, italic, etc.

### 4. Separate Database
Uses `database.at.json` instead of `database.json` to keep AnimeTosho and Nyaa data separate.

## Usage Examples

### Initialize Database
First run to populate the database without sending notifications:
```bash
python animetosho_scraper.py --dump-comments --max-pages 5
```

### Monitor with Keyword Filter
Monitor specific release groups:
```bash
python animetosho_scraper.py \
  --keyword "[ToonsHub]" \
  --keyword "[EMBER]" \
  --webhook "YOUR_DISCORD_WEBHOOK_URL"
```

### Monitor All Comments
Monitor all comments (no keyword filter):
```bash
python animetosho_scraper.py --webhook "YOUR_DISCORD_WEBHOOK_URL"
```

### Upload Database Backup
```bash
python animetosho_scraper.py \
  --upload-db \
  --db-expiry 24h \
  --secret-webhook "YOUR_SECRET_WEBHOOK_URL"
```

## How It Works

### 1. Comment Scraping
- Fetches pages from `https://animetosho.org/comments`
- Extracts comment divs (class `comment` or `comment2`)
- Parses torrent ID, title, username, timestamp, and message
- Converts HTML content to Markdown

### 2. Torrent ID Extraction
AnimeTosho uses compound IDs like:
- `subsplease-egao-no-taenai-shokuba-desu-02-1080p-e74d5e45-mkv.2028501`
- Numeric ID: `2028501` (extracted with regex)
- Full slug used as fallback

### 3. Keyword Matching
- Case-insensitive matching
- Matches against torrent title (not comment text)
- Multiple keywords supported (OR logic)
- If no keywords specified, all comments are included

### 4. Timestamp Parsing
Converts relative time strings to Unix timestamps:
- "Today 15:51" → Current date + time
- "Yesterday 23:47" → Previous date + time
- Approximate UTC-based calculation

### 5. Pagination Detection
Automatically detects maximum pages from HTML:
```html
<div class="pagination">
  <a href="...?page=3257">3257</a>
</div>
```

## Discord Notifications

### Embed Format
- **Color**: Orange (#FF6B00) for AnimeTosho
- **Title**: "New Comment on: [Torrent Title]"
- **URL**: Links to comment on AnimeTosho
- **Author**: Username (anonymous users handled)
- **Thumbnail**: AnimeTosho favicon
- **Description**: Markdown-formatted comment (up to 4096 chars)

### Rate Limiting
Automatic handling of Discord API rate limits with backoff.

## Database Structure

`database.at.json` format:
```json
{
  "2028501": [
    {
      "id": 148280,
      "pos": 1,
      "timestamp": 1760370660,
      "user": {
        "username": "Anonymous",
        "image": null
      },
      "message": "Comment text in Markdown format"
    }
  ]
}
```

## Configuration

### CLI Arguments
- `base_url`: AnimeTosho URL (default: `https://animetosho.org/comments`)
- `--dump-comments`: Initialize database without notifications
- `--webhook`: Discord webhook URL
- `--secret-webhook`: Separate webhook for sensitive data
- `--keyword` / `-k`: Filter by keyword (multiple allowed)
- `--max-pages`: Maximum pages to scrape (default: 5, 0 = unlimited)
- `--upload-db`: Upload encrypted database backup
- `--db-expiry`: Backup expiry time (1h, 12h, 24h, 72h)

### Environment Variables
- `DISCORD_WEBHOOK_URL`: Default webhook
- `DISCORD_SECRET_WEBHOOK_URL`: Webhook for sensitive data

### .secrets.json
```json
{
  "discord_webhook_url": "https://discord.com/api/webhooks/...",
  "discord_secret_webhook_url": "https://discord.com/api/webhooks/..."
}
```

## Differences from Nyaa Scraper

| Feature | Nyaa Scraper | AnimeTosho Scraper |
|---------|--------------|-------------------|
| Database | `database.json` | `database.at.json` |
| Cookies | Supported | Not needed |
| User roles | Trusted/Uploader | Not available |
| Comment format | Plain text | HTML → Markdown |
| URL patterns | `/view/{id}` | `/view/{slug}.n{id}` |
| Default pages | Unlimited | 5 (configurable) |
| Keyword filter | Not available | Multiple keywords |
| Single torrent mode | Supported | Not applicable |

## Troubleshooting

### No Comments Found
- Check if keywords are too restrictive
- Verify the URL is correct
- Try increasing `--max-pages`

### Database Not Saving
- Ensure write permissions in directory
- Check for disk space
- Verify JSON format is not corrupted

### Markdown Not Rendering
- Discord has 4096 character limit for descriptions
- Very long comments are truncated automatically

### Rate Limited
- Script automatically handles Discord rate limits
- Wait for cooldown period
- Consider reducing notification frequency

## Implementation Details

### Key Classes
1. **AnimeToshoScraper**: Main scraper logic
   - `_get_page()`: Fetch and parse HTML
   - `_get_max_page_from_pagination()`: Extract max page
   - `scrape_comments_from_page()`: Parse comments from page
   - `_html_to_markdown()`: Convert HTML to Markdown
   - `_matches_keywords()`: Filter by keywords

2. **DatabaseManager**: Shared with Nyaa scraper
   - Handles both numeric and alphanumeric IDs
   - Sorts appropriately based on ID type

3. **DiscordWebhook**: Enhanced for AnimeTosho
   - `is_animetosho` parameter for different formatting
   - Orange color and AnimeTosho URLs

### Dependencies
- `markdownify>=0.11.0`: HTML to Markdown conversion
- `beautifulsoup4>=4.12.0`: HTML parsing
- `requests>=2.31.0`: HTTP requests
- `typer>=0.9.0`: CLI interface
- `alive-progress>=3.1.0`: Progress bars

## Future Improvements

Potential enhancements:
- Support for single torrent monitoring
- Advanced filtering (regex, date ranges)
- Custom Markdown formatting options
- Multi-threaded scraping for speed
- Comment search functionality
