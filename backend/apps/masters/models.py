from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, UniqueConstraint


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Kategoriya nomi")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Slug")
    icon = models.CharField(max_length=50, blank=True, default="Wrench", verbose_name="Belgi (icon)")
    description = models.TextField(blank=True, default="", verbose_name="Tavsif")
    is_active = models.BooleanField(default=True, verbose_name="Faol")
    order = models.PositiveIntegerField(default=0, verbose_name="Tartib")

    class Meta:
        verbose_name = "Kategoriya"
        verbose_name_plural = "Kategoriyalar"
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Master(models.Model):
    STATUS_CHOICES = (
        ('active', 'Faol'),
        ('busy', 'Band'),
        ('inactive', 'Nofaol'),
    )

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='master_profile',
        verbose_name="Foydalanuvchi akkaunti"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='masters',
        verbose_name="Usta kategoriyasi"
    )
    description = models.TextField(verbose_name="Xizmat haqida qisqa ma'lumot")
    experience = models.PositiveIntegerField(default=1, verbose_name="Ish tajribasi (yil)")
    price = models.PositiveIntegerField(default=50000, verbose_name="Boshlang'ich narx (so'm)")
    region = models.CharField(max_length=100, db_index=True, verbose_name="Hudud / Viloyat")
    district = models.CharField(max_length=100, db_index=True, verbose_name="Tuman / Shahar")
    address = models.CharField(max_length=255, blank=True, default="", verbose_name="Aniq manzil")
    latitude = models.FloatField(null=True, blank=True, verbose_name="Kenglik (Latitude)")
    longitude = models.FloatField(null=True, blank=True, verbose_name="Uzunlik (Longitude)")
    working_hours = models.CharField(max_length=100, default="09:00 - 18:00", verbose_name="Ish vaqti")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active', verbose_name="Holat")

    # Real calculated ratings cached on model for fast filtering and ordering
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        db_index=True,
        verbose_name="O'rtacha reyting"
    )
    ratings_count = models.PositiveIntegerField(default=0, db_index=True, verbose_name="Baholaganlar soni")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan sana")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Yangilangan sana")

    class Meta:
        verbose_name = "Usta"
        verbose_name_plural = "Ustalar"
        ordering = ['-average_rating', '-ratings_count', '-created_at']

    def update_rating_stats(self):
        """Recalculate average rating and count accurately from the Rating table."""
        stats = self.ratings.aggregate(avg=Avg('score'), count=Count('id'))
        avg = stats['avg']
        self.average_rating = round(avg, 2) if avg is not None else 0.00
        self.ratings_count = stats['count'] or 0
        self.save(update_fields=['average_rating', 'ratings_count'])

    @property
    def full_name(self):
        return self.user.full_name

    @property
    def phone(self):
        return self.user.phone

    @property
    def avatar_url(self):
        if self.user.avatar:
            return self.user.avatar.url
        return None

    def __str__(self):
        return f"{self.user.full_name} - {self.category.name} ({self.region})"


class Service(models.Model):
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name="Usta"
    )
    name = models.CharField(max_length=200, verbose_name="Xizmat nomi")
    price = models.PositiveIntegerField(verbose_name="Xizmat narxi (so'm)")

    class Meta:
        verbose_name = "Xizmat"
        verbose_name_plural = "Xizmatlar"
        ordering = ['price']

    def __str__(self):
        return f"{self.name} - {self.price:,} so'm ({self.master.user.full_name})"


class Rating(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ratings_given',
        verbose_name="Baho beruvchi foydalanuvchi"
    )
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name="Usta"
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Baho (1-5)"
    )
    comment = models.TextField(blank=True, default="", verbose_name="Fikr / Sharh")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Baho berilgan vaqt")

    class Meta:
        verbose_name = "Reyting / Baho"
        verbose_name_plural = "Reytinglar"
        ordering = ['-created_at']
        constraints = [
            UniqueConstraint(
                fields=['user', 'master'],
                name='unique_user_master_rating'
            )
        ]

    def clean(self):
        super().clean()
        if self.master and self.user_id == self.master.user_id:
            raise ValidationError("Usta o'ziga o'zi baho bera olmaydi.")
        if self.score < 1 or self.score > 5:
            raise ValidationError("Baho faqat 1 dan 5 gacha bo'lishi kerak.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
        self.master.update_rating_stats()

    def delete(self, *args, **kwargs):
        master = self.master
        super().delete(*args, **kwargs)
        master.update_rating_stats()

    def __str__(self):
        return f"{self.user.full_name} -> {self.master.user.full_name}: {self.score} yulduz"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name="Foydalanuvchi"
    )
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name="Saqlangan usta"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Saqlangan usta"
        verbose_name_plural = "Saqlangan ustalar"
        ordering = ['-created_at']
        constraints = [
            UniqueConstraint(
                fields=['user', 'master'],
                name='unique_user_favorite_master'
            )
        ]

    def __str__(self):
        return f"{self.user.full_name} saqlagan: {self.master.user.full_name}"


class PortfolioWork(models.Model):
    master = models.ForeignKey(
        Master,
        on_delete=models.CASCADE,
        related_name='portfolio',
        verbose_name="Usta"
    )
    title = models.CharField(max_length=200, verbose_name="Ish nomi")
    description = models.TextField(blank=True, default="", verbose_name="Bajarilgan ish tavsifi")
    image = models.ImageField(upload_to='portfolio/', null=True, blank=True, verbose_name="Rasm")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Qo'shilgan sana")

    class Meta:
        verbose_name = "Bajarilgan ish"
        verbose_name_plural = "Bajarilgan ishlar (Portfolio)"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.master.user.full_name})"
