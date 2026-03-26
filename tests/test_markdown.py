import tempfile
import unittest
from pathlib import Path

from discourse_lm.markdown import slugify, write_markdown_files


class MarkdownTests(unittest.TestCase):
    def test_slugify_falls_back_for_empty_values(self):
        self.assertEqual(slugify("!!!"), "topic")

    def test_write_markdown_files_chunks(self):
        payload = {
            "id": 42,
            "title": "Chunk me",
            "posts_count": 3,
            "post_stream": {
                "posts": [
                    {
                        "id": 1,
                        "post_number": 1,
                        "username": "alice",
                        "created_at": "2026-03-25T00:00:00Z",
                        "updated_at": "2026-03-25T00:00:00Z",
                        "cooked": "<p>Hello</p>",
                        "reply_count": 0,
                        "reads": 1,
                        "reactions": [],
                    },
                    {
                        "id": 2,
                        "post_number": 2,
                        "username": "bob",
                        "created_at": "2026-03-25T00:01:00Z",
                        "updated_at": "2026-03-25T00:01:00Z",
                        "cooked": "<p>Hi</p>",
                        "reply_count": 0,
                        "reads": 1,
                        "reactions": [],
                    },
                    {
                        "id": 3,
                        "post_number": 3,
                        "username": "carol",
                        "created_at": "2026-03-25T00:02:00Z",
                        "updated_at": "2026-03-25T00:02:00Z",
                        "cooked": "<p>Bye</p>",
                        "reply_count": 0,
                        "reads": 1,
                        "reactions": [],
                    },
                ]
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            outputs = write_markdown_files(payload, Path(temp_dir) / "topic", chunk_size=2)
        self.assertEqual(len(outputs), 2)
        self.assertEqual(outputs[0].name, "topic_part1.md")
        self.assertEqual(outputs[1].name, "topic_part2.md")


if __name__ == "__main__":
    unittest.main()
