# app_torneo_f5/tokens.py
from django.contrib.auth.tokens import PasswordResetTokenGenerator

class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    # Si querés invalidar al verificarse, agregá email_verified en el hash
    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.is_active}{user.email_verified}"

email_verification_token = EmailVerificationTokenGenerator()
