from datetime import date, timedelta
from decimal import Decimal

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch, Sum, F, Q, Case, When, DecimalField, Value, Count
from django.db.models.functions import Coalesce
from .models import (
    Chantier,
    PartieChantier,
    ListeMateriaux,
    BonCommande,
    MateriauBonCommande,
    OptionMateriau,
)
from .serializers import (
    ChantierSerializer,
    PartieChantierSerializer,
    ListeMateriauxSerializer,
    BonCommandeSerializer,
    BonCommandeListSerializer,
    MateriauBonCommandeSerializer,
    OptionMateriauSerializer,
)
from chantier.filters import BonCommandeFilter, ListeMateriauxFilter


def _bc_queryset():
    return BonCommande.objects.select_related(
        'partie__chantier', 'paiement'
    ).prefetch_related(
        Prefetch(
            'materiaux',
            queryset=MateriauBonCommande.objects.select_related('materiau', 'option'),
        )
    ).order_by('-date', '-id')


# ---------------------------------------------------------------------------
# Matériaux / Options
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_options_by_materiau(request, materiau_id):
    try:
        materiau = ListeMateriaux.objects.get(id=materiau_id)
    except ListeMateriaux.DoesNotExist:
        return Response({'detail': 'Materiau not found.'}, status=status.HTTP_404_NOT_FOUND)
    serializer = OptionMateriauSerializer(materiau.options.all(), many=True)
    return Response(serializer.data)


