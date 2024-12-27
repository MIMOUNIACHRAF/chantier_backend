from chantier.models import BonCommande
from django_filters.rest_framework import FilterSet, DateFilter, CharFilter
from django.db.models import Q
class BonCommandeFilter(FilterSet):
    date_min = DateFilter(field_name="date", lookup_expr='gte')  # Date après ou égale
    date_max = DateFilter(field_name="date", lookup_expr='lte')  # Date avant ou égale
    reference = CharFilter(method='filter_reference')  # Recherche partielle
    chantier = CharFilter(field_name="chantier__id")  # Filtrer par ID de chantier

    class Meta:
        model = BonCommande
        fields = ['date', 'reference', 'chantier']
        
    def filter_reference(self, queryset, name, value):
        respone = queryset.filter(
            Q(reference__exact=value))
        respone_2 =  queryset.filter(
            Q(reference__icontains=value))
        if respone and respone_2:
            return respone
        elif respone_2:
            return respone_2
        return queryset.none()
        