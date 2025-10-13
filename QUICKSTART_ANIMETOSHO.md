# AnimeTosho Scraper - Quick Start Guide

## Installation
```bash
pip install markdownify
```

## Common Usage Patterns

### 1. Initialize Database (First Run)
```bash
# All comments, 5 pages (default)
python animetosho_scraper.py --dump-comments

# Filter by keyword, 10 pages
python animetosho_scraper.py --dump-comments -k "[ToonsHub]" --max-pages 10

# Multiple keywords, unlimited pages
python animetosho_scraper.py --dump-comments -k "[EMBER]" -k "[SubsPlease]" --max-pages 0
```

### 2. Monitor for New Comments
```bash
# All comments
python animetosho_scraper.py --webhook "https://discord.com/api/webhooks/..."

# Filter by keywords
python animetosho_scraper.py -k "[ToonsHub]" --webhook "YOUR_WEBHOOK_URL"
```

### 3. Backup Database
```bash
python animetosho_scraper.py --upload-db --db-expiry 24h --secret-webhook "YOUR_WEBHOOK"
```

## Quick Tips

- **Default pages**: 5 (set `--max-pages 0` for unlimited)
- **Database file**: `database.at.json` (separate from Nyaa's `database.json`)
- **Keyword matching**: Case-insensitive, matches torrent title
- **Multiple keywords**: Use multiple `-k` flags (OR logic)
- **Comments format**: Automatically converted from HTML to Markdown

## Keyword Examples

### Monitor Specific Release Groups
```bash
python animetosho_scraper.py \
  -k "[ToonsHub]" \
  -k "[EMBER]" \
  -k "[SubsPlease]" \
  --webhook "URL"
```

### Monitor by Series Name
```bash
python animetosho_scraper.py -k "Blue Orchestra" --webhook "URL"
```

### Monitor Everything
```bash
# No -k flag = no filtering
python animetosho_scraper.py --webhook "URL"
```

## Help
```bash
python animetosho_scraper.py --help
```
