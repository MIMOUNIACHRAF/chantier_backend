from django_filters.rest_framework import FilterSet, DateFilter, CharFilter
from django.db.models import Q
from chantier.models import BonCommande, ListeMateriaux


class BonCommandeFilter(FilterSet):
    date_min    = DateFilter(field_name='date', lookup_expr='gte')
    date_max    = DateFilter(field_name='date', lookup_expr='lte')
    reference   = CharFilter(method='filter_reference')
    chantier    = CharFilter(method='filter_chantier')
    partie_type = CharFilter(field_name='partie__type')

    class Meta:
        model  = BonCommande
        fields = ['date', 'reference', 'chantier', 'partie_type']

    def filter_reference(self, queryset, name, value):
        return queryset.filter(
            Q(reference__iexact=value) | Q(reference__icontains=value)
        ).distinct()

    def filter_chantier(self, queryset, name, value):
        return queryset.filter(
            Q(partie__chantier__id=value) |
            Q(partie__chantier__nom__icontains=value) |
            Q(partie__chantier__numero__iexact=value)
        ).distinct()


class ListeMateriauxFilter(FilterSet):
    type = CharFilter(field_name='type', lookup_expr='iexact')
    nom  = CharFilter(field_name='name', lookup_expr='icontains')

    class Meta:
        model  = ListeMateriaux
        fields = ['type', 'nom']
