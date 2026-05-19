from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from chantier.views import (
    BonCommandeViewSet,
    ChantierBonCommandeViewSet,
    ChantierViewSet,
    ListeMateriauxViewSet,
    OptionMateriauViewSet,
    PartieChantierViewSet,
)

router = DefaultRouter()
router.register(r'chantiers', ChantierViewSet)
router.register(r'parties', PartieChantierViewSet)
router.register(r'materiaux', ListeMateriauxViewSet)
router.register(r'options', OptionMateriauViewSet)
router.register(r'bons-commande', BonCommandeViewSet, basename='boncommande')

urlpatterns = [
    path('admin/', admin.site.urls),

    # ── JWT Auth ──────────────────────────────────────────────────────────────
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),

    # ── API Resources ─────────────────────────────────────────────────────────
    path('api/', include(router.urls)),
    path('api/', include('chantier.urls')),
]
