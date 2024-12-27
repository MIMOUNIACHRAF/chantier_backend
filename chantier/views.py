from rest_framework import viewsets

from chantier.filters import BonCommandeFilter
from .models import Chantier, ListeMateriaux, BonCommande, MateriauBonCommande
from .serializers import ChantierSerializer, ListeMateriauxSerializer, BonCommandeSerializer


class ChantierViewSet(viewsets.ModelViewSet):
    queryset = Chantier.objects.all()
    serializer_class = ChantierSerializer


class ListeMateriauxViewSet(viewsets.ModelViewSet):
    queryset = ListeMateriaux.objects.all()
    serializer_class = ListeMateriauxSerializer
    
from django_filters.rest_framework import DjangoFilterBackend

class BonCommandeViewSet(viewsets.ModelViewSet):
    queryset = BonCommande.objects.all()
    serializer_class = BonCommandeSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = BonCommandeFilter

    
from rest_framework.response import Response
class ChantierBonCommandeViewSet(viewsets.ViewSet):
    def list(self, request, chantier_id=None):
        chantier = Chantier.objects.get(id=chantier_id)
        bons_commande = BonCommande.objects.filter(chantier=chantier)
        serializer = BonCommandeSerializer(bons_commande, many=True)
        return Response(serializer.data)
    

from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework import status
class BonCommandeDetailView(APIView):
    def get(self, request, bon_commande_id):
        # Récupérer le bon de commande par ID
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        serializer = BonCommandeSerializer(bon_commande)
        return Response(serializer.data)

    def put(self, request, bon_commande_id):
        # Récupérer le bon de commande par ID
        bon_commande = get_object_or_404(BonCommande, id=bon_commande_id)
        serializer = BonCommandeSerializer(bon_commande, data=request.data, partial=True)
        
        if serializer.is_valid():
            # Mettre à jour le bon de commande
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

from django.db.models import Sum, F
class ChantierMateriauxTotalsView(APIView):
   def get(self, request, chantier_id, *args, **kwargs):
        try:
            # Récupérer le chantier
            chantier = Chantier.objects.get(id=chantier_id)

            # Récupérer les bons de commande associés au chantier
            bons_commandes = BonCommande.objects.filter(chantier=chantier).prefetch_related('materiaux')

            # Initialiser un dictionnaire pour regrouper les matériaux par ID
            materiaux_totaux = {}

            for bon in bons_commandes:
                for materiau_bon in bon.materiaux.all():
                    materiau_id = materiau_bon.materiau.id  # ID du matériau
                    materiau_name = materiau_bon.materiau.name  # Nom du matériau (ajustez selon votre modèle)
                    quantite = float(materiau_bon.quantite)
                    cout_total = float(materiau_bon.cout_total)

                    if materiau_id not in materiaux_totaux:
                        materiaux_totaux[materiau_id] = {
                            'materiau_name': materiau_name,
                            'total_quantite': 0,
                            'total_cout': 0
                        }
                    
                    # Ajouter la quantité et le coût total
                    materiaux_totaux[materiau_id]['total_quantite'] += quantite
                    materiaux_totaux[materiau_id]['total_cout'] += cout_total
            
            # Préparer la réponse formatée
            response_data = [
                {
                    'materiau_id': materiau_id,
                    'materiau_name': data['materiau_name'],
                    'total_quantite': data['total_quantite'],
                    'total_cout': data['total_cout']
                }
                for materiau_id, data in materiaux_totaux.items()
            ]

            return Response(response_data, status=status.HTTP_200_OK)

        except Chantier.DoesNotExist:
            return Response({'error': 'Chantier non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
from .serializers import MateriauBonCommandeSerializer
from rest_framework.exceptions import NotFound
class MateriauBonCommandeDetailView(APIView):
    def get(self, request, bon_commande_id, materiau_id):
        try:
            # Vérifier que le bon de commande existe
            bon_commande = BonCommande.objects.get(id=bon_commande_id)
        except BonCommande.DoesNotExist:
            raise NotFound("Bon de commande non trouvé.")
        
        try:
            # Vérifier que le matériau existe dans ce bon de commande
            materiau = MateriauBonCommande.objects.get(id=materiau_id, bon_commande=bon_commande)
        except MateriauBonCommande.DoesNotExist:
            raise NotFound("Matériau non trouvé dans ce bon de commande.")
        
        # Sérialiser le matériau
        serializer = MateriauBonCommandeSerializer(materiau)
        return Response(serializer.data)

    def put(self, request, bon_commande_id, materiau_id):
        try:
            # Vérifier que le bon de commande existe
            bon_commande = BonCommande.objects.get(id=bon_commande_id)
        except BonCommande.DoesNotExist:
            raise NotFound("Bon de commande non trouvé.")
        
        try:
            # Vérifier que le matériau existe dans ce bon de commande
            materiau = MateriauBonCommande.objects.get(id=materiau_id, bon_commande=bon_commande)
        except MateriauBonCommande.DoesNotExist:
            raise NotFound("Matériau non trouvé dans ce bon de commande.")
        
        # Sérialiser et mettre à jour le matériau
        serializer = MateriauBonCommandeSerializer(materiau, data=request.data, partial=True)
        
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
from rest_framework.decorators import api_view
@api_view(['POST'])
def add_materiau_to_bon_commande(request, bon_commande_id):
    try:
        bon_commande = BonCommande.objects.get(id=bon_commande_id)
    except BonCommande.DoesNotExist:
        return Response({"error": "Bon de commande non trouvé"}, status=status.HTTP_404_NOT_FOUND)

    materiau_id = request.data.get('materiau_id')
    quantite = request.data.get('quantite')
    unite = request.data.get('unite')

    # Récupérer le matériau
    try:
        materiau = ListeMateriaux.objects.get(id=materiau_id)
    except ListeMateriaux.DoesNotExist:
        return Response({"error": "Matériau non trouvé"}, status=status.HTTP_404_NOT_FOUND)

    # Créer un nouvel enregistrement dans la table de liaison entre BonCommande et Materiau
    materiau_bon_commande = MateriauBonCommande.objects.create(
        bon_commande=bon_commande,
        materiau=materiau,
        quantite=quantite,
        unite=unite,
    )

    # Sérialiser le matériau ajouté
    serializer = MateriauBonCommandeSerializer(materiau_bon_commande)
    return Response(serializer.data, status=status.HTTP_201_CREATED)

@api_view(['DELETE'])
def delete_materiau_from_bon_commande(request, bon_commande_id, materiau_id):
    
    try:
        # Récupérer le bon de commande et le matériau
        bon_commande_materiau = MateriauBonCommande.objects.get(id=materiau_id)
    except MateriauBonCommande.DoesNotExist:
        return Response({"error": "Matériau non trouvé dans ce bon de commande."}, status=status.HTTP_404_NOT_FOUND)
    
    # Supprimer le matériau
    bon_commande_materiau.delete()

    # Retourner une réponse réussie
    return Response({"message": "Matériau supprimé avec succès."}, status=status.HTTP_204_NO_CONTENT)