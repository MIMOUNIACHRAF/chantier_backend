from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch, Sum, F
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
