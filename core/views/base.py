from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from core.throttling import LoginRateThrottle, RegisterRateThrottle
from django.contrib.auth import authenticate, get_user_model
from django.db.models import Q

from core.models import Enterprise, Branch, AuditLog
from core.serializers import (
    CustomUserSerializer, CustomUserCreateSerializer,
    EnterpriseSerializer, BranchSerializer, AuditLogSerializer
)
from core.permissions import IsAdmin, IsEnterpriseOwnerOrAdmin, IsAuthenticated

User = get_user_model()


class CustomUserViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de usuarios.

    Sólo admins pueden listar/editar/eliminar/crear usuarios. Acciones
    públicas (login, register) y de self-service (me) tienen permisos
    aparte vía decorador.
    """
    queryset = User.objects.all()
    serializer_class = CustomUserSerializer

    # Acciones que cualquier usuario autenticado puede ejecutar sobre
    # sí mismo o como flujo público.
    _OPEN_ACTIONS = {'login', 'register', 'me', 'logout', 'health'}

    def get_permissions(self):
        if getattr(self, 'action', None) in self._OPEN_ACTIONS:
            # cada @action ya define sus permission_classes (AllowAny/IsAuthenticated)
            return super().get_permissions()
        # Todo lo demás (list/retrieve/create/update/partial_update/destroy,
        # admin_create, set_password, set_branches) requiere admin.
        return [IsAuthenticated(), IsAdmin()]

    def get_queryset(self):
        # Los usuarios solo ven usuarios de su misma empresa
        if self.request.user and self.request.user.enterprise:
            return User.objects.filter(enterprise=self.request.user.enterprise)
        return User.objects.none()

    def get_serializer_class(self):
        if self.action == 'create':
            return CustomUserCreateSerializer
        return CustomUserSerializer

    def perform_create(self, serializer):
        # get_permissions ya bloquea no-admins; igual dejamos un guard explícito.
        if self.request.user.role != 'admin' and not self.request.user.is_superuser:
            raise PermissionError('Solo administradores pueden crear usuarios')
        serializer.save(enterprise=self.request.user.enterprise)
    
    @action(
        detail=False, methods=['post'],
        permission_classes=[AllowAny],
        throttle_classes=[RegisterRateThrottle],
    )
    def register(self, request):
        """Registrar nuevo usuario (crea empresa).

        Throttled a 3/min por IP (THROTTLE_REGISTER en settings) — prevenir
        creación masiva de cuentas dummy.
        """
        serializer = CustomUserCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Crear empresa
            enterprise = Enterprise.objects.create(
                name=request.data.get('enterprise_name', 'Mi Empresa'),
                ruc=request.data.get('ruc', ''),
                email=request.data.get('email'),
                phone=request.data.get('phone', ''),
                address=request.data.get('address', ''),
                city=request.data.get('city', 'Asunción')
            )
            
            # Crear usuario como admin
            user = serializer.save(
                enterprise=enterprise,
                role='admin'
            )
            
            # Generar tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'user': CustomUserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(
        detail=False, methods=['post'],
        permission_classes=[AllowAny],
        throttle_classes=[LoginRateThrottle],
    )
    def login(self, request):
        """Iniciar sesión con usuario y contraseña.

        Throttled a 5/min por IP (THROTTLE_LOGIN en settings) — bloquea
        brute force contra contraseñas. Devolvemos siempre el mismo error
        para usuario inexistente y contraseña mala (no filtramos qué falló).
        """
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({
                'error': 'Usuario y contraseña son requeridos'
            }, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(username=username, password=password)

        if user is None:
            # Loguear intentos fallidos para detectar brute force.
            import logging
            logging.getLogger('security').warning(
                'login_failed username=%s ip=%s',
                username, request.META.get('REMOTE_ADDR', '?'),
            )
            return Response({
                'error': 'Usuario o contraseña inválidos',
                'detail': 'Usuario o contraseña inválidos',
            }, status=status.HTTP_401_UNAUTHORIZED)

        if not user.is_active:
            return Response({
                'error': 'Usuario inactivo'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': CustomUserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_200_OK)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Obtener datos del usuario actual"""
        return Response(CustomUserSerializer(request.user).data)

    @action(detail=False, methods=['get'], permission_classes=[AllowAny], throttle_classes=[])
    def health(self, request):
        """Health check público (sin auth, sin throttle).

        Usado por Render para verificar que el servicio responde. Hace una
        query trivial a la DB para detectar problemas de conexión a Supabase.
        """
        from django.db import connection
        try:
            with connection.cursor() as c:
                c.execute('SELECT 1')
            return Response({'status': 'ok', 'db': 'ok'})
        except Exception as e:
            return Response(
                {'status': 'error', 'db': str(e)[:200]},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Cerrar sesión — invalida el refresh token enviado.

        El cliente debe pasar `{"refresh": "<token>"}` en el body. Lo
        agregamos a la blacklist para que no se pueda volver a usar.
        El access token sigue siendo válido hasta que expire (1h), pero
        sin refresh el cliente no puede renovar.
        """
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'Falta el refresh token en el body.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as e:
            # El token ya estaba blacklisteado o vencido — del lado del
            # usuario la sesión está cerrada igual. Devolvemos 200 para no
            # confundir al frontend.
            pass
        return Response({'detail': 'Sesión cerrada'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def set_password(self, request, pk=None):
        """Permite al admin resetear la contraseña de un usuario"""
        if request.user.role != 'admin' and not request.user.is_superuser:
            return Response({'detail': 'Solo admin'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        new_password = request.data.get('password')
        if not new_password or len(new_password) < 6:
            return Response({'password': 'Mínimo 6 caracteres'},
                            status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return Response({'detail': 'Contraseña actualizada'})

    @action(detail=True, methods=['post'])
    def set_branches(self, request, pk=None):
        """Permite al admin configurar las sucursales visibles de un usuario"""
        if request.user.role != 'admin' and not request.user.is_superuser:
            return Response({'detail': 'Solo admin'}, status=status.HTTP_403_FORBIDDEN)
        user = self.get_object()
        branch_ids = request.data.get('branches', [])
        if not isinstance(branch_ids, list):
            return Response({'branches': 'Debe ser una lista de IDs'},
                            status=status.HTTP_400_BAD_REQUEST)
        # Filtrar a sucursales de la misma empresa
        valid_branches = Branch.objects.filter(
            id__in=branch_ids, enterprise=user.enterprise
        )
        user.branches_visible.set(valid_branches)
        return Response(CustomUserSerializer(user).data)

    @action(detail=False, methods=['post'])
    def admin_create(self, request):
        """Crear usuario desde el módulo admin (sin password_confirm)"""
        if request.user.role != 'admin' and not request.user.is_superuser:
            return Response({'detail': 'Solo admin'}, status=status.HTTP_403_FORBIDDEN)

        username = request.data.get('username')
        password = request.data.get('password')
        if not username or not password or len(password) < 6:
            return Response({'detail': 'username y password (>=6) requeridos'},
                            status=status.HTTP_400_BAD_REQUEST)
        if User.objects.filter(username=username).exists():
            return Response({'username': 'Ya existe'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(
            username=username,
            password=password,
            email=request.data.get('email', ''),
            first_name=request.data.get('first_name', ''),
            last_name=request.data.get('last_name', ''),
        )
        user.role = request.data.get('role', 'vendor')
        user.phone = request.data.get('phone', '')
        user.is_active = request.data.get('is_active', True)
        user.enterprise = request.user.enterprise
        user.save()

        branches = request.data.get('branches', [])
        if branches:
            valid = Branch.objects.filter(id__in=branches, enterprise=user.enterprise)
            user.branches_visible.set(valid)

        return Response(CustomUserSerializer(user).data, status=status.HTTP_201_CREATED)


class EnterpriseViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de empresas"""
    queryset = Enterprise.objects.all()
    serializer_class = EnterpriseSerializer
    permission_classes = [IsAdmin]
    
    def get_queryset(self):
        # Admins de su empresa ven su empresa, super admin ve todas
        user = self.request.user
        if user.is_superuser:
            return Enterprise.objects.all()
        if user.role == 'admin' and user.enterprise:
            return Enterprise.objects.filter(id=user.enterprise.id)
        return Enterprise.objects.none()
    
    def perform_create(self, serializer):
        # El usuario que crea la empresa es el creador
        serializer.save(created_by=self.request.user)


class BranchViewSet(viewsets.ModelViewSet):
    """ViewSet para gestión de sucursales"""
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated, IsEnterpriseOwnerOrAdmin]
    
    def get_queryset(self):
        # Solo ver sucursales de su empresa
        if self.request.user and self.request.user.enterprise:
            return Branch.objects.filter(enterprise=self.request.user.enterprise)
        return Branch.objects.none()
    
    def perform_create(self, serializer):
        # Asegurar que la sucursal pertenece a la empresa del usuario
        serializer.save(enterprise=self.request.user.enterprise)


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para los registros de auditoría.

    Filtros (todos opcionales, vía query params):
      - `action`: create | update | delete | login | logout | export | import
      - `model`: nombre del modelo (Sale, Customer, etc.) — match exacto.
      - `user`: id del usuario que ejecutó la acción.
      - `date_from`, `date_to`: rango (timestamps tipo YYYY-MM-DD).
      - `q`: substring en `object_str` (ej: número de venta, nombre cliente).

    Acceso: sólo admins de la empresa (IsAdmin), salvo superuser que ve todo.
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        user = self.request.user
        if not (user and user.is_authenticated):
            return AuditLog.objects.none()

        # Base con select_related para evitar N+1 al serializar user__username.
        qs = AuditLog.objects.select_related('user', 'enterprise')

        if user.is_superuser:
            pass  # ve todo
        elif user.enterprise:
            qs = qs.filter(enterprise=user.enterprise)
        else:
            return AuditLog.objects.none()

        params = self.request.query_params
        if action := params.get('action'):
            qs = qs.filter(action=action)
        if model_name := params.get('model'):
            qs = qs.filter(model_name__iexact=model_name)
        if user_id := params.get('user'):
            if str(user_id).isdigit():
                qs = qs.filter(user_id=int(user_id))
        if date_from := params.get('date_from'):
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to := params.get('date_to'):
            qs = qs.filter(timestamp__date__lte=date_to)
        if q := (params.get('q') or '').strip():
            qs = qs.filter(object_str__icontains=q)

        return qs.order_by('-timestamp')
