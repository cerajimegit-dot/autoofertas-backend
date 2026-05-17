from rest_framework import serializers
from django.contrib.auth import get_user_model
from core.models import Enterprise, Branch, AuditLog

User = get_user_model()


class CustomUserSerializer(serializers.ModelSerializer):
    """Serializador para CustomUser"""
    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    branches_visible = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Branch.objects.all(), required=False
    )
    branches_visible_detail = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'enterprise', 'enterprise_name', 'role', 'role_display',
            'phone', 'is_active', 'is_staff',
            'branches_visible', 'branches_visible_detail',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'enterprise', 'created_at', 'updated_at')

    def get_branches_visible_detail(self, obj):
        return [
            {'id': b.id, 'name': b.name, 'code': b.code}
            for b in obj.branches_visible.all()
        ]


class CustomUserCreateSerializer(serializers.ModelSerializer):
    """Serializador para crear usuarios (con validación de contraseña)"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = (
            'username', 'email', 'first_name', 'last_name',
            'password', 'password_confirm', 'enterprise', 'role', 'phone'
        )
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password': 'Las contraseñas no coinciden'
            })
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


class EnterpriseSerializer(serializers.ModelSerializer):
    """Serializador para Enterprise"""
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    users_count = serializers.SerializerMethodField()
    branches_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Enterprise
        fields = (
            'id', 'name', 'ruc', 'email', 'phone', 'address', 'city',
            'country', 'logo', 'subscription_status', 'created_by',
            'created_by_name', 'users_count', 'branches_count', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at', 'created_by')
    
    def get_users_count(self, obj):
        return obj.users.count()
    
    def get_branches_count(self, obj):
        return obj.branches.count()


class BranchSerializer(serializers.ModelSerializer):
    """Serializador para Branch"""
    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)
    manager_name = serializers.CharField(source='manager.get_full_name', read_only=True)
    vehicles_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Branch
        fields = (
            'id', 'enterprise', 'enterprise_name', 'name', 'code',
            'address', 'city', 'phone', 'manager', 'manager_name',
            'vehicles_count', 'is_active', 'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_vehicles_count(self, obj):
        return obj.vehicles.count()


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializador de solo lectura para AuditLog"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    enterprise_name = serializers.CharField(source='enterprise.name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = (
            'id', 'user', 'user_name', 'enterprise', 'enterprise_name',
            'action', 'action_display', 'model_name', 'object_id', 'object_str',
            'old_values', 'new_values', 'ip_address', 'timestamp'
        )
        read_only_fields = fields
