from rest_framework.routers import DefaultRouter
from chat import views


router = DefaultRouter()
router.register(r"(?P<event_id>[^/.]+)/chat", views.MessageViewSet, basename="chat")
urlpatterns = router.urls
