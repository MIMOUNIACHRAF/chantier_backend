from rest_framework import serializers
from .models import Chantier, ListeMateriaux, BonCommande, MateriauBonCommande


class ListeMateriauxSerializer(serializers.ModelSerializer):
    class Meta:
        model = ListeMateriaux
        fields = '__all__'
        
class ChantierSerializer(serializers.ModelSerializer):
    cout_total_materiaux = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_main_oeuvre = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Chantier
        fields = ['id', 'numero', 'nom', 'cout_total_materiaux', 'cout_total_main_oeuvre']

class ChantierMateriauxCostSerializer(serializers.Serializer):
    chantier_name = serializers.CharField()
    total_materiaux_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
    materiaux_cout = serializers.ListField(
        child=serializers.DictField(
            child=serializers.CharField()
        )
    )
class ManualMaterialSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.DecimalField(max_digits=10, decimal_places=2)
    unit = serializers.CharField(max_length=50)

class MateriauBonCommandeSerializer(serializers.ModelSerializer):
    materiau = serializers.PrimaryKeyRelatedField(queryset=ListeMateriaux.objects.all())
    materiau_name = serializers.CharField(source='materiau.name', read_only=True)
    cout_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = MateriauBonCommande
        fields = ['id', 'materiau','materiau_name', 'quantite', 'unite', 'cout_total']


class BonCommandeSerializer(serializers.ModelSerializer):
    materiaux = MateriauBonCommandeSerializer(many=True)
    cout_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    chantier_name = serializers.CharField(source='chantier.nom', read_only=True)
    chantier_numero = serializers.CharField(source='chantier.numero', read_only=True)
    chantier = serializers.PrimaryKeyRelatedField(queryset=Chantier.objects.all())
    cout_total_chantier = serializers.DecimalField(max_digits=10, decimal_places=2,source='chantier.cout_total_materiaux', read_only=True)
    class Meta:
        model = BonCommande
        fields = ['id', 'reference', 'date','chantier', 'chantier_name','chantier_numero', 'materiaux', 'cout_total','cout_total_chantier']

    def create(self, validated_data):
        materiaux_data = validated_data.pop('materiaux',[])
        bon_commande = BonCommande.objects.create(**validated_data)
        for materiau_data in materiaux_data:
            MateriauBonCommande.objects.create(bon_commande=bon_commande, **materiau_data)
        return bon_commande
    def update(self, instance, validated_data):
        # Mise à jour des matériaux
        materiaux_data = validated_data.pop('materiaux', None)
        
        if materiaux_data is not None:
            # Supprimer les anciens matériaux associés
            instance.materiaux.all().delete()
            
            # Ajouter les nouveaux matériaux
            for materiau_data in materiaux_data:
                MateriauBonCommande.objects.create(bon_commande=instance, **materiau_data)
        
        # Mettre à jour les autres champs du bon de commande
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance


