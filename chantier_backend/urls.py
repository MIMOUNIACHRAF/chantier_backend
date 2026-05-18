from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
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
    path('api/', include(router.urls)),
    path('api/', include('chantier.urls')),
]
