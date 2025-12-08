from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
	list_display = [
		'action_timestamp', 'get_action_type_display', 'user', 'object_type', 
		'object_id', 'old_value', 'new_value', 'is_suspicious'
	]
	list_filter = ['action_type', 'action_timestamp', 'is_suspicious', 'object_type']
	search_fields = ['user__email', 'user__username', 'object_id', 'ip_address']
	readonly_fields = [
		'action_type', 'action_timestamp', 'user', 'user_role', 
		'object_type', 'object_id', 'old_value', 'new_value', 
		'ip_address', 'user_agent', 'reason', 'is_suspicious', 'notes',
		'created_at', 'updated_at'
	]
	
	def has_add_permission(self, request):
		return False
	
	def has_delete_permission(self, request, obj=None):
		return False
	
	def has_change_permission(self, request, obj=None):
		# Seulement les administrateurs peuvent visualiser et modifier les notes
		return request.user.is_superuser
