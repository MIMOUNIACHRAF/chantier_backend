from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch, Sum, F
from .models import (
    Chantier,
    PartieChantier,
    ListeMateriaux,
    BonCommande,
    MateriauBonCommande,
    OptionMateriau
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
            queryset=MateriauBonCommande.objects.select_related('materiau', 'option')
        )
    )



@api_view(['GET'])
def get_options_by_materiau(request, materiau_id):
    try:
        materiau = ListeMateriaux.objects.get(id=materiau_id)
    except ListeMateriaux.DoesNotExist:
        return Response({'detail': 'Materiau not found.'}, status=status.HTTP_404_NOT_FOUND)
    options = materiau.options.all()
    serializer = OptionMateriauSerializer(options, many=True)
    return Response(serializer.data, status=status.HTTP_200_OK)


class ChantierViewSet(viewsets.ModelViewSet):
    queryset = Chantier.objects.all()
    serializer_class = ChantierSerializer


class OptionMateriauViewSet(viewsets.ModelViewSet):
    queryset = OptionMateriau.objects.all()
    serializer_class = OptionMateriauSerializer


class PartieChantierViewSet(viewsets.ModelViewSet):
    queryset = PartieChantier.objects.select_related('chantier')
    serializer_class = PartieChantierSerializer


class ListeMateriauxViewSet(viewsets.ModelViewSet):
    queryset = ListeMateriaux.objects.all()
    serializer_class = ListeMateriauxSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ListeMateriauxFilter

    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


@api_view(['POST', 'PUT'])
def add_or_update_option(request, materiau_id):
    try:
        materiau = ListeMateriaux.objects.get(id=materiau_id)
    except ListeMateriaux.DoesNotExist:
        return Response({"detail": "Materiau not found"}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'POST':
        serializer = OptionMateriauSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(materiau=materiau)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'PUT':
        option_id = request.data.get('id')
        try:
            option = OptionMateriau.objects.get(id=option_id, materiau=materiau)
        except OptionMateriau.DoesNotExist:
            return Response({"detail": "Option not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = OptionMateriauSerializer(option, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BonCommandeViewSet(viewsets.ModelViewSet):
    queryset = _bc_queryset()
    filter_backends = [DjangoFilterBackend]
    filterset_class = BonCommandeFilter

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return BonCommandeSerializer
        return BonCommandeListSerializer

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['chantier_cache'] = {}
        ctx['bc_totals_cache'] = {}
        return ctx


class ChantierBonCommandeViewSet(viewsets.ViewSet):
    def list(self, request, chantier_id=None):
        chantier = get_object_or_404(Chantier, id=chantier_id)
        bons_commande = _bc_queryset().filter(partie__chantier=chantier)
        serializer = BonCommandeListSerializer(bons_commande, many=True, context={'request': request})
        return Response(serializer.data)


class BonCommandeDetailView(APIView):
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
    def get(self, request, chantier_id, *args, **kwargs):
        try:
            chantier = Chantier.objects.get(id=chantier_id)
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
                    total_cout=Sum(F('quantite') * F('prix_unitaire'))
                )
            )
            response_data = {
                "chantier_id": chantier.id,
                "chantier_name": chantier.nom,
                "chantier_numero": chantier.numero,
                "cout_total_materiaux": chantier.cout_total_global,
                "materiaux_totaux": list(materiaux_totaux),
            }
            return Response(response_data, status=status.HTTP_200_OK)
        except Chantier.DoesNotExist:
            return Response({"error": "Chantier non trouvé"}, status=status.HTTP_404_NOT_FOUND)


from rest_framework.exceptions import ValidationError


class MateriauBonCommandeDetailView(APIView):
    def get(self, request, bon_commande_id, materiau_id):
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        materiau_bon_commande = get_object_or_404(
            MateriauBonCommande.objects.select_related('materiau', 'option'),
            id=materiau_id, bon_commande=bon_commande
        )
        serializer = MateriauBonCommandeSerializer(materiau_bon_commande)
        return Response(serializer.data)

    def put(self, request, bon_commande_id, materiau_id):
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        materiau_bon_commande = get_object_or_404(MateriauBonCommande, id=materiau_id, bon_commande=bon_commande)

        option_id = request.data.get('option')
        if option_id:
            try:
                request.data['option'] = OptionMateriau.objects.get(id=option_id).id
            except OptionMateriau.DoesNotExist:
                return Response({"error": "L'option spécifiée n'existe pas."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            request.data['option'] = None

        serializer = MateriauBonCommandeSerializer(materiau_bon_commande, data=request.data, partial=True)
        if serializer.is_valid():
            instance = serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def add_materiau_to_bon_commande(request, bon_commande_id):
    try:
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        materiau_id = request.data.get('materiau_id')
        quantite = request.data.get('quantite')
        option_id = request.data.get('option_id')
        prix_unitaire = request.data.get('prix_unitaire')

        materiau = get_object_or_404(ListeMateriaux, id=materiau_id)
        option = get_object_or_404(OptionMateriau, id=option_id) if option_id else None

        materiau_bon_commande = MateriauBonCommande.objects.create(
            bon_commande=bon_commande,
            materiau=materiau,
            quantite=quantite,
            option=option,
            prix_unitaire=prix_unitaire,
        )
        serializer = MateriauBonCommandeSerializer(materiau_bon_commande)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_materiau_from_bon_commande(request, bon_commande_id, materiau_id):
    materiau_bon_commande = get_object_or_404(MateriauBonCommande, id=materiau_id)
    materiau_bon_commande.delete()
    return Response({"message": "Matériau supprimé avec succès."}, status=status.HTTP_204_NO_CONTENT)
