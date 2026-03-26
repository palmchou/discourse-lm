import unittest

from discourse_lm.discourse import DiscourseError, parse_discourse_topic_url


class ParseDiscourseTopicUrlTests(unittest.TestCase):
    def test_parse_slugged_topic_url(self):
        topic = parse_discourse_topic_url("https://meta.discourse.org/t/test-topic/12345")
        self.assertEqual(topic.base_url, "https://meta.discourse.org")
        self.assertEqual(topic.slug, "test-topic")
        self.assertEqual(topic.topic_id, "12345")

    def test_parse_unslugged_topic_url(self):
        topic = parse_discourse_topic_url("https://meta.discourse.org/t/12345")
        self.assertEqual(topic.base_url, "https://meta.discourse.org")
        self.assertIsNone(topic.slug)
        self.assertEqual(topic.topic_id, "12345")

    def test_invalid_topic_url_raises(self):
        with self.assertRaises(DiscourseError):
            parse_discourse_topic_url("https://example.com/not-a-topic")


if __name__ == "__main__":
    unittest.main()
