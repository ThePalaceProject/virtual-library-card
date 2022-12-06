from __future__ import annotations

from typing import TYPE_CHECKING

from django.contrib.auth.models import Permission

if TYPE_CHECKING:
    from virtuallibrarycard.models import CustomUser

STAFF_PERMISSIONS = [
    "add_customuser",
    "view_customuser",
    "change_customuser",
    "delete_customuser",
    "add_librarycard",
    "view_librarycard",
    "change_librarycard",
    "delete_librarycard",
]


class UserRules:
    @staticmethod
    def ensure_permissions(user: CustomUser):
        """Ensure a user has the right default permissions attached to them"""
        permissions = []
        if user.is_superuser:
            permissions = Permission.objects.all()
        elif user.is_staff:
            permissions = Permission.objects.filter(
                codename__in=STAFF_PERMISSIONS
            ).all()

        user.user_permissions.add(*permissions)
        user.save()

    @staticmethod
    def drop_permissions(user: CustomUser):
        """Drop permissions based on the current state of the user"""
        permissions = []
        if not user.is_superuser and user.is_staff:
            # Only a staff user, drop everything except the staff permissions
            permissions = Permission.objects.exclude(
                codename__in=STAFF_PERMISSIONS
            ).all()
        elif not user.is_superuser and not user.is_staff:
            # If no status is given, then drop all permissions
            permissions = Permission.objects.all()

        user.user_permissions.remove(*permissions)
        user.save()
