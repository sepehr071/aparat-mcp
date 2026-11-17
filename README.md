<!-- mcp-name: io.github.sepehr071/aparat-mcp -->

<div align="center">

<img src="https://raw.githubusercontent.com/sepehr071/aparat-mcp/main/.github/banner.png" alt="aparat-mcp: unofficial Aparat (آپارات) MCP server that searches Iranian videos and channels, reads comments and lists trending videos for Claude, Cursor and Copilot" width="100%">

# aparat-mcp: Aparat (آپارات) Iranian video platform MCP server for AI agents

**aparat-mcp is an unofficial, read-only MCP server that lets an AI agent search videos and channels, read video details and comments, and see what is trending on Aparat (آپارات, aparat.com), the biggest Iranian video platform.**<br>
Its 8 tools search videos and channels, show a video (views, likes, duration, tags, category, channel, publish date), its comments and related videos, show a channel and its newest or most viewed videos, and list trending videos overall or per category.<br>
No API key or account is needed; it works in Claude, Cursor, Copilot and any other MCP client.

[![PyPI](https://img.shields.io/pypi/v/aparat-mcp?color=2563eb)](https://pypi.org/project/aparat-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/aparat-mcp)](https://pypi.org/project/aparat-mcp/)
[![CI](https://github.com/sepehr071/aparat-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/sepehr071/aparat-mcp/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-16a34a)](https://github.com/sepehr071/aparat-mcp/blob/main/LICENSE)

[For AI agents](#for-ai-agents) · [Quick start](#quick-start) · [Tools](#tools) · [Limits](#limits) · [فارسی](#فارسی)

</div>

---

## For AI agents

- **What:** unofficial MCP server (model context protocol) for aparat.com: video and channel search, video details, comments, related videos, channel pages and trending feeds.
- **Install:** `uvx aparat-mcp` or `claude mcp add aparat -- uvx aparat-mcp`. Transport: stdio. Needs [uv](https://docs.astral.sh/uv/getting-started/installation/) (Python 3.10+).
- **Auth:** none. Optional `APARAT_MCP_PROXY` (HTTP proxy URL, or a comma-separated list); system proxy settings are ignored.
- **Access:** read-only. It cannot log in, upload, comment, like or follow. Video files and stream links are not exposed, only page URLs.
- **Tools:** 8, all prefixed `apr_`. Typical sequences: `apr_search` -> `apr_video` / `apr_channel`; `apr_channel` -> `apr_channel_videos`; `apr_categories` -> `apr_trending`; `apr_video` -> `apr_comments` / `apr_related`.
- **Use when:** the user asks what is popular on Aparat, wants to find Persian videos or a creator's channel, asks how many views, likes or followers something has, or wants to read what viewers say under a video.
- **Output:** compact JSON. Views are counts, duration is seconds, dates are Gregorian. Titles and comments are Persian.

## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). No API key or account.

Claude Code:

```bash
claude mcp add aparat -- uvx aparat-mcp
```

Claude Desktop, Cursor, VS Code and other clients:

```json
{
  "mcpServers": {
    "aparat": { "command": "uvx", "args": ["aparat-mcp"] }
  }
}
```

Example prompts:

- "Search Aparat for Persian cooking videos."
- "What are the most viewed videos of the channel macharta?"
- "What is trending in music on Aparat?"
- <span dir="rtl">نظرات این ویدیوی آپارات را بخوان.</span>
- <span dir="rtl">پربازدیدترین ویدیوهای کانال ماچارتا کدام‌اند؟</span>

Real answer (17 Nov 2026): `apr_channel_videos(channel="macharta", sort="top")` returned 2,118,476 views for the top video of that channel, then 1,650,691 and 1,488,902.

## Tools

| Tool | What it returns |
|---|---|
| `apr_search` | Videos and channels matching a text, in relevance order, paged with `next` |
| `apr_video` | One video: title, description, views, likes, comments, duration, tags, category, channel, publish date |
| `apr_comments` | Top comments of a video, 10 per page |
| `apr_related` | Videos Aparat recommends next to a video (about 10) |
| `apr_channel` | A channel: name, followers, video count, total views, description, start date |
| `apr_channel_videos` | A channel's videos, newest first or most viewed, 10 per page |
| `apr_categories` | The category names Aparat's trending tabs use |
| `apr_trending` | Trending videos overall or in one category (up to 40) |

## Limits

- Counters on Aparat change by the second, so a view count read twice a minute apart can differ slightly.
- Channel video lists and comments come 10 per page; search about 40 per page. Use the `next` token or `page` for more.
- Overall trending (the site's "hottest" row) is not shown on Aparat's logged-out home page, so it was checked against the API only, not against the rendered page. Category trending was checked against the page.
- Stream links, downloads, live streams and anything behind a login (history, subscriptions, uploads) are not covered.
- Aparat answers both Iranian and foreign networks in testing; if your network is blocked, set `APARAT_MCP_PROXY`. The server ignores system proxy variables on purpose.

## How it works

Aparat has no public API documentation. The endpoints were mapped by watching aparat.com in Chrome, and every tool was then checked in Chrome against the real rendered pages (search, video, comments, channel, channel videos, categories, trending, related) on 16 Nov 2026. The server calls those same public endpoints through a Chrome-impersonating HTTP client, with a short cache and at most two requests at a time.

## فارسی

<div dir="rtl">

**aparat-mcp** یک سرور MCP غیررسمی و فقط‌خواندنی برای آپارات (aparat.com) است. با آن یک عامل هوش مصنوعی می‌تواند ویدیوها و کانال‌ها را جست‌وجو کند، جزئیات ویدیو (بازدید، لایک، مدت، برچسب‌ها، دسته‌بندی)، نظرات و ویدیوهای مرتبط را بخواند، کانال و پربازدیدترین ویدیوهایش را ببیند و ویدیوهای پربازدید و داغ هر دسته را فهرست کند. بدون حساب کاربری و کلید API کار می‌کند. نصب در Claude Code:

</div>

```bash
claude mcp add aparat -- uvx aparat-mcp
```

## Development

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run python -m pytest -q          # offline tests on recorded fixtures
uv run python -m pytest -m live -q  # live calls to aparat.com
```

Releases: bump the version in `pyproject.toml` and `server.json`, run `uv lock`, then push a `v*` tag; GitHub Actions publishes to PyPI.

## Disclaimer

Unofficial and not affiliated with or endorsed by Aparat. It is read-only and uses the public pages and API of aparat.com, which can change without notice.

## Author

Built and maintained by **Sepehr Radmard** (سپهر رادمرد). [LinkedIn](https://www.linkedin.com/in/sepehr-radmard) · [GitHub](https://github.com/sepehr071) · more servers in [iran-mcp](https://github.com/sepehr071/iran-mcp).

## License

[MIT](https://github.com/sepehr071/aparat-mcp/blob/main/LICENSE)
