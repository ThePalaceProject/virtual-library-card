import logging
from typing import Any, Optional

from django.core.management import BaseCommand
from django.db import connection
from django.db.transaction import atomic
from psycopg2 import sql

logger = logging.getLogger(__name__)
logging.basicConfig()


class Command(BaseCommand):
    """This command is part of the renaming of the app from VirtualLibraryCard to virtuallibrarycard.
    It is idempotent so can remain a part of the codebase until all deployments are completed.
    Once that is done this code becomes redundant, and should be removed.
    """

    help = "Renames customuser auth permission tables"

    def add_arguments(self, parser) -> None:
        parser.add_argument("old_app_name", nargs=1, type=str)
        parser.add_argument("new_app_name", nargs=1, type=str)
        return super().add_arguments(parser)

    @atomic
    def handle(
        self, old_app_name, new_app_name, *args: Any, **options: Any
    ) -> Optional[str]:
        old_app_name = old_app_name[0]
        new_app_name = new_app_name[0]

        with connection.cursor() as cursor:

            for tablename in ("customuser_groups", "customuser_user_permissions"):
                old_full_name = f"{old_app_name}_{tablename}"
                new_full_name = f"{new_app_name}_{tablename}"
                # Postgresql specific implementation
                cursor.execute(
                    "SELECT table_name from information_schema.tables where table_schema='public' and table_name=%s",
                    (old_full_name,),
                )
                if cursor.fetchone() is not None:
                    logger.info(f"Renaming {old_full_name} to {new_full_name}")
                    alter_str = sql.SQL("ALTER TABLE {} RENAME TO {}").format(
                        sql.Identifier(old_full_name), sql.Identifier(new_full_name)
                    )
                    cursor.execute(alter_str)
                else:
                    logger.info(
                        f"No such table found: {old_full_name}. Already renamed.. "
                    )
