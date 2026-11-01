from django.apps import AppConfig

class AppTorneoF5Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_torneo_f5'

    def ready(self):
        import app_torneo_f5.signals  # 👈 Asegura que los signals se registren
