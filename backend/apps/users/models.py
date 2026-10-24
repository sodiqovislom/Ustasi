import re
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db.models import UniqueConstraint, Q
from django.db.models.functions import Lower
from django.core.exceptions import ValidationError
from django.utils import timezone


def normalize_phone_number(phone: str) -> str:
    """
    Standardize Uzbek and international phone numbers:
    e.g. +998 90 123-45-67 -> +998901234567
    """
    if not phone:
        return ''
    cleaned = re.sub(r'[^\d+]', '', str(phone).strip())
    if cleaned.startswith('00'):
        cleaned = '+' + cleaned[2:]
    elif cleaned.startswith('8'):
        cleaned = '+7' + cleaned[1:]
    elif cleaned.startswith('998') and not cleaned.startswith('+998'):
        cleaned = '+' + cleaned
    elif not cleaned.startswith('+') and len(cleaned) == 9:
        # standard 9 digit Uzbek local format e.g. 901234567 -> +998901234567
        cleaned = '+998' + cleaned
    return cleaned


class UserManager(BaseUserManager):
    def create_user(self, phone=None, email=None, password=None, **extra_fields):
        if not phone and not email:
            raise ValueError("Telefon raqami yoki elektron pochta kiritilishi shart.")

        if email:
            email = self.normalize_email(email).lower()
        if phone:
            phone = normalize_phone_number(phone)

        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', 'client')

        user = self.model(phone=phone or None, email=email or None, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def get_by_natural_key(self, username):
        login_str = str(username).strip()
        if login_str.isdigit():
            user = self.filter(id=int(login_str)).first()
            if user:
                return user
        norm_phone = normalize_phone_number(login_str)
        filters = Q(email__iexact=login_str.lower())
        if norm_phone:
            filters |= Q(phone=norm_phone)
        filters |= Q(phone=login_str)
        user = self.filter(filters).first()
        if user:
            return user
        raise self.model.DoesNotExist(f"Foydalanuvchi topilmadi: {username}")

    def create_superuser(self, phone=None, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')

        if not email and not phone:
            email = 'admin@ustasi.uz'

        return self.create_user(phone=phone, email=email, password=password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('client', 'Foydalanuvchi'),
        ('master', 'Usta'),
        ('admin', 'Administrator'),
    )

    first_name = models.CharField(max_length=150, verbose_name="Ism")
    last_name = models.CharField(max_length=150, blank=True, default='', verbose_name="Familiya")
    phone = models.CharField(max_length=25, null=True, blank=True, db_index=True, verbose_name="Telefon raqami")
    email = models.EmailField(max_length=255, null=True, blank=True, db_index=True, verbose_name="Elektron pochta")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='client', verbose_name="Foydalanuvchi roli")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Profil rasmi")
    
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Tahrirlangan sana")

    objects = UserManager()

    USERNAME_FIELD = 'id'  # We authenticate via custom authentication backend or serializer
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"
        ordering = ['-created_at']
        constraints = [
            # Ensure unique phone if not null and not empty
            UniqueConstraint(
                fields=['phone'],
                name='unique_non_empty_phone',
                condition=Q(phone__isnull=False) & ~Q(phone='')
            ),
            # Ensure case-insensitive unique email if not null and not empty
            UniqueConstraint(
                Lower('email'),
                name='unique_non_empty_lower_email',
                condition=Q(email__isnull=False) & ~Q(email='')
            )
        ]

    def clean(self):
        super().clean()
        if self.phone:
            self.phone = normalize_phone_number(self.phone)
        if self.email:
            self.email = self.email.strip().lower()
        if not self.phone and not self.email:
            raise ValidationError("Telefon raqami yoki elektron pochta kiritilishi shart.")

    def save(self, *args, **kwargs):
        if self.phone:
            self.phone = normalize_phone_number(self.phone)
            if not self.phone:
                self.phone = None
        if self.email:
            self.email = self.email.strip().lower()
            if not self.email:
                self.email = None
        self.full_clean(exclude=['password'])
        super().save(*args, **kwargs)

    @property
    def full_name(self) -> str:
        name = f"{self.first_name} {self.last_name}".strip()
        return name or "Foydalanuvchi"

    def __str__(self):
        login_id = self.phone or self.email or str(self.id)
        return f"{self.full_name} ({login_id} - {self.get_role_display()})"
