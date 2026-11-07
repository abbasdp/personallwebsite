"""Fixture tests for optional sibling ``.fa.md`` posts.

The markdown under the temporary directory is fixture data only.
It is not the Free Software, Free Society essay and it is not a translation.
"""

from __future__ import annotations

import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import app as blog

SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


class CompanionFixtureTests(unittest.TestCase):
    def setUp(self):
        self._posts_dir = blog.POSTS_DIR
        self._tmp = tempfile.TemporaryDirectory()
        blog.POSTS_DIR = Path(self._tmp.name)
        blog.app.config["TESTING"] = True
        self.client = blog.app.test_client()
        _write(
            blog.POSTS_DIR / "fixture-alpha.md",
            """---
title: FIXTURE-ALPHA-TITLE
date: 2020-01-03
summary: FIXTURE-ALPHA-SUMMARY
tags: fixture
---

FIXTURE-ALPHA-BODY. Not a published post.
""",
        )
        _write(
            blog.POSTS_DIR / "fixture-beta.md",
            """---
title: FIXTURE-EN-TITLE
date: 2020-01-02
dir: ltr
summary: FIXTURE-EN-SUMMARY
tags: fixture
source: https://example.invalid/fixture-only
---

FIXTURE-EN-BODY. Original English fixture, not a real essay.
""",
        )
        _write(
            blog.POSTS_DIR / "fixture-beta.fa.md",
            """---
title: FIXTURE-FA-TITLE
date: 1999-01-01
summary: FIXTURE-FA-SUMMARY
---

FIXTURE-FA-BODY. Fixture Persian text, not a real translation.
""",
        )
        _write(
            blog.POSTS_DIR / "fixture-orphan.fa.md",
            """---
title: FIXTURE-ORPHAN-TITLE
date: 2020-06-01
---

FIXTURE-ORPHAN-BODY. Must not be listed.
""",
        )

    def tearDown(self):
        blog.POSTS_DIR = self._posts_dir
        self._tmp.cleanup()

    def test_companion_present_keeps_english_and_offers_persian_toggle(self):
        res = self.client.get("/posts/fixture-beta")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn("<h1 class=\"article__title\">FIXTURE-EN-TITLE</h1>", html)
        self.assertIn("FIXTURE-EN-SUMMARY", html)
        self.assertIn("FIXTURE-EN-BODY", html)
        self.assertIn('dir="ltr" lang="en"', html)
        self.assertIn('rel="canonical" href="https://abbasdp.ir/posts/fixture-beta"', html)
        self.assertIn('property="og:url" content="https://abbasdp.ir/posts/fixture-beta"', html)
        self.assertIn('property="og:locale" content="en_US"', html)
        self.assertIn('"inLanguage": "en"', html)
        self.assertNotIn("fixture-beta.fa", html)

        fa_start = html.index('<details class="article-fa"')
        fa_end = html.index("</details>", fa_start)
        fa_html = html[fa_start:fa_end]
        english_after = html[fa_end:]
        self.assertIn('dir="ltr"', html[fa_start:html.index(">", fa_start) + 1])
        self.assertNotIn(" open", html[fa_start:html.index(">", fa_start) + 1])
        self.assertIn("نمایش ترجمهٔ فارسی", fa_html)
        self.assertIn(">Persian<", fa_html)
        self.assertIn('lang="fa" dir="rtl"', fa_html)
        self.assertIn("FIXTURE-FA-TITLE", fa_html)
        self.assertIn("FIXTURE-FA-BODY", fa_html)
        self.assertNotIn("FIXTURE-EN-BODY", fa_html)
        self.assertIn("FIXTURE-EN-BODY", english_after)
        self.assertNotIn("<h1 class=\"article__title\">FIXTURE-FA-TITLE</h1>", html)

    def test_companion_absent_has_no_toggle(self):
        res = self.client.get("/posts/fixture-alpha")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("FIXTURE-ALPHA-BODY", html)
        self.assertNotIn("article-fa", html)
        self.assertNotIn("نمایش ترجمهٔ فارسی", html)
        self.assertNotIn("FIXTURE-FA-BODY", html)
        self.assertIn('rel="canonical" href="https://abbasdp.ir/posts/fixture-alpha"', html)

    def test_companion_urls_redirect_to_canonical_english_post(self):
        res = self.client.get("/posts/fixture-beta.fa?from=fixture")
        self.assertEqual(res.status_code, 301)
        self.assertEqual(
            res.headers["Location"],
            "https://abbasdp.ir/posts/fixture-beta?from=fixture",
        )
        root = self.client.get("/fixture-beta.fa")
        self.assertEqual(root.status_code, 301)
        self.assertEqual(root.headers["Location"], "https://abbasdp.ir/posts/fixture-beta")
        missing = self.client.get("/posts/fixture-orphan.fa")
        self.assertEqual(missing.status_code, 404)
        self.assertIsNotNone(blog.read_post_raw("fixture-beta"))
        self.assertIsNone(blog.read_post_raw("fixture-beta.fa"))
        self.assertEqual(blog.read_post_raw("fixture-beta")["title"], "FIXTURE-EN-TITLE")

    def test_listings_sitemap_feed_and_api_skip_companions(self):
        posts = blog.load_posts()
        slugs = [post["slug"] for post in posts]
        self.assertEqual(slugs, ["fixture-alpha", "fixture-beta"])
        self.assertEqual(slugs.count("fixture-beta"), 1)

        listing = self.client.get("/posts").get_data(as_text=True)
        home = self.client.get("/").get_data(as_text=True)
        for page in (listing, home):
            self.assertEqual(page.count('href="/posts/fixture-beta"'), 1)
            self.assertEqual(page.count('href="/posts/fixture-alpha"'), 1)
            self.assertNotIn("fixture-beta.fa", page)
            self.assertNotIn("fixture-orphan", page)
            self.assertNotIn("FIXTURE-FA-TITLE", page)
            self.assertNotIn("FIXTURE-ORPHAN-TITLE", page)
            self.assertIn("FIXTURE-EN-TITLE", page)

        beta_card = listing.split('href="/posts/fixture-beta"', 1)[1][:700]
        alpha_card = listing.split('href="/posts/fixture-alpha"', 1)[1][:500]
        self.assertIn('class="post-card__title" dir="ltr" lang="en"', beta_card)
        self.assertIn('class="post-card__summary" dir="ltr" lang="en"', beta_card)
        self.assertNotIn('dir="ltr"', alpha_card)
        self.assertIn('dir="ltr" lang="en"', home.split('href="/posts/fixture-beta"', 1)[1][:700])
        self.assertNotIn('dir="ltr"', home.split('href="/posts/fixture-alpha"', 1)[1][:500])

        sitemap = self.client.get("/sitemap.xml")
        self.assertEqual(sitemap.status_code, 200)
        root = ET.fromstring(sitemap.get_data(as_text=True))
        locs = [node.text for node in root.findall("sm:url/sm:loc", SITEMAP_NS)]
        self.assertEqual(locs.count("https://abbasdp.ir/posts/fixture-beta"), 1)
        self.assertEqual(locs.count("https://abbasdp.ir/posts/fixture-alpha"), 1)
        self.assertTrue(all(not loc.endswith(".fa") for loc in locs))
        self.assertNotIn("fixture-orphan", sitemap.get_data(as_text=True))

        feed = self.client.get("/feed.xml").get_data(as_text=True)
        self.assertEqual(feed.count("<link>https://abbasdp.ir/posts/fixture-beta</link>"), 1)
        self.assertEqual(feed.count("<guid>https://abbasdp.ir/posts/fixture-beta</guid>"), 1)
        self.assertNotIn("fixture-beta.fa", feed)
        self.assertNotIn("FIXTURE-FA-TITLE", feed)
        self.assertNotIn("FIXTURE-ORPHAN", feed)
        self.assertIn("FIXTURE-EN-TITLE", feed)

        payload = self.client.get("/api/posts").get_json()
        self.assertEqual([item["slug"] for item in payload], ["fixture-alpha", "fixture-beta"])
        self.assertTrue(all("html" not in item and "fa" not in item for item in payload))
        self.assertNotIn("FIXTURE-FA-BODY", str(payload))


