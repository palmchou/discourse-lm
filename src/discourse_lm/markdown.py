from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser
from datetime import datetime
from pathlib import Path
from typing import Any

EMOJI_IMAGE_RE = re.compile(r'<img[^>]*class="[^"]*emoji[^"]*"[^>]*(?:title|alt)="([^"]+)"[^>]*>', re.IGNORECASE)


class SimpleMarkdownHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.link_stack: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        if tag in {"p", "div", "section"}:
            self.parts.append("\n\n")
        elif tag == "br":
            self.parts.append("\n")
        elif tag in {"ul", "ol"}:
            self.parts.append("\n")
        elif tag == "li":
            self.parts.append("\n- ")
        elif tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag == "code":
            self.parts.append("`")
        elif tag == "blockquote":
            self.parts.append("\n> ")
        elif tag == "a":
            self.link_stack.append(attr_map.get("href"))
        elif tag == "img":
            replacement = attr_map.get("title") or attr_map.get("alt")
            if replacement:
                self.parts.append(replacement)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"strong", "b"}:
            self.parts.append("**")
        elif tag in {"em", "i"}:
            self.parts.append("*")
        elif tag == "code":
            self.parts.append("`")
        elif tag == "a":
            href = self.link_stack.pop() if self.link_stack else None
            if href:
                self.parts.append(f" ({href})")
        elif tag in {"p", "div", "section", "blockquote"}:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data:
            self.parts.append(unescape(data))

    def markdown(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def simplify_emoji_images(html_content: str) -> str:
    if not html_content:
        return html_content
    return EMOJI_IMAGE_RE.sub(lambda match: match.group(1), html_content)


def cooked_to_markdown(html_content: str) -> str:
    if not html_content:
        return ""
    html_content = simplify_emoji_images(html_content)
    parser = SimpleMarkdownHTMLParser()
    parser.feed(html_content)
    parser.close()
    return parser.markdown()


def format_datetime(value: str | None) -> str:
    if not value:
        return "N/A"
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    return timestamp.strftime("%Y-%m-%d %H:%M UTC")


def format_reactions(reactions: list[dict[str, Any]]) -> str:
    parts = []
    for reaction in reactions or []:
        count = reaction.get("count", 0)
        if count > 0:
            parts.append(f":{reaction.get('id', '?')}: x{count}")
    return ", ".join(parts) if parts else "None"


def get_role_badges(post: dict[str, Any]) -> str:
    badges = []
    if post.get("admin"):
        badges.append("Admin")
    if post.get("moderator"):
        badges.append("Moderator")
    if post.get("staff"):
        badges.append("Staff")
    if post.get("wiki"):
        badges.append("Wiki")
    if post.get("accepted_answer"):
        badges.append("Accepted Answer")
    trust_level = post.get("trust_level")
    if trust_level is not None:
        badges.append(f"TL{trust_level}")
    return " · ".join(badges)


def extract_topic_metadata(data: dict[str, Any]) -> dict[str, Any]:
    details = data.get("details", {})
    created_by = details.get("created_by", {})
    last_poster = details.get("last_poster", {})
    tags = data.get("tags", [])
    tag_names = [tag["name"] for tag in tags if isinstance(tag, dict) and "name" in tag]
    return {
        "id": data.get("id"),
        "title": data.get("title", "Untitled Topic"),
        "tags": ", ".join(tag_names) if tag_names else "None",
        "posts_count": data.get("posts_count", 0),
        "created_at": format_datetime(data.get("created_at")),
        "last_posted_at": format_datetime(data.get("last_posted_at")),
        "views": data.get("views", 0),
        "reply_count": data.get("reply_count", 0),
        "like_count": data.get("like_count", 0),
        "word_count": data.get("word_count", 0),
        "participant_count": data.get("participant_count", 0),
        "closed": data.get("closed", False),
        "archived": data.get("archived", False),
        "category_id": data.get("category_id"),
        "created_by_username": created_by.get("username", "unknown"),
        "created_by_name": created_by.get("name", ""),
        "last_poster_username": last_poster.get("username", "unknown"),
        "last_poster_name": last_poster.get("name", ""),
    }


def extract_posts(data: dict[str, Any]) -> list[dict[str, Any]]:
    posts = []
    for post in data.get("post_stream", {}).get("posts", []):
        reply_to_user = post.get("reply_to_user", {})
        posts.append(
            {
                "id": post.get("id"),
                "username": post.get("username", "unknown"),
                "name": post.get("name", ""),
                "created_at": format_datetime(post.get("created_at")),
                "updated_at": format_datetime(post.get("updated_at")),
                "content": cooked_to_markdown(post.get("cooked", "")),
                "post_number": post.get("post_number"),
                "reply_count": post.get("reply_count", 0),
                "reply_to_post_number": post.get("reply_to_post_number"),
                "reads": post.get("reads", 0),
                "trust_level": post.get("trust_level"),
                "role_badges": get_role_badges(post),
                "reactions": format_reactions(post.get("reactions", [])),
                "reply_to_username": reply_to_user.get("username", ""),
            }
        )

    content_by_post_number = {post["post_number"]: post["content"] for post in posts}
    for post in posts:
        reference = post.get("reply_to_post_number")
        snippet = content_by_post_number.get(reference, "").replace("\n", " ").strip()
        if len(snippet) > 200:
            snippet = f"{snippet[:200].rstrip()}..."
        post["reply_to_quote"] = snippet
    return posts


def render_markdown(topic_data: dict[str, Any], posts: list[dict[str, Any]], chunk_info: dict[str, Any] | None = None) -> str:
    lines = [
        f"# {topic_data['title']}",
        "",
        "## Topic Overview",
        "",
        "| Property | Value |",
        "|---|---|",
        f"| Topic ID | {topic_data['id']} |",
        f"| Created | {topic_data['created_at']} |",
        f"| Last Active | {topic_data['last_posted_at']} |",
        (
            f"| Author | @{topic_data['created_by_username']}"
            f"{f' ({topic_data['created_by_name']})' if topic_data['created_by_name'] else ''} |"
        ),
        (
            f"| Last Poster | @{topic_data['last_poster_username']}"
            f"{f' ({topic_data['last_poster_name']})' if topic_data['last_poster_name'] else ''} |"
        ),
        f"| Tags | {topic_data['tags']} |",
        f"| Category ID | {topic_data['category_id']} |",
        (
            f"| Status | {'Closed' if topic_data['closed'] else 'Archived' if topic_data['archived'] else 'Open'} |"
        ),
        "",
        "### Engagement",
        "",
        "| Metric | Count |",
        "|---|---|",
        f"| Total Posts | {topic_data['posts_count']} |",
        f"| Views | {topic_data['views']} |",
        f"| Replies | {topic_data['reply_count']} |",
        f"| Likes | {topic_data['like_count']} |",
        f"| Participants | {topic_data['participant_count']} |",
        f"| Word Count | {topic_data['word_count']} |",
        "",
    ]
    if chunk_info:
        lines.extend(
            [
                f"> Part {chunk_info['current']} of {chunk_info['total']}. "
                f"Posts {chunk_info['start_post']}-{chunk_info['end_post']}.",
                "",
            ]
        )
    lines.extend(["## Posts", ""])

    for post in posts:
        lines.append(
            f"### Post #{post['post_number']} by @{post['username']}"
            f"{f' ({post['name']})' if post['name'] else ''}"
        )
        lines.append("")
        date_line = f"- Date: {post['created_at']}"
        if post["created_at"] != post["updated_at"]:
            date_line += f" (edited: {post['updated_at']})"
        lines.append(date_line)
        lines.append(f"- Reads: {post['reads']}")
        lines.append(f"- Replies: {post['reply_count']}")
        if post["reactions"] != "None":
            lines.append(f"- Reactions: {post['reactions']}")
        if post["role_badges"]:
            lines.append(f"- Badges: {post['role_badges']}")
        lines.append("")
        if post["reply_to_post_number"]:
            reply = f"> Replying to post #{post['reply_to_post_number']}"
            if post["reply_to_username"]:
                reply += f" by @{post['reply_to_username']}"
            lines.append(reply)
            if post["reply_to_quote"]:
                lines.append(">")
                lines.append(f"> {post['reply_to_quote']}")
            lines.append("")
        lines.append(post["content"])
        lines.extend(["", "---", ""])

    lines.append(f"Generated from Discourse API data on {datetime.now().strftime('%Y-%m-%d %H:%M')}.")
    lines.append("")
    return "\n".join(lines)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "topic"


def write_markdown_files(
    topic_payload: dict[str, Any],
    output_base: str | Path,
    chunk_size: int = 2000,
    num_chunks: int = 0,
) -> list[Path]:
    topic = extract_topic_metadata(topic_payload)
    posts = extract_posts(topic_payload)
    output_root = Path(output_base).with_suffix("")
    output_root.parent.mkdir(parents=True, exist_ok=True)

    if chunk_size <= 0 or len(posts) <= chunk_size:
        output_file = output_root.with_suffix(".md")
        output_file.write_text(render_markdown(topic, posts), encoding="utf-8")
        return [output_file]

    chunks = [posts[index : index + chunk_size] for index in range(0, len(posts), chunk_size)]
    limit = min(num_chunks, len(chunks)) if num_chunks > 0 else len(chunks)
    files = []
    for index, chunk in enumerate(chunks[:limit], start=1):
        chunk_info = {
            "current": index,
            "total": len(chunks),
            "start_post": chunk[0]["post_number"],
            "end_post": chunk[-1]["post_number"],
        }
        output_file = Path(f"{output_root}_part{index}.md")
        output_file.write_text(render_markdown(topic, chunk, chunk_info=chunk_info), encoding="utf-8")
        files.append(output_file)
    return files


def load_topic_payload(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))