@api_view(['POST', 'PUT'])
@permission_classes([IsAuthenticated])
def add_or_update_option(request, materiau_id):
    try:
        materiau = ListeMateriaux.objects.get(id=materiau_id)
    except ListeMateriaux.DoesNotExist:
        return Response({'detail': 'Materiau not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        serializer = OptionMateriauSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(materiau=materiau)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # PUT
    option_id = request.data.get('id')
    try:
        option = OptionMateriau.objects.get(id=option_id, materiau=materiau)
    except OptionMateriau.DoesNotExist:
        return Response({'detail': 'Option not found.'}, status=status.HTTP_404_NOT_FOUND)
    serializer = OptionMateriauSerializer(option, data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# ViewSets
# ---------------------------------------------------------------------------

class ChantierViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Chantier.objects.all().order_by('numero')
    serializer_class = ChantierSerializer


class OptionMateriauViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = OptionMateriau.objects.select_related('materiau').order_by('id')
    serializer_class = OptionMateriauSerializer


class PartieChantierViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = PartieChantier.objects.select_related('chantier').order_by('id')
    serializer_class = PartieChantierSerializer


class ListeMateriauxViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = ListeMateriaux.objects.prefetch_related('options').order_by('code')
    serializer_class = ListeMateriauxSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ListeMateriauxFilter


class BonCommandeViewSet(viewsets.ModelViewSet):
    """
    GET  /api/bons-commande/          → liste paginée (30/page), sérialiseur léger
    GET  /api/bons-commande/{id}/     → détail complet avec matériaux
    POST /api/bons-commande/          → création
    PUT  /api/bons-commande/{id}/     → mise à jour
    """
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = BonCommandeFilter

    def get_queryset(self):
        return _bc_queryset()

    def get_serializer_class(self):
        if self.action in ('retrieve', 'create', 'update', 'partial_update'):
            return BonCommandeSerializer
        return BonCommandeListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['chantier_cache'] = {}
        ctx['bc_totals_cache'] = {}
        ctx['bc_list_cache'] = {}
        return ctx


class ChantierBonCommandeViewSet(viewsets.ViewSet):
    """GET /api/chantier/{chantier_id}/bons-commande/?page=N"""
    permission_classes = [IsAuthenticated]

    def list(self, request, chantier_id=None):
        chantier = get_object_or_404(Chantier, id=chantier_id)
        qs = _bc_queryset().filter(partie__chantier=chantier)
        paginator = PageNumberPagination()
        paginator.page_size = 30
        page = paginator.paginate_queryset(qs, request)
        ctx = {'request': request, 'bc_list_cache': {}}
        if page is not None:
            serializer = BonCommandeListSerializer(page, many=True, context=ctx)
            return paginator.get_paginated_response(serializer.data)
        serializer = BonCommandeListSerializer(qs, many=True, context=ctx)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Vues détail (APIView)
# ---------------------------------------------------------------------------

class BonCommandeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, bon_commande_id):
        bon_commande = get_object_or_404(_bc_queryset(), id=bon_commande_id)
        ctx = {'chantier_cache': {}, 'bc_totals_cache': {}, 'request': request}
        serializer = BonCommandeSerializer(bon_commande, context=ctx)
        return Response(serializer.data)

    def put(self, request, bon_commande_id):
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        serializer = BonCommandeSerializer(bon_commande, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChantierMateriauxTotalsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, chantier_id):
        chantier = get_object_or_404(Chantier, id=chantier_id)
        materiaux_totaux = (
            MateriauBonCommande.objects
            .filter(bon_commande__partie__chantier=chantier)
            .values(
                material_name=F('materiau__name'),
                material_type=F('materiau__type'),
                option_type=F('option__type'),
                option_valeur=F('option__valeur'),
                material_code=F('materiau__code'),
                option_name=F('option__name'),
                bon_commande_type=F('bon_commande__type'),
            )
            .annotate(
                total_quantite=Sum('quantite'),
                total_cout=Sum(F('quantite') * F('prix_unitaire')),
            )
        )
        return Response({
            'chantier_id': chantier.id,
            'chantier_name': chantier.nom,
            'chantier_numero': chantier.numero,
            'cout_total_materiaux': chantier.cout_total_global,
            'materiaux_totaux': list(materiaux_totaux),
        })


class MateriauBonCommandeDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, bon_commande_id, materiau_id):
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        mbc = get_object_or_404(
            MateriauBonCommande.objects.select_related('materiau', 'option'),
            id=materiau_id, bon_commande=bon_commande,
        )
        return Response(MateriauBonCommandeSerializer(mbc).data)

    def put(self, request, bon_commande_id, materiau_id):
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        mbc = get_object_or_404(MateriauBonCommande, id=materiau_id, bon_commande=bon_commande)

        data = request.data.copy()
        option_id = data.get('option')
        if option_id:
            if not OptionMateriau.objects.filter(id=option_id).exists():
                return Response(
                    {'error': "L'option spécifiée n'existe pas."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            data['option'] = None

        serializer = MateriauBonCommandeSerializer(mbc, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        today = date.today()
        month_start = today.replace(day=1)
        prev_month_end = month_start - timedelta(days=1)
        prev_month_start = prev_month_end.replace(day=1)

        _D = DecimalField(max_digits=15, decimal_places=2)
        _Z = Value(Decimal('0'), output_field=_D)

        def csum(cond):
            return Coalesce(
                Sum(Case(When(cond, then=F('quantite') * F('prix_unitaire')), output_field=_D)),
                _Z,
            )

        fin = Q(option__isnull=False, option__type='finition')     | Q(option__isnull=True, materiau__type='finition')
        go  = Q(option__isnull=False, option__type='gros_oeuvre')  | Q(option__isnull=True, materiau__type='gros_oeuvre')
        mo  = Q(option__isnull=False, option__type='main_doeuvre') | Q(option__isnull=True, materiau__type='main_doeuvre')

        totals = MateriauBonCommande.objects.aggregate(
            ca_total       = Coalesce(Sum(F('quantite') * F('prix_unitaire'), output_field=_D), _Z),
            ca_espece      = csum(Q(bon_commande__paiement__type_paiement='espece')),
            ca_cheque      = csum(Q(bon_commande__paiement__type_paiement='cheque')),
            ca_go          = csum(go),
            ca_fin         = csum(fin),
            ca_mo          = csum(mo),
            ca_mois        = csum(Q(bon_commande__date__gte=month_start)),
            ca_mois_precedent = csum(Q(
                bon_commande__date__gte=prev_month_start,
                bon_commande__date__lte=prev_month_end,
            )),
        )

        # Budget total prévu sur tous les chantiers
        budget_total = Chantier.objects.aggregate(
            total=Coalesce(Sum('budget_previsionnel', output_field=_D), _Z)
        )['total']

        # Chantiers par statut
        chantiers_statut_qs = Chantier.objects.values('statut').annotate(count=Count('id'))
        chantiers_by_statut = {r['statut']: r['count'] for r in chantiers_statut_qs}

        # Bons de commande par statut
        bons_statut_qs = BonCommande.objects.values('statut').annotate(count=Count('id'))
        bons_by_statut = {r['statut']: r['count'] for r in bons_statut_qs}

        # Top 5 chantiers enrichis
        top_chantiers = list(
            Chantier.objects.annotate(
                ca=Coalesce(
                    Sum(
                        F('parties__bons_commande__materiaux__quantite') *
                        F('parties__bons_commande__materiaux__prix_unitaire'),
                        output_field=_D,
                    ),
                    _Z,
                ),
                nb_bons=Count('parties__bons_commande', distinct=True),
            ).order_by('-ca').values(
                'id', 'nom', 'numero', 'ca', 'statut',
                'budget_previsionnel', 'nb_bons'
            )[:5]
        )

        ctx = {'request': request, 'bc_list_cache': {}}
        derniers = BonCommandeListSerializer(_bc_queryset()[:8], many=True, context=ctx).data

        return Response({
            'stats': {
                'total_chantiers':      Chantier.objects.count(),
                'chantiers_en_cours':   chantiers_by_statut.get('en_cours', 0),
                'total_bons':           BonCommande.objects.count(),
                'bons_ce_mois':         BonCommande.objects.filter(date__gte=month_start).count(),
                'bons_en_attente':      bons_by_statut.get('en_attente', 0),
                'bons_livre':           bons_by_statut.get('livre', 0),
                'ca_total':             totals['ca_total'],
                'ca_espece':            totals['ca_espece'],
                'ca_cheque':            totals['ca_cheque'],
                'ca_ce_mois':           totals['ca_mois'],
                'ca_mois_precedent':    totals['ca_mois_precedent'],
                'budget_total_prevu':   budget_total,
            },
            'repartition': {
                'gros_oeuvre':  totals['ca_go'],
                'finition':     totals['ca_fin'],
                'main_doeuvre': totals['ca_mo'],
            },
            'chantiers_by_statut':    chantiers_by_statut,
            'bons_by_statut':         bons_by_statut,
            'top_chantiers':          top_chantiers,
            'derniers_bons_commande': derniers,
        })


# ---------------------------------------------------------------------------
# Matériaux d'un bon de commande
# ---------------------------------------------------------------------------

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_materiau_to_bon_commande(request, bon_commande_id):
    bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
    materiau = get_object_or_404(ListeMateriaux, id=request.data.get('materiau_id'))
    option_id = request.data.get('option_id')
    option = get_object_or_404(OptionMateriau, id=option_id) if option_id else None

    mbc = MateriauBonCommande.objects.create(
        bon_commande=bon_commande,
        materiau=materiau,
        quantite=request.data.get('quantite'),
        option=option,
        prix_unitaire=request.data.get('prix_unitaire'),
    )
    return Response(MateriauBonCommandeSerializer(mbc).data, status=status.HTTP_201_CREATED)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_materiau_from_bon_commande(request, bon_commande_id, materiau_id):
    mbc = get_object_or_404(MateriauBonCommande, id=materiau_id, bon_commande_id=bon_commande_id)
    mbc.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)
