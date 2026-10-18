from rest_framework.routers import DefaultRouter

from .views import LiveSessionViewSet
from .attendance_views import AttendanceViewSet

router = DefaultRouter()
router.register(
    "live-sessions",
    LiveSessionViewSet,
    basename="live-session",
)
router.register(
    "attendance",
    AttendanceViewSet,
    basename="attendance",
)

urlpatterns = router.urls