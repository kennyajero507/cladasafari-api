from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import serializers

from apps.common.exceptions import ApiError
from apps.common.responses import page_meta, paginate, send
from apps.common.validation import PaginationQuery, SearchField, query_dict, validate

from .audit import record_changes, write_audit
from .auth import AdminView, PublicView, clear_auth_cookie, client_ip, set_auth_cookie, sign_token
from .models import AdminUser, AuditLog, Role
from .permissions_catalog import ALL_PERMISSIONS, PERMISSION_GROUPS, is_permission

# ---------------------------------------------------------------------------
# Shapes
# ---------------------------------------------------------------------------


def session_shape(user: AdminUser) -> dict:
    """/auth/me and /auth/login: what the dashboard needs to decide what to show."""
    return {
        'id': str(user.id),
        '_id': str(user.id),
        'email': user.email,
        'name': user.name,
        'role': user.legacy_role,
        'roleName': user.role.name if user.role else None,
        'permissions': user.dashboard_permissions,
        'lastLoginAt': user.last_login,
    }


def user_shape(user: AdminUser) -> dict:
    return {
        'id': str(user.id),
        '_id': str(user.id),
        'email': user.email,
        'name': user.name,
        'role': {'id': str(user.role.id), 'name': user.role.name, 'locked': user.role.locked} if user.role else None,
        'roleId': str(user.role_id) if user.role_id else None,
        'isSample': user.is_sample,
        'lastLoginAt': user.last_login,
        'createdAt': user.created_at,
        'updatedAt': user.updated_at,
    }


def role_shape(role: Role, user_count: int | None = None) -> dict:
    return {
        'id': str(role.id),
        '_id': str(role.id),
        'name': role.name,
        'description': role.description,
        # A locked role holds everything, including permissions added after the
        # row was written: report that rather than the stored list.
        'permissions': role.effective_permissions,
        'locked': role.locked,
        'userCount': user_count,
        'createdAt': role.created_at,
        'updatedAt': role.updated_at,
    }


def legacy_role_for(role: Role | None) -> str:
    """Anyone who can manage users or settings counts as a full admin on the coarse role."""
    if role is None:
        return AdminUser.LegacyRole.EDITOR
    if role.locked:
        return AdminUser.LegacyRole.ADMIN
    perms = role.permissions or []
    return AdminUser.LegacyRole.ADMIN if ('users.manage' in perms or 'settings.edit' in perms) else AdminUser.LegacyRole.EDITOR


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class LoginBody(serializers.Serializer):
    email = serializers.EmailField(error_messages={'invalid': 'Enter a valid email address.'})
    password = serializers.CharField(error_messages={'blank': 'Enter your password.'})


def _failure_key(request) -> str:
    return f'login-failures:{client_ip(request)}'


class LoginView(PublicView):
    """
    Brute-force guard counts *failed* attempts only, per client IP. A correct
    password is not evidence of an attack, and counting successes could lock
    out an office sharing one address.
    """

    def post(self, request):
        key = _failure_key(request)
        if cache.get(key, 0) >= settings.LOGIN_MAX_FAILURES:
            raise ApiError(
                429, 'Too many failed sign-in attempts from this address. Try again in about 15 minutes.'
            )

        body = validate(LoginBody, request.data)
        email = body['email'].strip().lower()
        user = AdminUser.objects.select_related('role').filter(email=email, is_active=True).first()

        # One message for unknown email and wrong password: never reveal which.
        if user is None or not user.has_usable_password() or not user.check_password(body['password']):
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, settings.LOGIN_FAILURE_WINDOW_SECONDS)
            raise ApiError.unauthorized('Those credentials do not match our records.')

        cache.delete(key)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])

        response = send(session_shape(user))
        set_auth_cookie(response, sign_token(user))
        return response


class LogoutView(AdminView):
    def post(self, request):
        response = send({'loggedOut': True})
        clear_auth_cookie(response)
        return response


class MeView(AdminView):
    def get(self, request):
        return send(session_shape(request.user))


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

USER_SORTS = {
    'newest': ['-created_at'],
    'oldest': ['created_at'],
    'name-asc': ['name'],
    'email-asc': ['email'],
}


class UserListQuery(PaginationQuery):
    q = SearchField()
    roleId = serializers.UUIDField(required=False)
    sort = serializers.ChoiceField(choices=list(USER_SORTS), required=False)


class PasswordField(serializers.CharField):
    def __init__(self, **kwargs):
        super().__init__(
            min_length=12,
            max_length=200,
            trim_whitespace=False,
            error_messages={'min_length': 'Use at least 12 characters.', 'max_length': 'That password is too long.'},
            **kwargs,
        )


class CreateUserBody(serializers.Serializer):
    email = serializers.EmailField(error_messages={'invalid': 'Enter a valid email address.'})
    name = serializers.CharField(min_length=2, max_length=120, error_messages={'min_length': 'Enter a name.'})
    password = PasswordField()
    roleId = serializers.UUIDField(error_messages={'invalid': 'That is not a valid id.'})


