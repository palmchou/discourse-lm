from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "X-Requested-With": "XMLHttpRequest",
}
MAX_RETRIES = 3
CHUNK_SIZE = 20


class DiscourseError(RuntimeError):
    """Raised when a Discourse topic cannot be processed."""


@dataclass(frozen=True)
class TopicRef:
    base_url: str
    topic_id: str
    slug: str | None = None

    @property
    def topic_json_url(self) -> str:
        return f"{self.base_url}/t/{self.topic_id}.json"

    @property
    def posts_json_url(self) -> str:
        return f"{self.base_url}/t/{self.topic_id}/posts.json"


def parse_discourse_topic_url(url: str) -> TopicRef:
    """Extract base URL, topic ID, and optional slug from a Discourse topic URL."""
    match = re.search(r"^(https?://[^/]+)/t/(?:([^/?#]+)/)?(\d+)", url.strip())
    if not match:
        raise DiscourseError(f"Invalid Discourse topic URL: {url}")
    return TopicRef(
        base_url=match.group(1),
        slug=match.group(2),
        topic_id=match.group(3),
    )


def _safe_request(url: str, params: dict[str, Any] | None = None) -> Any:
    if params:
        query_string = urllib.parse.urlencode(params, doseq=True)
        query_string = query_string.replace("post_ids=", "post_ids[]=")
        url = f"{url}?{query_string}"

    for attempt in range(MAX_RETRIES):
        try:
            headers = HEADERS.copy()
            headers["Referer"] = url.split(".json")[0]
            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt < MAX_RETRIES - 1:
                retry_after = exc.headers.get("Retry-After")
                wait_time = float(retry_after) if retry_after else 3 + attempt
                time.sleep(wait_time)
                continue
            raise DiscourseError(f"HTTP {exc.code}: {exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise DiscourseError(f"Network error fetching Discourse topic: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise DiscourseError(f"Invalid JSON returned by Discourse: {exc}") from exc

    raise DiscourseError("Exceeded retry budget while fetching topic")


def fetch_topic(topic_url: str, chunk_size: int = CHUNK_SIZE, sleep_seconds: float = 1.0) -> dict[str, Any]:
    """Fetch a full Discourse topic payload, including paginated posts."""
    topic = parse_discourse_topic_url(topic_url)
    initial_data = _safe_request(topic.topic_json_url)

    all_posts = list(initial_data.get("post_stream", {}).get("posts", []))
    stream_ids = initial_data.get("post_stream", {}).get("stream", [])
    fetched_ids = {post["id"] for post in all_posts}
    remaining_ids = [post_id for post_id in stream_ids if post_id not in fetched_ids]

    for offset in range(0, len(remaining_ids), chunk_size):
        chunk = remaining_ids[offset : offset + chunk_size]
        chunk_data = _safe_request(topic.posts_json_url, params={"post_ids": chunk})
        chunk_posts = chunk_data.get("post_stream", {}).get("posts", [])
        all_posts.extend(chunk_posts)
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    initial_data.setdefault("post_stream", {})
    initial_data["post_stream"]["posts"] = sorted(
        all_posts,
        key=lambda post: post.get("post_number", 0),
    )
    return initial_data


def save_topic_json(topic_data: dict[str, Any], output_path: str | Path) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(topic_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output
