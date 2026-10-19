from types import SimpleNamespace

from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from .admin import TeacherAdmin
from .models import AdminProfile, Teacher, User
from .teacher_registration_serializers import TeacherRegistrationSerializer


class AccountApprovalFlowTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            email="admin@example.com",
            raw_password="StrongPass123!",
            full_name="Admin User",
            role=User.Role.ADMIN,
            status=User.Status.ACTIVE,
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        self.admin_profile, _ = AdminProfile.objects.get_or_create(user=self.admin_user)

    def test_teacher_registration_defaults_to_pending_verification(self):
        serializer = TeacherRegistrationSerializer(data={
            "full_name": "Teacher Name",
            "email": "teacher@example.com",
            "password": "StrongPass123!",
            "full_legal_name": "Teacher Legal Name",
            "display_name": "Teacher Display",
            "country": "Kenya",
            "bio": "Experienced educator",
            "subjects_expertise": ["Math"],
            "languages": ["English"],
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        teacher = serializer.save()

        self.assertEqual(teacher.user.status, User.Status.PENDING)
        self.assertFalse(teacher.user.is_active)
        self.assertEqual(teacher.verification_status, Teacher.VerificationStatus.PENDING)

    def test_teacher_admin_approval_sets_user_active_and_verified(self):
        teacher_user = User.objects.create_user(
            email="teacher@example.com",
            raw_password="StrongPass123!",
            full_name="Teacher User",
            role=User.Role.TEACHER,
            status=User.Status.PENDING,
            is_active=False,
        )
        teacher = Teacher.objects.create(
            user=teacher_user,
            full_legal_name="Teacher User",
            display_name="Teacher Display",
            verification_status=Teacher.VerificationStatus.PENDING,
        )

        request = SimpleNamespace(user=self.admin_user)
        teacher_admin = TeacherAdmin(Teacher, AdminSite())
        teacher_admin.approve_selected_teachers(request, Teacher.objects.filter(pk=teacher.pk))

        teacher.refresh_from_db()
        teacher_user.refresh_from_db()

        self.assertEqual(teacher_user.status, User.Status.ACTIVE)
        self.assertTrue(teacher_user.is_active)
        self.assertEqual(teacher.verification_status, Teacher.VerificationStatus.VERIFIED)
        self.assertEqual(teacher.verified_by, self.admin_profile)
