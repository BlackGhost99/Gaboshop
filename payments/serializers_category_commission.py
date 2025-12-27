from rest_framework import serializers
from .models import CategoryCommission


class CategoryCommissionSerializer(serializers.ModelSerializer):
    store_category_name = serializers.CharField(source='store_category.name', read_only=True)

    class Meta:
        model = CategoryCommission
        fields = [
            'id', 'store_category', 'store_category_name', 'base_rate', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'store_category_name']
