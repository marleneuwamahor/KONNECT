
import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", User.Status.ACTIVE)
        extra_fields.setdefault("role", User.Role.ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("A superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("A superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        TEACHER = "teacher", "Teacher"
        STUDENT = "student", "Student"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        SUSPENDED = "suspended", "Suspended"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    managed_by = models.ForeignKey(
        "accounts.AdminProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_users",
    )
    full_name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(default=timezone.now)

    # Django authentication and authorization fields.
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # Additional profile fields from your existing model.
    profile_image = models.URLField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    bio = models.TextField(blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"

    def __str__(self):
        return f"{self.full_name} <{self.email}>"


class Student(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    username = models.CharField(max_length=30, unique=True)
    profile_picture_url = models.URLField(blank=True)
    bio = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    grade_level = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "students"

    def __str__(self):
        return f"{self.username} - {self.user.full_name}"


class Teacher(models.Model):
    class VerificationStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        VERIFIED = "verified", "Verified"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="teacher_profile",
    )
    verified_by = models.ForeignKey(
        "accounts.AdminProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_teachers",
    )
    full_legal_name = models.CharField(max_length=200)
    display_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=30, blank=True)
    country = models.CharField(max_length=100, blank=True)
    legal_name_on_documents = models.CharField(max_length=200, blank=True)
    cv_url = models.URLField(blank=True)
    degree_certificate_url = models.URLField(blank=True)
    profile_picture_url = models.URLField(blank=True)
    headline = models.CharField(max_length=200, blank=True)
    years_of_experience = models.CharField(max_length=50, blank=True)
    bio = models.TextField(blank=True)
    subjects_expertise = models.JSONField(default=list, blank=True)
    education_level_taught = models.CharField(max_length=150, blank=True)
    languages = models.JSONField(default=list, blank=True)
    current_institution = models.CharField(max_length=200, blank=True)
    teaching_mode = models.CharField(max_length=100, blank=True)
    portfolio_url = models.URLField(blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )

    class Meta:
        db_table = "teachers"

    def __str__(self):
        return f"{self.display_name or self.full_legal_name} - {self.user.email}"


class AdminProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="admin_profile",
    )
    profile_picture_url = models.URLField(blank=True)
    admin_level = models.CharField(max_length=50, default="standard")

    class Meta:
        db_table = "admin_profiles"

    def __str__(self):
        return f"{self.admin_level}: {self.user.email}"


@receiver(post_save, sender=User)
def create_admin_profile(sender, instance, created, **kwargs):
    if created and instance.role == User.Role.ADMIN:
        AdminProfile.objects.get_or_create(user=instance)
