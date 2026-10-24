from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import normalize_phone_number

UserModel = get_user_model()


class PhoneOrEmailBackend(ModelBackend):
    """
    Authenticate against settings.AUTH_USER_MODEL using phone number,
    email address, or id.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD) or kwargs.get('email') or kwargs.get('phone')

        if not username or not password:
            return None

        login_str = str(username).strip()
        normalized_phone = normalize_phone_number(login_str)

        filters = Q(email__iexact=login_str.lower())
        if normalized_phone:
            filters |= Q(phone=normalized_phone)
        filters |= Q(phone=login_str)
        if login_str.isdigit():
            filters |= Q(id=int(login_str))

        user = UserModel.objects.filter(filters).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

    def get_user(self, user_id):
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None
