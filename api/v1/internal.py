"""Minuteur des tâches automatiques et page « santé » de l'API."""
import hmac
from datetime import timedelta

from django.conf import settings
from django.db import connection
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView


class SchedulerTickView(APIView):
	"""POST /api/v1/internal/tick/ : appelé par le minuteur GitHub avec l'en-tête X-Cron-Token (= CRON_TOKEN)."""
	permission_classes = [permissions.AllowAny]
	authentication_classes = []
	throttle_classes = []

	def post(self, request):
		expected = getattr(settings, 'CRON_TOKEN', '')
		if not expected:
			return Response({'success': False, 'error': {'code': 503, 'message': 'Minuteur non configuré (CRON_TOKEN absent).'}},
				status=status.HTTP_503_SERVICE_UNAVAILABLE)
		given = request.headers.get('X-Cron-Token', '')
		if not hmac.compare_digest(given.encode(), expected.encode()):
			return Response({'success': False, 'error': {'code': 403, 'message': 'Accès refusé.'}}, status=status.HTTP_403_FORBIDDEN)
		from core.scheduled import run_due_jobs
		return Response({'success': True, 'data': run_due_jobs()})


class HealthView(APIView):
	"""GET /api/v1/health/ : état de l'API sans aucune donnée privée (base, minuteur, commandes bloquées)."""
	permission_classes = [permissions.AllowAny]
	authentication_classes = []

	def get(self, request):
		from core.models import ScheduledTaskRun
		from orders.models import Order
		from payments.models import Payment

		try:
			with connection.cursor() as cursor:
				cursor.execute('SELECT 1')
			database = True
		except Exception:
			return Response({'success': False, 'data': {'database': False}}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

		now = timezone.now()
		jobs = {
			run.name: {'last_run_at': run.last_run_at, 'ok': run.last_ok, 'message': run.last_message[:200]}
			for run in ScheduledTaskRun.objects.all()
		}
		last_tick = max((j['last_run_at'] for j in jobs.values() if j['last_run_at']), default=None)
		stuck_since = now - timedelta(minutes=30)
		return Response({'success': True, 'data': {
			'database': database,
			'scheduler_configured': bool(getattr(settings, 'CRON_TOKEN', '')),
			'last_tick_at': last_tick,
			'jobs': jobs,
			'orders_ready_without_driver_30min': Order.objects.filter(
				status='ready', updated_at__lt=stuck_since, delivery__delivery_agent__isnull=True,
			).count(),
			'online_payments_pending_30min': Payment.objects.filter(
				status__in=('pending', 'processing'), payment_method__in=('airtel_money', 'moov_money'), created_at__lt=stuck_since,
			).count(),
		}})
