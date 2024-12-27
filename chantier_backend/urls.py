from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from chantier.views import ChantierViewSet, ListeMateriauxViewSet, BonCommandeViewSet,ChantierBonCommandeViewSet
from chantier.models import Chantier

router = DefaultRouter()
router.register(r'chantiers', ChantierViewSet)
router.register(r'materiaux', ListeMateriauxViewSet)
router.register(r'bons-commande', BonCommandeViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/',include('chantier.urls')),
    path('api/chantier/<int:chantier_id>/bons-commande/', ChantierBonCommandeViewSet.as_view({'get': 'list'})),
]
