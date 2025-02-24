import os
import shutil
from django.core.management.base import BaseCommand, CommandError
from event.models import EventPosterTemplate
from django.conf import settings


class Command(BaseCommand):
    help = "Move an HTML file to 'poster/' and create an EventPosterTemplate instance."

    def add_arguments(self, parser):
        parser.add_argument("title", type=str, help="Title of the template (max 10 chars)")
        parser.add_argument("html_file_path", type=str, help="Path to the HTML file")

    def handle(self, *args, **options):
        title = options["title"]
        html_file_path = options["html_file_path"]

        # Validate title length
        if len(title) > 10:
            raise CommandError("Title must be 10 characters or less.")

        # Define the destination directory and filename
        poster_dir = os.path.join(settings.BASE_DIR, "event", "templates", "event", "poster")
        os.makedirs(poster_dir, exist_ok=True)  # Ensure directory exists
        destination_file = os.path.join(poster_dir, f"{title}.html")

        # Check if the file exists
        if not os.path.exists(html_file_path):
            raise CommandError(f"File not found: {html_file_path}")

        # Move the file
        shutil.move(html_file_path, destination_file)

        # Create a new EventPosterTemplate instance
        template, created = EventPosterTemplate.objects.get_or_create(
            title=title, defaults={"html_file": f"{title}.html"}
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f"Template '{title}' created successfully."))
        else:
            self.stdout.write(self.style.WARNING(f"Template '{title}' already exists. File moved but not recreated."))
