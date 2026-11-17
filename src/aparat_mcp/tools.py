"""Aparat tools: search, video detail, comments, related, channels, trending and categories."""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal
from urllib.parse import parse_qsl, quote

from pydantic import Field

from .http import SITE, ApiError, fetch
from .registry import tool

V0 = f"{SITE}/api/v0"
V1 = f"{SITE}/api/fa/v1"
UID = re.compile(r"^[A-Za-z0-9]{3,12}$")
USERNAME = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")
DESC_MAX = 1500

Video = Annotated[
    str, Field(description="Video uid (the part after /v/ in the URL, e.g. jjbwme6) or the full aparat.com video URL.")
]
Channel = Annotated[str, Field(description="Channel username (the part after aparat.com/, e.g. macharta).")]


def _uid(video: str) -> str:
    uid = (m.group(1) if (m := re.search(r"/v/([A-Za-z0-9]+)", video)) else video).strip()
    if not UID.match(uid):
        raise ApiError(f"'{video}' is not a video uid or aparat.com video URL.")
    return uid


def _user(channel: str) -> str:
    name = channel.strip().removeprefix(f"{SITE}/").strip("/")
    if not USERNAME.match(name):
        raise ApiError(f"'{channel}' is not a channel username.")
    return name


def _int(v: Any) -> int | None:
    try:
        return int(str(v).replace(",", ""))
    except ValueError:
        return None


def _video(v: dict) -> dict:
    """One video line as the feeds return it."""
    return {
        "uid": v.get("uid"),
        "title": v.get("title"),
        "channel": v.get("username"),
        "channel_name": v.get("sender_name"),
        "views": _int(v.get("visit_cnt_int")),
        "likes": _int(v.get("like_cnt")),
        "duration_s": _int(v.get("duration")),
        "published": v.get("sdate_rss"),
        "url": f"{SITE}/v/{v.get('uid')}",
    }


def _feed_videos(d: dict) -> list[dict]:
    """Videos of a JSON:API row feed, in row order, without repeats."""
    by_id = {i["id"]: i["attributes"] for i in d.get("included", []) if i.get("type") == "Video"}
    seen: set[str] = set()
    out = []
    for row in d.get("data", []):
        for ref in (row.get("relationships") or {}).get("video", {}).get("data", []):
            if ref["id"] in by_id and ref["id"] not in seen:
                seen.add(ref["id"])
                out.append(_video(by_id[ref["id"]]))
    return out


def _check(body: Any) -> Any:
    if isinstance(body, dict) and (e := body.get("error")):
        raise ApiError(f"Aparat rejected the request: {e.get('message') if isinstance(e, dict) else e}")
    return body


@tool("Search Aparat")
async def apr_search(
    query: Annotated[str, Field(description="Persian or English search text, at least 2 characters.")],
    next: Annotated[str | None, Field(description="`next` token from a previous result, for the next page.")] = None,
) -> dict:
    """Search Aparat videos and channels by text.

    Returns matching channels and videos in relevance order (about 40 per page). Pass `next` for more. Use
    apr_video with a uid for full details, apr_channel with a username for a channel.
    """
    body = _check(
        await fetch(
            f"{V0}/search/mix/{quote(query.strip(), safe='')}", {"nextq": next, "isnextpage": "true"} if next else None
        )
    )
    block = (body.get("data") or [{}])[0]
    videos, channels = [], []
    for x in (block.get("mixV2") or {}).get("data", []):
        d = x.get("data") or {}
        if x.get("type") == "Video":
            videos.append(_video(d))
        elif x.get("type") == "ChannelInfo":
            channels.append(
                {
                    "username": d.get("username"),
                    "name": d.get("name"),
                    "followers": d.get("follower_cnt"),
                    "videos": _int(d.get("video_cnt")),
                    "description": (d.get("description") or "")[:200],
                }
            )
    nxt = dict(parse_qsl((block.get("link") or {}).get("next", "").partition("?")[2])).get("nextq")
    return {"channels": channels, "videos": videos, "next": nxt}


@tool("Aparat video details")
async def apr_video(video: Video) -> dict:
    """Get one Aparat video: title, description, views, likes, duration, tags, category, channel, publish date.

    Use apr_comments for what viewers wrote and apr_related for similar videos.
    """
    d = (await fetch(f"{V0}/videos/{_uid(video)}")).get("data") or {}
    if not d.get("id"):
        raise ApiError(f"No Aparat video '{video}'.", 404)
    ch = (d.get("Channel") or {}).get("data") or {}
    return {
        "uid": d.get("uid"),
        "title": d.get("title"),
        "description": (d.get("description") or d.get("meta_description") or "")[:DESC_MAX],
        "views": d.get("visit_cnt_non_formatted"),
        "likes": d.get("like_cnt_non_formatted"),
        "comments": _int(d.get("comment_cnt_non_formatted")),
        "duration_s": _int(d.get("duration")),
        "published": d.get("sdate_real"),
        "tags": d.get("tags"),
        "category": (d.get("category") or {}).get("name"),
        "max_resolution": f"{d.get('max_width')}x{d.get('max_height')}" if d.get("max_width") else None,
        "channel": {"username": ch.get("username"), "name": ch.get("name"), "followers": ch.get("follower_cnt")},
        "url": f"{SITE}/v/{d.get('uid')}",
    }


