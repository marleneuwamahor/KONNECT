import uuid

from django.db import models


class Course(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "public", "Public"
        PRIVATE = "private", "Private"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    teacher = models.ForeignKey(
        "accounts.Teacher",
        on_delete=models.PROTECT,
        related_name="courses",
    )
    approved_by = models.ForeignKey(
        "accounts.AdminProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_courses",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=20,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
    )
    course_limit = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    class Meta:
        db_table = "courses"
        ordering = ["title"]

    def __str__(self):
        return self.title


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    student = models.ForeignKey(
        "accounts.Student",
        on_delete=models.CASCADE,
        related_name="enrollments",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "enrollments"
        ordering = ["-enrolled_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["course", "student"],
                name="unique_student_course_enrollment",
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.course}"

class LiveSession(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="live_sessions",
    )

    #  The 100ms room identifier used by the backend
    provider_room_id = models.CharField(
        max_length=255,
        blank=True,
    )

    join_link = models.URLField(max_length=1000, blank=True)
    tools_enabled = models.JSONField(default=list, blank=True)

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    join_deadline = models.DateTimeField()
    attendance_cutoff = models.DateTimeField()

    class Meta:
        db_table = "live_sessions"
        ordering = ["starts_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_at__gt=models.F("starts_at")),
                name="live_session_end_after_start",
            ),
        ]

    def save(self, *args, **kwargs):
        from datetime import timedelta

        self.join_deadline = self.starts_at + timedelta(minutes=15)
        self.attendance_cutoff = self.ends_at - timedelta(minutes=15)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.course.title} - {self.starts_at}"


class Attendance(models.Model):
    class Status(models.TextChoices):
        PRESENT = "present", "Present"
        ABSENT = "absent", "Absent"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    live_session = models.ForeignKey(
        LiveSession,
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    student = models.ForeignKey(
        "accounts.Student",
        on_delete=models.CASCADE,
        related_name="attendance_records",
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ABSENT,
    )
    joined_at = models.DateTimeField(null=True, blank=True)
    left_at = models.DateTimeField(null=True, blank=True)
    auto_marked = models.BooleanField(default=False)
    marked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "attendance"
        constraints = [
            models.UniqueConstraint(
                fields=["live_session", "student"],
                name="unique_session_student_attendance",
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.live_session}"
    
from django.core.validators import MinValueValidator


class Assignment(models.Model):
    class Type(models.TextChoices):
        QUIZ = "quiz", "Quiz"
        EXERCISE = "exercise", "Exercise"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
    )
    title = models.CharField(max_length=255)
    due_at = models.DateTimeField()
    max_score = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    class Meta:
        db_table = "assignments"
        ordering = ["due_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_score__gte=1),
                name="assignment_max_score_at_least_one",
            ),
        ]

    def __str__(self):
        return f"{self.title} - {self.course.title}"


class Submission(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    student = models.ForeignKey(
        "accounts.Student",
        on_delete=models.CASCADE,
        related_name="submissions",
    )
    answers = models.JSONField(
        default=dict,
        help_text="The student's submitted answers in JSON format.",
    )
    score = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    teacher_feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "submissions"
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.student} - {self.assignment.title}"
class Exam(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="exams",
    )
    title = models.CharField(max_length=255)
    exam_date = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )
    total_marks = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
    )

    class Meta:
        db_table = "exams"
        ordering = ["exam_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(duration_minutes__gte=1),
                name="exam_duration_at_least_one",
            ),
            models.CheckConstraint(
                condition=models.Q(total_marks__gte=1),
                name="exam_total_marks_at_least_one",
            ),
        ]

    def __str__(self):
        return f"{self.title} - {self.course.title}"


class Grade(models.Model):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    exam = models.ForeignKey(
        Exam,
        on_delete=models.CASCADE,
        related_name="grades",
    )
    student = models.ForeignKey(
        "accounts.Student",
        on_delete=models.CASCADE,
        related_name="exam_grades",
    )
    graded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.PROTECT,
        related_name="grades_awarded",
    )
    score = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    grade_letter = models.CharField(max_length=5, blank=True)
    teacher_feedback = models.TextField(blank=True)
    graded_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "grades"
        ordering = ["-graded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["exam", "student"],
                name="unique_exam_student_grade",
            ),
            models.CheckConstraint(
                condition=models.Q(score__gte=0),
                name="exam_grade_score_nonnegative",
            ),
        ]

    def __str__(self):
        return f"{self.student} - {self.exam.title}: {self.score}"
