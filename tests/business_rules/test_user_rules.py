from django.contrib.auth.models import Permission

from tests.base import BaseUnitTest
from virtuallibrarycard.business_rules.user import UserRules


class TestUserRules(BaseUnitTest):
    def test_ensure_permissions(self):
        user = self.create_user(self._default_library)
        assert user.is_staff == False

        user.is_staff = True
        user.save()

        # Ensure 8 staff permissions are added
        UserRules.ensure_permissions(user)
        assert user.user_permissions.count() == 8

        # We do not replace permissions, only add
        perm = Permission.objects.get(codename="add_contenttype")
        user.user_permissions.clear()
        user.user_permissions.add(perm)
        UserRules.ensure_permissions(user)
        assert user.user_permissions.count() == 9
