import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from .permissions_catalog import ALL_PERMISSIONS


class Role(models.Model):
    """
    A named set of dashboard permissions (see permissions_catalog.py).

    Permissions are a plain list rather than a join table: the set is small,
    always read whole, and never queried by individual permission.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=60, unique=True)
    description = models.CharField(max_length=300, blank=True, default='')
    permissions = models.JSONField(default=list, blank=True)
    # The Administrator role: always holds every permission, including ones a
    # later release adds, and cannot be edited, renamed or deleted.
    locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-locked', 'name']

    def __str__(self):
        return self.name

    @property
    def effective_permissions(self) -> list[str]:
        return list(ALL_PERMISSIONS) if self.locked else list(self.permissions or [])


class AdminUserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('An email address is required.')
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('legacy_role', AdminUser.LegacyRole.ADMIN)
        user = self.create_user(email, password, **extra)
        if user.role_id is None:
            admin_role = Role.objects.filter(locked=True).first()
            if admin_role:
                user.role = admin_role
                user.save(update_fields=['role'])
        return user


class AdminUser(AbstractBaseUser, PermissionsMixin):
    """
    A dashboard account. Signs in by email.

    `role` drives what the Next.js dashboard allows. `is_staff`/`is_superuser`
    only gate Django's own /django-admin/ screens, which are a fallback for
    operators rather than the everyday tool.
    """

    class LegacyRole(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        EDITOR = 'editor', 'Editor'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=120, default='Administrator')
    # Coarse role kept in step with `role` (see views.legacy_role_for). Still
    # checked by the few routes gated on "full admin" rather than a permission.
    legacy_role = models.CharField(max_length=10, choices=LegacyRole.choices, default=LegacyRole.EDITOR)
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.SET_NULL, related_name='users')
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_sample = models.BooleanField(
        default=False, help_text='Demo staff account created by the seed; cannot sign in.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = AdminUserManager()

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} <{self.email}>'

    @property
    def dashboard_permissions(self) -> list[str]:
        if self.role is not None:
            return self.role.effective_permissions
        # An account predating roles keeps access through its coarse role.
        return list(ALL_PERMISSIONS) if self.legacy_role == self.LegacyRole.ADMIN else []

    def has_dashboard_permission(self, *required: str) -> bool:
        held = set(self.dashboard_permissions)
        return all(p in held for p in required)


class AuditLog(models.Model):
    """
    Append-only record of access changes: who did what to whom.

    `actor` is SET_NULL, not CASCADE: deleting an account must not erase the
    history of what it did. `actor_email` keeps the identity legible afterwards.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor = models.ForeignKey(AdminUser, null=True, blank=True, on_delete=models.SET_NULL, related_name='audit_entries')
    actor_email = models.CharField(max_length=254)
    action = models.CharField(max_length=60, db_index=True)
    target_type = models.CharField(max_length=40, blank=True, null=True)
    target_id = models.UUIDField(blank=True, null=True)
    target_label = models.CharField(max_length=254, blank=True, null=True)
    changes = models.JSONField(default=dict, blank=True)
    ip = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M} {self.actor_email} {self.action}'
