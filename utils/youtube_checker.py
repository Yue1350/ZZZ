"""
유튜브는 API 키 없이도 채널별 공개 RSS 피드로 최신 영상을 확인할 수 있습니다.
피드 주소: https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
"""
import aiohttp
import feedparser

RSS_URL = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


async def fetch_latest_video(session: aiohttp.ClientSession, channel_id: str):
    """채널의 가장 최근 영상 (video_id, title, url, channel_name)을 반환. 실패 시 None."""
    url = RSS_URL.format(channel_id=channel_id)
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return None
            text = await resp.text()
    except Exception:
        return None

    feed = feedparser.parse(text)
    if not feed.entries:
        return None

    entry = feed.entries[0]
    video_id = entry.get("yt_videoid") or entry.get("id", "").split(":")[-1]
    title = entry.get("title", "제목 없음")
    link = entry.get("link", f"https://www.youtube.com/watch?v={video_id}")
    channel_name = feed.feed.get("title", "유튜브 채널")

    return {
        "video_id": video_id,
        "title": title,
        "url": link,
        "channel_name": channel_name,
    }


async def resolve_channel_id_from_handle(session: aiohttp.ClientSession, handle_or_url: str):
    """
    '@handle', 채널 URL, 또는 이미 UC로 시작하는 channel_id를 받아서
    channel_id(UCxxxx...)를 최대한 추측해서 반환. 실패 시 None.
    (유튜브가 비공식적으로 channel page HTML에 channelId를 노출하는 것을 이용)
    """
    handle_or_url = handle_or_url.strip()

    if handle_or_url.startswith("UC") and len(handle_or_url) >= 20:
        return handle_or_url

    if handle_or_url.startswith("http"):
        url = handle_or_url
    elif handle_or_url.startswith("@"):
        url = f"https://www.youtube.com/{handle_or_url}"
    else:
        url = f"https://www.youtube.com/@{handle_or_url}"

    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
            if resp.status != 200:
                return None
            html = await resp.text()
    except Exception:
        return None

    marker = '"channelId":"'
    idx = html.find(marker)
    if idx == -1:
        return None
    start = idx + len(marker)
    end = html.find('"', start)
    channel_id = html[start:end]
    if channel_id.startswith("UC"):
        return channel_id
    return None