class UpdateUserBody(serializers.Serializer):
    email = serializers.EmailField(required=False)
    name = serializers.CharField(min_length=2, max_length=120, required=False)
    password = PasswordField(required=False)
    roleId = serializers.UUIDField(required=False)

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError('Nothing to update.')
        return attrs


def _check_password_strength(password: str, user: AdminUser | None = None) -> None:
    try:
        validate_password(password, user)
    except DjangoValidationError as exc:
        raise ApiError.unprocessable(details={'password': exc.messages[0]})


def _load_role(role_id) -> Role:
    role = Role.objects.filter(pk=role_id).first()
    if role is None:
        raise ApiError.bad_request('That role does not exist.')
    return role


def _assert_not_last_manager(user_id, action: str) -> None:
    """Refuse any change that would leave nobody able to manage users."""
    others = [
        u
        for u in AdminUser.objects.select_related('role').filter(is_active=True).exclude(pk=user_id)
        if 'users.manage' in u.dashboard_permissions
    ]
    if not others:
        raise ApiError.bad_request(
            f'This is the only account that can manage users. Give another account that permission before {action} it.'
        )


class UserListView(AdminView):
    required_permissions = {'GET': 'users.view', 'POST': 'users.manage'}

    def get(self, request):
        q = validate(UserListQuery, query_dict(request))
        qs = AdminUser.objects.select_related('role')
        if q.get('roleId'):
            qs = qs.filter(role_id=q['roleId'])
        if q.get('q'):
            qs = qs.filter(Q(name__icontains=q['q']) | Q(email__icontains=q['q']))
        qs = qs.order_by(*USER_SORTS.get(q.get('sort'), ['name']))
        rows, total = paginate(qs, q['page'], q['limit'])
        return send([user_shape(u) for u in rows], meta=page_meta(q['page'], q['limit'], total))

    def post(self, request):
        body = validate(CreateUserBody, request.data)
        email = body['email'].strip().lower()
        if AdminUser.objects.filter(email=email).exists():
            raise ApiError.bad_request('An account with that email address already exists.')
        role = _load_role(body['roleId'])
        _check_password_strength(body['password'])

        user = AdminUser(email=email, name=body['name'].strip(), role=role, legacy_role=legacy_role_for(role))
        user.set_password(body['password'])
        user.save()

        write_audit(
            request,
            'user.create',
            {'type': 'user', 'id': user.id, 'label': user.email},
            {'after': {'name': user.name, 'email': user.email, 'role': role.name}},
        )
        return send(user_shape(user), status=201)


class UserDetailView(AdminView):
    required_permissions = 'users.manage'

    def patch(self, request, id):
        body = validate(UpdateUserBody, request.data)
        target = AdminUser.objects.select_related('role').filter(pk=id).first()
        if target is None:
            raise ApiError.not_found('That account no longer exists.')

        before = {'name': target.name, 'email': target.email, 'role': target.role.name if target.role else None}
        after: dict = {}

        if 'email' in body:
            email = body['email'].strip().lower()
            if email != target.email and AdminUser.objects.filter(email=email).exists():
                raise ApiError.bad_request('An account with that email address already exists.')
            target.email = after['email'] = email
        if 'name' in body:
            target.name = after['name'] = body['name'].strip()
        if 'password' in body:
            _check_password_strength(body['password'], target)
            target.set_password(body['password'])
            after['password'] = True

        role_changed = 'roleId' in body and body['roleId'] != target.role_id
        if role_changed:
            next_role = _load_role(body['roleId'])
            # Moving yourself to a role without user management locks the door
            # from the inside: this request succeeds, the next one is refused.
            if target.id == request.user.id and 'users.manage' not in next_role.effective_permissions:
                raise ApiError.bad_request('You cannot remove your own access to user management.')
            if 'users.manage' in target.dashboard_permissions and 'users.manage' not in next_role.effective_permissions:
                _assert_not_last_manager(target.id, 'changing the role of')
            target.role = next_role
            target.legacy_role = legacy_role_for(next_role)
            after['role'] = next_role.name

        target.save()
        write_audit(
            request,
            'user.role_change' if role_changed else 'user.update',
            {'type': 'user', 'id': target.id, 'label': target.email},
            record_changes(before, after),
        )
        return send(user_shape(target))

    def delete(self, request, id):
        if str(id) == str(request.user.id):
            raise ApiError.bad_request('You cannot delete the account you are signed in with.')
        target = AdminUser.objects.select_related('role').filter(pk=id).first()
        if target is None:
            raise ApiError.not_found('That account no longer exists.')
        if 'users.manage' in target.dashboard_permissions:
            _assert_not_last_manager(target.id, 'deleting')

        snapshot = {'name': target.name, 'email': target.email, 'role': target.role.name if target.role else None}
        target.delete()
        write_audit(request, 'user.delete', {'type': 'user', 'id': id, 'label': snapshot['email']}, {'before': snapshot})
        return send({'deleted': True, 'id': str(id)})


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------


