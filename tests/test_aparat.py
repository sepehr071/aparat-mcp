import json

import pytest
from conftest import fixture

from aparat_mcp import http

pytestmark = pytest.mark.anyio

TOOLS = {
    "apr_search",
    "apr_video",
    "apr_comments",
    "apr_related",
    "apr_channel",
    "apr_channel_videos",
    "apr_categories",
    "apr_trending",
}


async def test_all_tools_are_read_only_and_described(client):
    tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == TOOLS
    for t in tools:
        assert t.annotations.read_only_hint is True, t.name
        assert t.title and t.description.splitlines()[0].endswith("."), t.name


async def test_search_splits_channels_and_videos(client, api):
    api["/api/v0/search/mix/آشپزی"] = fixture("search.json")
    r = (await client.call_tool("apr_search", {"query": "آشپزی"})).structured_content
    assert r["channels"][0]["username"] == "ashpazibasomaye"
    v = r["videos"][0]
    assert v["uid"] == "jjbwme6" and v["views"] > 1_000_000 and v["duration_s"] == 120
    assert v["url"] == "https://www.aparat.com/v/jjbwme6"
    assert r["next"]


async def test_search_error_body_becomes_tool_error(client, api):
    api["/api/v0/search/mix/x"] = {"error": {"code": "invalid_request", "message": "text too short"}}
    r = await client.call_tool("apr_search", {"query": "x"})
    assert r.is_error and "text too short" in r.content[0].text


async def test_video_detail_drops_stream_urls(client, api):
    api["/api/v0/videos/jjbwme6"] = fixture("video.json")
    r = (await client.call_tool("apr_video", {"video": "https://www.aparat.com/v/jjbwme6?x=1"})).structured_content
    assert r["title"].startswith("تریلر") and r["views"] > 1_298_000 and r["duration_s"] == 120
    assert r["channel"]["username"] == "filimo" and r["category"] and r["tags"]
    assert "m3u8" not in json.dumps(r)


async def test_video_rejects_bad_id(client, api):
    r = await client.call_tool("apr_video", {"video": "../etc"})
    assert r.is_error and not api.calls


async def test_video_not_found(client, api):
    api["/api/v0/videos/zzzzzzz"] = {"data": [], "meta": {"status": 404}}
    assert (await client.call_tool("apr_video", {"video": "zzzzzzz"})).is_error


async def test_comments_and_next_token(client, api):
    api["/api/v0/videos/ewcw97o/comments"] = fixture("comments.json")
    r = (await client.call_tool("apr_comments", {"video": "ewcw97o"})).structured_content
    assert r["comments"][0]["likes"] == 97 and r["comments"][0]["user"] == "Ripmahdim"
    assert r["next"].startswith("cursor=")
    await client.call_tool("apr_comments", {"video": "ewcw97o", "next": r["next"]})
    assert api.calls[-1].url.params["cursor"] == "136622342"


async def test_related(client, api):
    api["/api/v0/videos/jjbwme6/recommendations"] = fixture("related.json")
    r = (await client.call_tool("apr_related", {"video": "jjbwme6"})).structured_content
    assert len(r["videos"]) == 3 and r["videos"][0]["uid"]


async def test_channel(client, api):
    api["/api/v0/users/username/macharta"] = fixture("channel.json")
    r = (await client.call_tool("apr_channel", {"channel": "macharta"})).structured_content
    assert r["name"] == "ماچارتا" and r["followers"] == 257474 and r["videos"] == 584


async def test_channel_videos_latest_and_top(client, api):
    api["/api/fa/v1/user/video/last_videos_more/username/macharta/page/2/perpage/10"] = fixture("channel_latest.json")
    api["/api/fa/v1/user/video/list/username/macharta/type/top/more_type/infinity_btn/page/1/perpage/10"] = fixture(
        "channel_top.json"
    )
    new = (await client.call_tool("apr_channel_videos", {"channel": "macharta", "page": 2})).structured_content
    top = (await client.call_tool("apr_channel_videos", {"channel": "macharta", "sort": "top"})).structured_content
    assert new["videos"] and top["videos"]
    assert top["videos"][0]["views"] >= top["videos"][-1]["views"]


async def test_categories_skip_home_tab(client, api):
    api["/api/fa/v1/etc/page/home_tabs"] = fixture("tabs.json")
    r = (await client.call_tool("apr_categories", {})).structured_content
    assert r["categories"] and "برای شما" not in r["categories"]


async def test_trending_category_and_overall(client, api):
    feed = fixture("trending.json")
    api["/api/fa/v1/video/video/list/tagid/51/slug/سگ و حیوانات"] = feed
    r = (await client.call_tool("apr_trending", {"category": "سگ و حیوانات"})).structured_content
    assert r["videos"]
    for row in feed["data"]:
        row["attributes"]["title"] = {"text": "داغ‌ترین‌ها"}
    api["/api/fa/v1/video/video/list/tagid/1"] = feed
    r = (await client.call_tool("apr_trending", {})).structured_content
    assert r["videos"] and "category" not in r


def test_http_rejects_other_hosts():
    import asyncio

    with pytest.raises(http.ApiError):
        asyncio.run(http.fetch("https://evil.example/x"))
