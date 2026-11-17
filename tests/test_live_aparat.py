import pytest

pytestmark = [pytest.mark.live, pytest.mark.anyio]


async def test_live_search_video_comments_related(client):
    r = (await client.call_tool("apr_search", {"query": "آشپزی"})).structured_content
    assert r["videos"] and r["channels"]
    uid = r["videos"][0]["uid"]
    v = (await client.call_tool("apr_video", {"video": uid})).structured_content
    assert v["title"] and v["views"] > 0 and v["channel"]["username"]
    assert "comments" in (await client.call_tool("apr_comments", {"video": uid})).structured_content
    assert (await client.call_tool("apr_related", {"video": uid})).structured_content["videos"]


async def test_live_channel_and_videos(client):
    c = (await client.call_tool("apr_channel", {"channel": "macharta"})).structured_content
    assert c["followers"] > 1000 and c["videos"] > 100
    for sort in ("latest", "top"):
        r = (await client.call_tool("apr_channel_videos", {"channel": "macharta", "sort": sort})).structured_content
        assert (
            len(r["videos"]) == 10 and sum(v["channel"] == "macharta" for v in r["videos"]) >= 8
        )  # feed may mix in a partner channel


async def test_live_trending(client):
    cats = (await client.call_tool("apr_categories", {})).structured_content["categories"]
    assert len(cats) > 10
    assert (await client.call_tool("apr_trending", {"category": cats[0]})).structured_content["videos"]
    assert (await client.call_tool("apr_trending", {})).structured_content["videos"]
