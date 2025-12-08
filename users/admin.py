from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin


User = get_user_model()


@admin.register(User)
class CustomUserAdmin(UserAdmin):
	model = User
	list_display = ('phone', 'email', 'first_name', 'last_name', 'city', 'is_staff', 'user_type', 'is_verified')
	list_filter = ('is_staff', 'is_superuser', 'is_active', 'user_type', 'city')
	search_fields = ('phone', 'email', 'first_name', 'last_name', 'city')
	ordering = ('-date_joined',)

	# Make date_joined readonly in the admin form
	readonly_fields = ('date_joined',)

	fieldsets = (
		(None, {'fields': ('phone', 'password')}),
		('Personal info', {'fields': ('first_name', 'last_name', 'email', 'city')}),
		('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
		('Important dates', {'fields': ('last_login',)}),
		('GABOSHOP info', {'fields': ('user_type', 'is_verified', 'is_available', 'current_location')}),
	)

	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ('phone', 'email', 'password1', 'password2', 'user_type'),
		}),
	)
