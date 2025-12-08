from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = 'Start Celery worker and beat together'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Starting Celery services...'))
        
        # Démarrer le worker
        self.stdout.write('🤖 Starting Celery worker...')
        call_command('celery', 'worker', '--loglevel=info')
        
        # Démarrer beat (dans un terminal séparé en production)
        self.stdout.write('⏰ Starting Celery beat...')
        call_command('celery', 'beat', '--loglevel=info')
