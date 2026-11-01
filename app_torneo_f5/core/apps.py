from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.dispatch import receiver

class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app_torneo_f5.core"

@receiver(connection_created)
def set_sqlite_pragmas(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        with connection.cursor() as c:
            c.execute("PRAGMA journal_mode=WAL;")
            c.execute("PRAGMA busy_timeout=5000;")
            c.execute("PRAGMA synchronous=NORMAL;")