def _permission_list(value):
    if not all(is_permission(p) for p in value):
        raise serializers.ValidationError('That permission list contains an unknown permission.')
    return value


class CreateRoleBody(serializers.Serializer):
    name = serializers.CharField(min_length=2, max_length=60, error_messages={'min_length': 'Name the role.'})
    description = serializers.CharField(max_length=300, required=False, allow_blank=True)
    permissions = serializers.ListField(child=serializers.CharField(), max_length=200, validators=[_permission_list])


class UpdateRoleBody(serializers.Serializer):
    name = serializers.CharField(min_length=2, max_length=60, required=False)
    description = serializers.CharField(max_length=300, required=False, allow_blank=True)
    permissions = serializers.ListField(
        child=serializers.CharField(), max_length=200, required=False, validators=[_permission_list]
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError('Nothing to update.')
        return attrs


class PermissionCatalogueView(AdminView):
    required_permissions = 'users.view'

    def get(self, request):
        return send({'groups': PERMISSION_GROUPS})


class RoleListView(AdminView):
    required_permissions = {'GET': 'users.view', 'POST': 'roles.manage'}

    def get(self, request):
        q = validate(PaginationQuery, query_dict(request))
        qs = Role.objects.annotate(user_count=Count('users')).order_by('-locked', 'name')
        rows, total = paginate(qs, q['page'], q['limit'])
        return send([role_shape(r, r.user_count) for r in rows], meta=page_meta(q['page'], q['limit'], total))

    def post(self, request):
        body = validate(CreateRoleBody, request.data)
        name = body['name'].strip()
        if Role.objects.filter(name__iexact=name).exists():
            raise ApiError.bad_request('A role with that name already exists.')
        role = Role.objects.create(name=name, description=body.get('description', ''), permissions=body['permissions'])
        write_audit(
            request,
            'role.create',
            {'type': 'role', 'id': role.id, 'label': role.name},
            {'after': {'name': role.name, 'permissions': role.permissions}},
        )
        return send(role_shape(role, 0), status=201)


class RoleDetailView(AdminView):
    required_permissions = 'roles.manage'

    def patch(self, request, id):
        body = validate(UpdateRoleBody, request.data)
        role = Role.objects.filter(pk=id).first()
        if role is None:
            raise ApiError.not_found('That role no longer exists.')
        # The Administrator role is the recovery path; it must stay intact.
        if role.locked:
            raise ApiError.bad_request('The Administrator role cannot be changed.')

        before = {'name': role.name, 'permissions': list(role.permissions)}
        if 'name' in body:
            name = body['name'].strip()
            if name != role.name and Role.objects.filter(name__iexact=name).exclude(pk=role.pk).exists():
                raise ApiError.bad_request('A role with that name already exists.')
            role.name = name
        if 'description' in body:
            role.description = body['description']
        if 'permissions' in body:
            role.permissions = body['permissions']
        role.save()

        # Keep holders' coarse role in step with what the role now grants.
        AdminUser.objects.filter(role=role).update(legacy_role=legacy_role_for(role))

        write_audit(
            request,
            'role.update',
            {'type': 'role', 'id': role.id, 'label': role.name},
            {'before': before, 'after': {'name': role.name, 'permissions': role.permissions}},
        )
        return send(role_shape(role, role.users.count()))

    def delete(self, request, id):
        role = Role.objects.filter(pk=id).first()
        if role is None:
            raise ApiError.not_found('That role no longer exists.')
        if role.locked:
            raise ApiError.bad_request('The Administrator role cannot be deleted.')
        holders = role.users.count()
        # SET_NULL would silently strip these accounts of every permission.
        if holders:
            noun = 'account uses' if holders == 1 else 'accounts use'
            raise ApiError.bad_request(f'{holders} {noun} this role. Move them to another role first.')

        snapshot = {'name': role.name, 'permissions': role.permissions}
        role.delete()
        write_audit(request, 'role.delete', {'type': 'role', 'id': id, 'label': snapshot['name']}, {'before': snapshot})
        return send({'deleted': True, 'id': str(id)})


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


class AuditQuery(PaginationQuery):
    action = serializers.CharField(max_length=60, required=False, allow_blank=True)


class AuditListView(AdminView):
    required_permissions = 'audit.view'

    def get(self, request):
        q = validate(AuditQuery, query_dict(request))
        qs = AuditLog.objects.all()
        if q.get('action'):
            qs = qs.filter(action=q['action'])
        rows, total = paginate(qs, q['page'], q['limit'])
        data = [
            {
                'id': str(e.id),
                '_id': str(e.id),
                'actorId': str(e.actor_id) if e.actor_id else None,
                'actorEmail': e.actor_email,
                'action': e.action,
                'targetType': e.target_type,
                'targetId': str(e.target_id) if e.target_id else None,
                'targetLabel': e.target_label,
                'changes': e.changes,
                'ip': e.ip,
                'createdAt': e.created_at,
            }
            for e in rows
        ]
        return send(data, meta=page_meta(q['page'], q['limit'], total))


__all__ = ['ALL_PERMISSIONS']
