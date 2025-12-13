from django.test import TestCase
from django.utils import timezone
from core.models import AuditLog
from core.validators import validate_not_null, ensure_timezone_aware
from core.exceptions import BusinessValidationError
import datetime


class CoreModuleTests(TestCase):
	def test_auditlog_timestamps_are_timezone_aware(self):
		al = AuditLog.log_action('order_created', None, 'order', 1)
		self.assertIsNotNone(al.created_at.tzinfo)
		self.assertFalse(timezone.is_naive(al.created_at))

	def test_validate_not_null_raises(self):
		with self.assertRaises(BusinessValidationError):
			validate_not_null(None, 'test_field')

	def test_ensure_timezone_aware_converts_naive(self):
		naive = datetime.datetime.utcnow().replace(tzinfo=None)
		aware = ensure_timezone_aware(naive)
		self.assertIsNotNone(aware.tzinfo)
		self.assertFalse(timezone.is_naive(aware))

	def test_ensure_timezone_aware_keeps_aware(self):
		now = timezone.now()
		res = ensure_timezone_aware(now)
		self.assertEqual(res.tzinfo, now.tzinfo)
