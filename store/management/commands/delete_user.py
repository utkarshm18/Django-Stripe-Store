from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Delete a user by username or ID'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Username to delete')
        parser.add_argument('--id', type=int, help='User ID to delete')
        parser.add_argument('--all', action='store_true', help='Delete all users (except superuser)')

    def handle(self, *args, **options):
        if options['all']:
            # Delete all users except superusers
            users = User.objects.filter(is_superuser=False)
            count = users.count()
            users.delete()
            self.stdout.write(self.style.SUCCESS(f'Deleted {count} non-superuser users'))
            return
        
        if options['username']:
            try:
                user = User.objects.get(username=options['username'])
                username = user.username
                user.delete()
                self.stdout.write(self.style.SUCCESS(f'Deleted user: {username}'))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User "{options["username"]}" not found'))
        
        elif options['id']:
            try:
                user = User.objects.get(id=options['id'])
                username = user.username
                user.delete()
                self.stdout.write(self.style.SUCCESS(f'Deleted user ID {options["id"]}: {username}'))
            except User.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'User with ID {options["id"]} not found'))
        else:
            self.stdout.write(self.style.ERROR('Please provide --username, --id, or --all'))