class ShippedContentTests(unittest.TestCase):
    """The committed posts stay as they are. No fixture files are written here."""

    def setUp(self):
        blog.app.config["TESTING"] = True
        self.client = blog.app.test_client()

    def test_existing_posts_keep_canonical_urls_and_optional_toggle(self):
        primaries = [
            path for path in blog.POSTS_DIR.glob("*.md")
            if path.is_file() and not path.name.endswith(".fa.md")
        ]
        self.assertGreaterEqual(len(primaries), 1)
        posts = blog.load_posts()
        self.assertEqual(
            sorted(post["slug"] for post in posts),
            sorted(path.stem for path in primaries),
        )
        self.assertEqual(len(posts), len({post["slug"] for post in posts}))

        sitemap = self.client.get("/sitemap.xml").get_data(as_text=True)
        root = ET.fromstring(sitemap)
        locs = [node.text for node in root.findall("sm:url/sm:loc", SITEMAP_NS)]
        post_locs = [loc for loc in locs if "/posts/" in loc]
        self.assertEqual(
            sorted(post_locs),
            sorted(f"https://abbasdp.ir/posts/{post['slug']}" for post in posts),
        )
        self.assertTrue(all(not loc.endswith(".fa") for loc in locs))
        listing = self.client.get("/posts").get_data(as_text=True)
        english_card = listing.split('href="/posts/deltachat-relay-iran-internet"', 1)[1][:800]
        persian_card = listing.split('href="/posts/whoami"', 1)[1][:500]
        self.assertIn('class="post-card__title" dir="ltr" lang="en"', english_card)
        self.assertNotIn('dir="ltr"', persian_card)

        for post in posts:
            res = self.client.get(f"/posts/{post['slug']}")
            self.assertEqual(res.status_code, 200, post["slug"])
            html = res.get_data(as_text=True)
            self.assertIn(
                f'rel="canonical" href="https://abbasdp.ir/posts/{post["slug"]}"',
                html,
            )
            self.assertIn(post["title"], html)
            if post["dir"] == "ltr":
                self.assertIn('dir="ltr" lang="en"', html)
            companion = blog.POSTS_DIR / f"{post['slug']}.fa.md"
            if companion.is_file():
                self.assertIn("نمایش ترجمهٔ فارسی", html)
            else:
                self.assertNotIn("article-fa", html)
                self.assertNotIn("نمایش ترجمهٔ فارسی", html)

        legacy = self.client.get("/fingercoder-chetor-shekl-gereft")
        self.assertEqual(legacy.status_code, 301)
        self.assertEqual(
            legacy.headers["Location"],
            "https://abbasdp.ir/posts/sheklgiri-fingercoder",
        )
        gone = self.client.get("/jmaah-nrmfzr-azd-shyrzlynwkhs")
        self.assertEqual(gone.status_code, 410)
        http = self.client.get("/posts/whoami", base_url="http://abbasdp.ir")
        self.assertEqual(http.status_code, 301)
        self.assertEqual(http.headers["Location"], "https://abbasdp.ir/posts/whoami")
        probe = self.client.get("/healthz", base_url="http://abbasdp.ir")
        self.assertEqual(probe.status_code, 200)
        bandali = self.client.get("/posts/bandali").get_data(as_text=True)
        self.assertIn("https://tubedu.org/videos/embed/nudTkw32nKN6kjpwkrmoUV", bandali)
        self.assertIn("ویدیوی ارائه من و امین بندعلی", bandali)
        install = self.client.get("/posts/install-party-deltachat").get_data(as_text=True)
        self.assertIn('dir="ltr" lang="en"', install)


if __name__ == "__main__":
    unittest.main()
