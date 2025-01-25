from chantier.models import BonCommande,ListeMateriaux
from django_filters.rest_framework import FilterSet, DateFilter, CharFilter
from django.db.models import Q


class BonCommandeFilter(FilterSet):
    date_min = DateFilter(field_name="date", lookup_expr='gte')  # Date après ou égale
    date_max = DateFilter(field_name="date", lookup_expr='lte')  # Date avant ou égale
    reference = CharFilter(method='filter_reference')  # Recherche avancée par référence
    chantier = CharFilter(method='filter_chantier')  # Filtrer par ID ou nom du chantier
    partie_type = CharFilter(field_name="partie__type")  # Filtrer par type de partie (gros œuvre ou finition)
    
    class Meta:
        model = BonCommande
        fields = ['date', 'reference', 'chantier', 'partie_type']

    def filter_reference(self, queryset, name, value):
        # Filtrage avancé par référence exacte ou partielle
        return queryset.filter(
            Q(reference__iexact=value) | Q(reference__icontains=value)
        ).distinct()

    def filter_chantier(self, queryset, name, value):
        # Permet de filtrer par ID ou nom de chantier
        return queryset.filter(
            Q(partie__chantier__id=value) | Q(partie__chantier__nom__icontains=value) | Q(partie__chantier__numero__iexact=value)
        ).distinct()
        
class ListeMateriauxFilter(FilterSet):
    type = CharFilter(method='filter_type')  # 'iexact' pour comparaison insensible à la casse
    nom = CharFilter(field_name='name', lookup_expr='icontains') 
    class Meta:
        model = ListeMateriaux
        fields = ['type','nom']
    def filter_type(self, queryset, name, value):
        # Permet de filtrer par ID ou nom de chantier
        return queryset.filter(
           Q(type__iexact=value)  | Q(type__iexact="main_doeuvre") 
        ).distinct()
