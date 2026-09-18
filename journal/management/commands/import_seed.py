import json
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.utils.text import slugify

from journal.models import Post, SiteSettings, Tag


class Command(BaseCommand):
    help = "Import seed posts, media and site settings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-if-exists",
            action="store_true",
            help="Do nothing if any post already exists",
        )
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **opts):
        if opts["skip_if_exists"] and Post.objects.exists():
            self.stdout.write("posts exist, skip")
            return

        seed = Path(settings.BASE_DIR) / "journal" / "seed"
        payload = json.loads((seed / "posts.json").read_text(encoding="utf-8"))
        media_root = Path(settings.MEDIA_ROOT)
        media_root.mkdir(parents=True, exist_ok=True)

        src_media = seed / "media"
        if src_media.exists():
            for item in src_media.rglob("*"):
                if not item.is_file():
                    continue
                dest = media_root / item.relative_to(src_media)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if opts["force"] or not dest.exists():
                    shutil.copy2(item, dest)

        SiteSettings.load()

        if opts["force"]:
            Post.objects.all().delete()

        for item in payload:
            tag_objs = []
            for tag in item.get("tags") or []:
                if isinstance(tag, str):
                    name, slug = tag, slugify(tag, allow_unicode=True) or "tag"
                else:
                    name, slug = tag["name"], tag["slug"]
                obj, _ = Tag.objects.get_or_create(slug=slug, defaults={"name": name})
                if obj.name != name:
                    obj.name = name
                    obj.save(update_fields=["name"])
                tag_objs.append(obj)

            body = (seed / "html" / item["html"]).read_text(encoding="utf-8")
            published_at = datetime.fromisoformat(item["published_at"])
            if timezone.is_naive(published_at):
                published_at = timezone.make_aware(published_at)

            post, created = Post.objects.update_or_create(
                slug=item["slug"],
                defaults={
                    "title": item["title"],
                    "excerpt": item.get("excerpt") or "",
                    "body": body,
                    "cover_alt": item.get("cover_alt") or "",
                    "cover_caption": item.get("cover_caption") or "",
                    "published": item.get("published", False),
                    "featured": item.get("featured", False),
                    "published_at": published_at,
                },
            )
            post.tags.set(tag_objs)

            cover = item.get("cover")
            if cover:
                path = media_root / cover
                if path.exists():
                    with path.open("rb") as fh:
                        post.cover.save(Path(cover).name, File(fh), save=True)

            self.stdout.write(f"{'created' if created else 'updated'} {post.slug}")
