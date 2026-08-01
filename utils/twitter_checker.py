"""
Nitter(트위터 미러) 인스턴스의 RSS 피드로 특정 계정의 최신 트윗을 가져옵니다.
공식 X API 없이 동작하지만, Nitter 인스턴스들이 자주 막히거나 다운되기 때문에
여러 인스턴스를 순서대로 시도하고, 응답이 느리거나 실패하는 인스턴스는
자동으로 뒤로 밀려나도록 만들었습니다.

RSS 주소 형식: https://{instance}/{username}/rss
"""
import re
import xml.etree.ElementTree as ET

import aiohttp

from config import NITTER_INSTANCES

# 응답 실패한 인스턴스는 잠깐 뒤로 밀어서 다음 시도부터는 우선순위를 낮춤
_instance_order = list(NITTER_INSTANCES)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}


def is_configured() -> bool:
    return len(_instance_order) > 0


def _demote_instance(instance: str):
    if instance in _instance_order:
        _instance_order.remove(instance)
        _instance_order.append(instance)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


async def fetch_latest_tweet(session: aiohttp.ClientSession, username: str):
    """username(@ 없이)의 가장 최근 트윗(리트윗 제외)을 반환. 모든 인스턴스 실패 시 None."""
    username = username.lstrip("@").strip()

    for instance in list(_instance_order):
        url = f"https://{instance}/{username}/rss"
        try:
            async with session.get(
                url, headers=_HEADERS, timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    _demote_instance(instance)
                    continue
                body = await resp.text()
        except Exception:
            _demote_instance(instance)
            continue

        try:
            root = ET.fromstring(body)
        except ET.ParseError:
            _demote_instance(instance)
            continue

        items = root.findall("./channel/item")
        if not items:
            # 계정이 없거나 비공개일 수도 있고, 인스턴스가 빈 응답을 줬을 수도 있음
            continue

        for item in items:
            title = item.findtext("title") or ""
            if title.startswith("RT by"):
                continue  # 리트윗은 건너뛰기

            link = item.findtext("link") or ""
            guid = item.findtext("guid") or link
            tweet_id_match = re.search(r"/status/(\d+)", guid) or re.search(r"/status/(\d+)", link)
            if not tweet_id_match:
                continue
            tweet_id = tweet_id_match.group(1)

            text = _strip_html(title)
            real_url = f"https://twitter.com/{username}/status/{tweet_id}"

            return {
                "tweet_id": tweet_id,
                "text": text,
                "url": real_url,
            }

        # item은 있었지만 전부 리트윗이라 건너뛴 경우
        return None

    return None
