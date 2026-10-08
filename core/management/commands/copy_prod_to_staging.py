"""Site de test uniquement : remplace la base de test par une copie de la base de production.

Lancé au démarrage du site de test (scripts/entrypoint.prod.sh). Ne fait quelque chose que si
le service de test porte les deux variables :
- STAGING_COPY_FROM_DATABASE_URL : adresse de la base de production (la même que DATABASE_URL
  du vrai service) ;
- STAGING_COPY_REQUEST : un numéro de demande (ex. 1). Chaque demande n'est exécutée qu'une
  fois ; pour recopier plus tard, mettre une autre valeur (2, 3...).

Garanties :
- ne tourne que sur le site de test (STAGING_TEST_SHOP=1) ;
- la production n'est que lue : toute la lecture se fait dans une seule transaction en lecture
  seule (PostgreSQL refuserait toute écriture), qui voit aussi une photo cohérente de la base ;
  et la copie est refusée si la source est la même base que la destination ;
- aucun signal pendant le chargement : pas de notification, pas de livraison créée en double ;
- tout ou rien : si la copie échoue, la base de test reste comme avant ;
- les images (fichiers stockés en base) sont copiées par petits paquets pour tenir en mémoire.
"""
import os
import tempfile
from contextlib import contextmanager

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.core.management.color import no_style
from django.db import connections, transaction
from django.db.models import signals

from core.models import StoredFile

MARKER_TABLE = 'staging_copy_marker'
EXCLUDE = [
    'contenttypes', 'auth.permission', 'sessions', 'admin.logentry',
    'django_celery_results', 'django_celery_beat',
    'core.storedfile',  # copié à part, par paquets
]
FILE_BATCH = 20


@contextmanager
def muted_model_signals():
    """Coupe les signaux des modèles pendant le chargement (notifications, livraisons, commissions...)."""
    sigs = [signals.pre_save, signals.post_save, signals.pre_delete, signals.post_delete, signals.m2m_changed]
    saved = [(sig, sig.receivers) for sig in sigs]
    try:
        for sig in sigs:
            sig.receivers = []
            sig.sender_receivers_cache.clear()
        yield
    finally:
        for sig, receivers in saved:
            sig.receivers = receivers
            sig.sender_receivers_cache.clear()


def _same_database(a, b):
    return (a.get('HOST'), str(a.get('PORT')), a.get('NAME')) == (b.get('HOST'), str(b.get('PORT')), b.get('NAME'))


class Command(BaseCommand):
    help = 'Site de test : remplace la base de test par une copie (lecture seule) de la base de production.'

    def handle(self, *args, **options):
        request_id = (os.environ.get('STAGING_COPY_REQUEST') or '').strip()
        if os.environ.get('STAGING_TEST_SHOP') != '1' or 'source' not in connections.databases or not request_id:
            self.stdout.write('Copie de la production : rien à faire.')
            return
        if _same_database(connections['source'].settings_dict, connections['default'].settings_dict):
            raise CommandError('La source et la destination sont la même base : copie refusée.')

        with connections['default'].cursor() as cursor:
            cursor.execute(
                f'CREATE TABLE IF NOT EXISTS {MARKER_TABLE} '
                '(request varchar(100) PRIMARY KEY, done_at timestamptz NOT NULL DEFAULT now())'
            )
            cursor.execute(f'SELECT 1 FROM {MARKER_TABLE} WHERE request = %s', [request_id])
            if cursor.fetchone():
                self.stdout.write(f'Copie de la production : demande « {request_id} » déjà faite.')
                return

        path = os.path.join(tempfile.gettempdir(), 'gaboshop_prod_copy.json')
        try:
            # Une seule transaction côté production (et non un réglage de session) : derrière un
            # pooler, un réglage de session pourrait rester sur une connexion du vrai site.
            with transaction.atomic(using='source'):
                self._start_read_only_snapshot()
                self.stdout.write('Copie de la production : lecture de la vraie base...')
                call_command('dumpdata', database='source', natural_foreign=True, exclude=EXCLUDE,
                             output=path, verbosity=0)

                # Tout ou rien : en cas d'échec, la base de test reste comme avant.
                self.stdout.write('Copie de la production : remplacement de la base de test...')
                with transaction.atomic(using='default'):
                    call_command('flush', interactive=False, database='default', verbosity=0)
                    with muted_model_signals():
                        call_command('loaddata', path, database='default', verbosity=0)
                        files = self._copy_files()
                    with connections['default'].cursor() as cursor:
                        cursor.execute(f'INSERT INTO {MARKER_TABLE} (request) VALUES (%s)', [request_id])
        finally:
            if os.path.exists(path):
                os.remove(path)
        self.stdout.write(self._summary(files))

    def _start_read_only_snapshot(self):
        """Première instruction de la transaction : lecture seule, photo figée de la base."""
        with connections['source'].cursor() as cursor:
            cursor.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY')
            cursor.execute('SHOW transaction_read_only')
            if cursor.fetchone()[0] != 'on':
                raise CommandError('Impossible de lire la base de production en lecture seule : copie annulée.')

    def _copy_files(self):
        """Images stockées en base : copiées par paquets pour rester dans la mémoire du serveur gratuit."""
        pks = list(StoredFile.objects.using('source').order_by('pk').values_list('pk', flat=True))
        for start in range(0, len(pks), FILE_BATCH):
            with transaction.atomic(using='default'):
                for stored in StoredFile.objects.using('source').filter(pk__in=pks[start:start + FILE_BATCH]):
                    stored.content = bytes(stored.content)
                    # raw=True : comme loaddata, garde la date d'origine (auto_now_add l'écraserait).
                    stored.save_base(raw=True, using='default', force_insert=True)
        sql = connections['default'].ops.sequence_reset_sql(no_style(), [StoredFile])
        if sql:
            with connections['default'].cursor() as cursor:
                for statement in sql:
                    cursor.execute(statement)
        return len(pks)

    def _summary(self, files):
        from orders.models import Order
        from products.models import Product
        from stores.models import Store
        from users.models import User

        return (
            f'Copie de la production terminée : {User.objects.count()} comptes, {Store.objects.count()} commerces, '
            f'{Product.objects.count()} produits, {Order.objects.count()} commandes, {files} images.'
        )
