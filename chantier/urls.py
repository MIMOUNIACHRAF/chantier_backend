from django.urls import path
from . import views
urlpatterns = [
    path('chantier/<int:chantier_id>/bons-commande/', views.ChantierBonCommandeViewSet.as_view({'get': 'list'})),
    path('bon-commande/<int:bon_commande_id>/', views.BonCommandeDetailView.as_view(), name='bon-commande-detail'),
    path('bon-commande/<int:bon_commande_id>/materiaux/<int:materiau_id>/', views.MateriauBonCommandeDetailView.as_view(), name='materiau-bon-commande-detail'),
    path('bon-commandes/<int:bon_commande_id>/materiaux/', views.add_materiau_to_bon_commande, name='add_materiau_to_bon_commande'),
    path('bon-commandes/<int:bon_commande_id>/materiaux/<int:materiau_id>/', views.delete_materiau_from_bon_commande, name='delete_materiau_from_bon_commande'),
    path('chantier/<int:chantier_id>/materiaux-cost/', views.ChantierMateriauxTotalsView.as_view(), name='chantier-materiaux-cost'),
]