@tool("Aparat video comments")
async def apr_comments(
    video: Video,
    next: Annotated[str | None, Field(description="`next` token from a previous result, for older comments.")] = None,
) -> dict:
    """Read the top comments under an Aparat video (10 per page, most liked first as the site orders them).

    Pass `next` for more. An empty list means no comments or comments are off.
    """
    body = await fetch(f"{V0}/videos/{_uid(video)}/comments", dict(parse_qsl(next)) if next else None)
    out = []
    for c in body.get("data", []):
        u = (c.get("channel") or {}).get("data") or {}
        out.append(
            {
                "text": c.get("body"),
                "user": u.get("username"),
                "user_name": u.get("name"),
                "likes": _int(c.get("like_cnt")),
                "replies": _int(c.get("reply_cnt")),
                "date": c.get("sdate_gregorian"),
                "pinned": c.get("is_pinned") or None,
                "by_channel_owner": c.get("isOwnerComment") or None,
            }
        )
    more = (body.get("links") or {}).get("more") or ""
    return {"comments": out, "next": more.partition("?")[2] or None}


@tool("Related Aparat videos")
async def apr_related(video: Video) -> dict:
    """List videos Aparat recommends next to a video (about 10).

    Use apr_video for details of one of them.
    """
    body = await fetch(f"{V0}/videos/{_uid(video)}/recommendations")
    return {"videos": [_video(v) for v in (body.get("data") or {}).get("video_recom", [])]}


@tool("Aparat channel")
async def apr_channel(channel: Channel) -> dict:
    """Get an Aparat channel: name, followers, video count, total views, description, start date.

    Use apr_channel_videos for its videos.
    """
    d = (await fetch(f"{V0}/users/username/{_user(channel)}")).get("data") or {}
    return {
        "username": d.get("username"),
        "name": d.get("name"),
        "description": (d.get("description") or "")[:DESC_MAX],
        "followers": d.get("follower_cnt_num"),
        "following": _int(d.get("follow_cnt")),
        "videos": _int(d.get("video_cnt")),
        "total_views_text": d.get("video_visit"),
        "started": d.get("start_date"),
        "verified": d.get("official") or None,
        "url": f"{SITE}/{d.get('username')}",
    }


@tool("Aparat channel videos")
async def apr_channel_videos(
    channel: Channel,
    sort: Annotated[
        Literal["latest", "top"], Field(description="latest = newest first; top = most viewed.")
    ] = "latest",
    page: Annotated[int, Field(ge=1, le=50, description="Page number, 10 videos per page.")] = 1,
) -> dict:
    """List a channel's videos, newest first or most viewed (10 per page).

    Use apr_video for details of one.
    """
    u = _user(channel)
    if sort == "top":
        path = f"{V1}/user/video/list/username/{u}/type/top/more_type/infinity_btn/page/{page}/perpage/10"
    else:
        path = f"{V1}/user/video/last_videos_more/username/{u}/page/{page}/perpage/10"
    return {"videos": _feed_videos(await fetch(path)), "page": page}


@tool("Aparat trending categories")
async def apr_categories() -> dict:
    """List the category names Aparat's trending tabs use.

    Pass one as `category` to apr_trending.
    """
    body = await fetch(f"{V1}/etc/page/home_tabs")
    return {"categories": [t["text"] for t in body["data"]["attributes"] if t.get("type") == "trend"]}


@tool("Trending Aparat videos")
async def apr_trending(
    category: Annotated[
        str | None, Field(description="Category name from apr_categories. Omit for overall hot videos.")
    ] = None,
) -> dict:
    """List trending Aparat videos, overall or in one category (up to 40).

    Use apr_video for details of one.
    """
    if category:
        d = await fetch(f"{V1}/video/video/list/tagid/51/slug/{quote(category.strip(), safe='')}")
        return {"category": category, "videos": _feed_videos(d)}
    d = await fetch(f"{V1}/video/video/list/tagid/1")
    # shortcut: picks the row titled "hottest" by its Persian title; falls back to the first row if the site renames it
    rows = d.get("data", [])
    hot = [r for r in rows if "داغ" in str(r["attributes"].get("title", {}).get("text"))] or rows[:1]
    return {"videos": _feed_videos({**d, "data": hot})}
