from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from apps.files.models import Folder
class Command(BaseCommand):
    help = "Create an optional FlowDrive demo account and sample folders"
    def add_arguments(self, parser): parser.add_argument("--password", default="FlowDriveDemo123!")
    def handle(self, *args, **options):
        user, created=get_user_model().objects.get_or_create(username="demo", defaults={"email":"demo@example.com","first_name":"Demo"})
        if created: user.set_password(options["password"]); user.save()
        projects,_=Folder.objects.get_or_create(owner=user,parent=None,name="Projects"); Folder.objects.get_or_create(owner=user,parent=projects,name="Website Redesign"); Folder.objects.get_or_create(owner=user,parent=None,name="Documents"); Folder.objects.get_or_create(owner=user,parent=None,name="Photos")
        self.stdout.write(self.style.SUCCESS(f"Demo ready: username demo / password {options['password']}"))
