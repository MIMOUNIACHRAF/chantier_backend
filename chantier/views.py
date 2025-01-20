from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import api_view
from django.shortcuts import get_object_or_404
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
    MateriauBonCommandeSerializer
)
from chantier.filters import BonCommandeFilter,ListeMateriauxFilter

from .serializers import OptionMateriauSerializer

@api_view(['GET'])
def get_options_by_materiau(request, materiau_id):
    try:
        # Récupérer le matériau à partir de son ID
        materiau = ListeMateriaux.objects.get(id=materiau_id)
    except ListeMateriaux.DoesNotExist:
        return Response({'detail': 'Materiau not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Récupérer les options associées au matériau
    options = materiau.options.all()

    # Sérialiser les options
    serializer = OptionMateriauSerializer(options, many=True)

    # Retourner les options sous forme de réponse JSON
    return Response(serializer.data, status=status.HTTP_200_OK)


# Gestion des chantiers
class ChantierViewSet(viewsets.ModelViewSet):
    queryset = Chantier.objects.all()
    serializer_class = ChantierSerializer


class OptionMateriauViewSet(viewsets.ModelViewSet):
    queryset = OptionMateriau.objects.all()
    serializer_class = OptionMateriauSerializer

# Gestion des parties de chantier (gros œuvre et finition)
class PartieChantierViewSet(viewsets.ModelViewSet):
    queryset = PartieChantier.objects.all()
    serializer_class = PartieChantierSerializer


# Gestion des matériaux
class ListeMateriauxViewSet(viewsets.ModelViewSet):
    queryset = ListeMateriaux.objects.all()
    serializer_class = ListeMateriauxSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = ListeMateriauxFilter 
    def create(self, request, *args, **kwargs):
        # Custom creation logic to handle options
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        # Custom update logic to handle options
        return super().update(request, *args, **kwargs)
    # def get_queryset(self):
    #     queryset = ListeMateriaux.objects.all()
    #     type_materiau = self.request.query_params.get('type', None)
    #     if type_materiau:
    #         queryset = queryset.filter(type=type_materiau)
    #     return queryset

@api_view(['POST', 'PUT'])
def add_or_update_option(request, materiau_id):
    try:
        materiau = ListeMateriaux.objects.get(id=materiau_id)
    except ListeMateriaux.DoesNotExist:
        return Response({"detail": "Materiau not found"}, status=status.HTTP_404_NOT_FOUND)

    # Si c'est une requête POST, on ajoute une nouvelle option
    if request.method == 'POST':
        serializer = OptionMateriauSerializer(data=request.data)
        if serializer.is_valid():
            # Relier l'option au matériau avant de sauvegarder
            option = serializer.save(materiau=materiau)  # Relier l'option au matériau
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Si c'est une requête PUT, on met à jour une option existante
    elif request.method == 'PUT':
        option_id = request.data.get('id')
        try:
            option = OptionMateriau.objects.get(id=option_id, materiau=materiau)
        except OptionMateriau.DoesNotExist:
            return Response({"detail": "Option not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = OptionMateriauSerializer(option, data=request.data)
        if serializer.is_valid():
            serializer.save()  # Sauvegarde de l'option mise à jour
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# Gestion des bons de commande
class BonCommandeViewSet(viewsets.ModelViewSet):
    queryset = BonCommande.objects.all()
    serializer_class = BonCommandeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = BonCommandeFilter


# Vue pour récupérer les bons de commande d'un chantier
class ChantierBonCommandeViewSet(viewsets.ViewSet):
    def list(self, request, chantier_id=None):
        chantier = get_object_or_404(Chantier, id=chantier_id)
        bons_commande = BonCommande.objects.filter(partie__chantier=chantier)
        serializer = BonCommandeSerializer(bons_commande, many=True)
        return Response(serializer.data)


# Vue pour les détails des bons de commande
class BonCommandeDetailView(APIView):
    def get(self, request, bon_commande_id):
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        serializer = BonCommandeSerializer(bon_commande)
        return Response(serializer.data)

    def put(self, request, bon_commande_id):
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        serializer = BonCommandeSerializer(bon_commande, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from django.db.models import Sum, F
# Vue pour les totaux de matériaux d'un chantier
class ChantierMateriauxTotalsView(APIView):
    def get(self, request, chantier_id, *args, **kwargs):
        try:
            # Récupérer le chantier
            chantier = Chantier.objects.get(id=chantier_id)

            # Calculer les totaux pour chaque matériau
            materiaux_totaux = (
                MateriauBonCommande.objects
                .filter(bon_commande__partie__chantier=chantier)
                .values(material_name=F('materiau__name'),material_type=F('materiau__type'),option_type=F('option__type'),
                        option_valeur=F('option__valeur'),material_code=F('materiau__code'),option_name=F('option__name'),
                        bon_commande_type = F('bon_commande__type'))
                
                .annotate(
                    total_quantite=Sum('quantite'),
                    total_cout=Sum(F('quantite') * F('prix_unitaire'))
                )
            )

            # Construire la réponse
            response_data = {
                "chantier_id": chantier.id,
                "chantier_name": chantier.nom,
                "chantier_numero": chantier.numero,
                "cout_total_materiaux": chantier.cout_total_global,
                "materiaux_totaux": list(materiaux_totaux)
            }

            return Response(response_data, status=status.HTTP_200_OK)
        except Chantier.DoesNotExist:
            return Response({"error": "Chantier non trouvé"}, status=status.HTTP_404_NOT_FOUND)


# Vue pour les matériaux dans un bon de commande
class MateriauBonCommandeDetailView(APIView):
    def get(self, request, bon_commande_id, materiau_id):
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        materiau_bon_commande = get_object_or_404(MateriauBonCommande, id=materiau_id, bon_commande=bon_commande)
        serializer = MateriauBonCommandeSerializer(materiau_bon_commande)
        return Response(serializer.data)

    def put(self, request, bon_commande_id, materiau_id):
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        materiau_bon_commande = get_object_or_404(MateriauBonCommande, id=materiau_id, bon_commande=bon_commande)
        serializer = MateriauBonCommandeSerializer(materiau_bon_commande, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def add_materiau_to_bon_commande(request, bon_commande_id):
    try:
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        materiau_id = request.data.get('materiau_id')
        quantite = request.data.get('quantite')
        unite = request.data.get('unite')
        prix_unitaire = request.data.get('prix_unitaire')

        materiau = get_object_or_404(ListeMateriaux, id=materiau_id)
        materiau_bon_commande = MateriauBonCommande.objects.create(
            bon_commande=bon_commande,
            materiau=materiau,
            quantite=quantite,
            unite=unite,
            prix_unitaire=prix_unitaire,
        )
        serializer = MateriauBonCommandeSerializer(materiau_bon_commande)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# Supprimer un matériau d'un bon de commande
@api_view(['DELETE'])
def delete_materiau_from_bon_commande(request, bon_commande_id, materiau_id):
    materiau_bon_commande = get_object_or_404(MateriauBonCommande, id=materiau_id)
    materiau_bon_commande.delete()
    return Response({"message": "Matériau supprimé avec succès."}, status=status.HTTP_204_NO_CONTENT)
