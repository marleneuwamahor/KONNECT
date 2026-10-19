from rest_framework.routers import DefaultRouter

from .views import LiveSessionViewSet
from .attendance_views import AttendanceViewSet
from .catalog_views import CourseViewSet, EnrollmentViewSet
from .assignment_views import AssignmentViewSet, SubmissionViewSet


router = DefaultRouter()

router.register("live-sessions", LiveSessionViewSet, basename="live-session")
router.register("attendance", AttendanceViewSet, basename="attendance")
router.register("courses", CourseViewSet, basename="course")
router.register("enrollments", EnrollmentViewSet, basename="enrollment")
router.register("assignments", AssignmentViewSet, basename="assignment")
router.register("submissions", SubmissionViewSet, basename="submission")


urlpatterns = router.urls