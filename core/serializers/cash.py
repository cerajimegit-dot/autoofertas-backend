"""Serializadores para CashMovement."""

from rest_framework import serializers
from core.models import CashMovement


class CashMovementSerializer(serializers.ModelSerializer):
    kind_display      = serializers.CharField(source='get_kind_display', read_only=True)
    direction_display = serializers.CharField(source='get_direction_display', read_only=True)
    branch_name       = serializers.CharField(source='branch.name', read_only=True, allow_null=True)
    sale_number       = serializers.CharField(source='sale.sale_number', read_only=True, allow_null=True)
    quota_label       = serializers.SerializerMethodField()
    created_by_username = serializers.CharField(source='created_by.username', read_only=True, allow_null=True)
    signed_amount     = serializers.SerializerMethodField()

    class Meta:
        model = CashMovement
        fields = (
            'id', 'enterprise', 'branch', 'branch_name',
            'date', 'kind', 'kind_display', 'direction', 'direction_display',
            'description',
            'amount', 'currency', 'amount_usd', 'exchange_rate', 'signed_amount',
            'provider',
            'sale', 'sale_number', 'quota', 'quota_label',
            'created_by', 'created_by_username', 'is_auto',
            'notes', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'enterprise', 'created_at', 'updated_at',
            'is_auto', 'created_by',
        )

    def get_quota_label(self, obj):
        if not obj.quota:
            return None
        q = obj.quota
        return f'{q.quota_number}/{q.total_plan or "?"}'

    def get_signed_amount(self, obj):
        return float(obj.amount if obj.direction == 'in' else -obj.amount)

    def validate(self, attrs):
        # `amount` debe ser > 0; el signo lo da `direction`.
        amount = attrs.get('amount') or getattr(self.instance, 'amount', None)
        if amount is not None and amount <= 0:
            raise serializers.ValidationError({
                'amount': 'El monto debe ser positivo. La dirección (ingreso/egreso) define el signo.'
            })
        return attrs
