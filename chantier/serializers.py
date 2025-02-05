from rest_framework import serializers
from .models import (Chantier, ListeMateriaux, BonCommande, MateriauBonCommande,
                    PartieChantier,OptionMateriau,Paiement)
from django.db.models import Sum,F

class OptionMateriauSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionMateriau
        fields = ['id','name','valeur','type','materiau']
    
    def create(self, validated_data):
        materiau = validated_data.get('materiau')  # Vérifier si le materiau est dans les données validées
        if not materiau:
            raise serializers.ValidationError("Le champ 'materiau' est requis.")
        
        # Créer l'option et l'associer au materiau
        option = OptionMateriau.objects.create(**validated_data)

        return option
        
class ListeMateriauxSerializer(serializers.ModelSerializer):
    options = OptionMateriauSerializer(many=True, read_only=True)
    class Meta:
        model = ListeMateriaux
        fields = ['id', 'code', 'name', 'type', 'options']
    def update(self, instance, validated_data):
        options_data = validated_data.pop('options', [])
        # Mettre à jour les autres champs de ListeMateriaux
        instance = super().update(instance, validated_data)
        
        # Mettre à jour les options
        for option_data in options_data:
            option_id = option_data.get('id', None)
            if option_id:
                option = OptionMateriau.objects.get(id=option_id)
                option.valeur = option_data['valeur']
                option.save()
            else:
                # Si c'est une nouvelle option, la créer
                OptionMateriau.objects.create(liste_materiau=instance, **option_data)
        
        return instance


from rest_framework import serializers
from .models import Chantier, MateriauBonCommande

class ChantierSerializer(serializers.ModelSerializer):
    cout_total_materiaux = serializers.ReadOnlyField()
    cout_total_main_oeuvre = serializers.ReadOnlyField()
    cout_total_materiaux_finition = serializers.ReadOnlyField()
    cout_total_materiaux_gros_oeuvre = serializers.ReadOnlyField()
    cout_total_main_oeuvre_gros_oeuvre = serializers.ReadOnlyField()
    cout_total_main_oeuvre_finition = serializers.ReadOnlyField()
    cout_total_global = serializers.SerializerMethodField()
    cout_total_espece = serializers.ReadOnlyField()
    cout_total_cheque = serializers.ReadOnlyField()
    # cout_total_global = serializers.ReadOnlyField()

    class Meta:
        model = Chantier
        fields = ['id', 'numero', 'nom', 'cout_total_materiaux', 'cout_total_main_oeuvre','cout_total_materiaux_gros_oeuvre','cout_total_materiaux_finition','cout_total_main_oeuvre_finition','cout_total_main_oeuvre_gros_oeuvre', 
                  'cout_total_global','cout_total_espece','cout_total_cheque']

    def get_cout_total_global(self, obj):
        # Somme des matériaux et de la main-d'œuvre
        return obj.cout_total_materiaux + obj.cout_total_main_oeuvre

class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = ['id', 'type_paiement', 'date_paiement', 'numero_cheque', 'nom_banque']

    def validate(self, data):
        if data['type_paiement'] == 'cheque':
            if not data.get('numero_cheque'):
                raise serializers.ValidationError("Le numéro de chèque est requis pour un paiement par chèque.")
            if not data.get('nom_banque'):
                raise serializers.ValidationError("Le nom de la banque est requis pour un paiement par chèque.")
        elif data['type_paiement'] == 'espece':
            if data.get('numero_cheque') or data.get('nom_banque'):
                raise serializers.ValidationError("Les champs 'numéro de chèque' et 'nom de banque' ne sont pas valides pour un paiement en espèces.")
        return data


class PartieChantierSerializer(serializers.ModelSerializer):
    cout_total_materiaux = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_main_oeuvre = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_chantier_materiaux_finition = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_chantier_materiaux_gros_oeuvre = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_main_oeuvre_finition  = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True) 
    cout_total_main_oeuvre_gros_oeuvre  = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_espece  = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_cheque  = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = PartieChantier
        fields = ['id', 'chantier', 'type', 'cout_total_materiaux', 'cout_total_main_oeuvre','cout_total_chantier_materiaux_finition','cout_total_main_oeuvre_finition','cout_total_main_oeuvre_gros_oeuvre',
                  'cout_total_chantier_materiaux_gros_oeuvre','cout_total_espece','cout_total_cheque']


class MateriauBonCommandeSerializer(serializers.ModelSerializer):
    materiau = serializers.CharField(required=False)
    materiau_id = serializers.CharField(source='materiau.id', read_only=True)
    materiau_name = serializers.CharField(source='materiau.name', read_only=True)
    type_materiau = serializers.CharField(source='materiau.type', read_only=True)
    code = serializers.CharField(source='materiau.code', read_only=True)
    cout_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    prix_unitaire = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    option = serializers.SerializerMethodField()
    option_id = serializers.IntegerField(write_only=True, required=False)  # Nouveau champ pour l'option en entrée

    # option_code =   serializers.CharField(source='option.valeur', read_only=True)
    
    class Meta:
        model = MateriauBonCommande
        fields = ['id','materiau_id', 'materiau','materiau_name','prix_unitaire', 'quantite', 'code', 'type_materiau', 'cout_total','option','option_id']
    def validate_option_id(self, value):
        
        try:
            return OptionMateriau.objects.get(id=value)
        except OptionMateriau.DoesNotExist:
            raise serializers.ValidationError("L'option spécifiée n'existe pas.")
        
    def validate_materiau_id(self, value):
        # Si la valeur est "autre", laissez la gestion au `create`
        if value == "autre":
            return value
        # Vérifiez si le matériau existe dans la base
        print(value)
        try:
            return ListeMateriaux.objects.get(id=value)
        except (ListeMateriaux.DoesNotExist, ValueError):
            raise serializers.ValidationError(f"Le matériau spécifié avec l'ID {value} n'existe pas.")


    def update(self, instance, validated_data):
        
        if 'materiau_id' in self.initial_data:
            try:
                instance.materiau = ListeMateriaux.objects.get(id=self.initial_data['materiau_id'])
            except ListeMateriaux.DoesNotExist:
                raise serializers.ValidationError(f"Le matériau spécifié avec l'ID {self.initial_data['materiau_id']} n'existe pas.")

        
        # Mise à jour de l'option
        print('initial data is : ',self.initial_data)
        if 'option' in self.initial_data:
            option_data = self.initial_data['option']
            print(option_data)
            if option_data: 
                try:
                    instance.option = OptionMateriau.objects.get(id=option_data)
                except OptionMateriau.DoesNotExist:
                    raise serializers.ValidationError(f"L'option spécifiée avec l'ID {option_data['option']} n'existe pas.")
            else:
                instance.option =None

                
            # Si c'est un ID
        else:   
            raise serializers.ValidationError("Le champ 'option' doit être soit un ID, soit un objet valide.")

        # Mise à jour du prix unitaire
        if 'prix_unitaire' in self.initial_data:
            instance.prix_unitaire = self.initial_data['prix_unitaire']

        # Mise à jour de la quantité
        # instance.quantite = validated_data.get('quantite', instance.quantite)
        if 'quantite' in self.initial_data:
            instance.quantite = self.initial_data['quantite']
        instance.save()

        # Affichage de l'instance pour débogage
        print('Instance mise à jour :', instance)

        return instance
   
        
    def get_option(self, obj):
        if obj.option:
            return {
                "option_id":obj.option.id,
                "code_option": obj.option.valeur,
                "type_option": obj.option.type,
                "nom_option": obj.option.name,
                "code_materiau": obj.materiau.code if obj.materiau else None,
                "nom_materiau": obj.materiau.name if obj.materiau else None,
                "type_materiau": obj.materiau.type if obj.materiau else None,
            }
        return None

class BonCommandeSerializer(serializers.ModelSerializer):
    materiaux = MateriauBonCommandeSerializer(many=True, read_only=True)
    paiement = PaiementSerializer()
    cout_total_materiaux = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_main_oeuvre = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_global_BC = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    chantier_id = serializers.CharField(source='partie.chantier.id', read_only=True)
    chantier_name = serializers.CharField(source='partie.chantier.nom', read_only=True)
    chantier_numero = serializers.CharField(source='partie.chantier.numero', read_only=True)
    # cout_total_chantier_espece = serializers.DecimalField(max_digits=10, decimal_places=2,source='partie.chantier.cout_total_chantier_espece', read_only=True)
    cout_total_chantier_materiaux = serializers.DecimalField(max_digits=10, decimal_places=2,source='partie.chantier.cout_total_materiaux', read_only=True)
    cout_total_chantier_main_d_oeuvre= serializers.DecimalField(max_digits=10, decimal_places=2,source='partie.chantier.cout_total_main_oeuvre', read_only=True)
    cout_total_chantier_global= serializers.DecimalField(max_digits=10, decimal_places=2,source='partie.chantier.cout_total_global', read_only=True)
    cout_total_chantier_materiaux_finition = serializers.DecimalField(max_digits=10, decimal_places=2,source='partie.chantier.cout_total_materiaux_finition', read_only=True)
    cout_total_chantier_materiaux_gros_oeuvre = serializers.DecimalField(max_digits=10, decimal_places=2,source='partie.chantier.cout_total_materiaux_gros_oeuvre', read_only=True)
    
    cout_total_main_oeuvre_finition  = serializers.DecimalField(max_digits=10, decimal_places=2,source='partie.chantier.cout_total_main_oeuvre_finition', read_only=True) 
    cout_total_main_oeuvre_gros_oeuvre  = serializers.DecimalField(max_digits=10, decimal_places=2,source='partie.chantier.cout_total_main_oeuvre_gros_oeuvre', read_only=True) 
    cout_total_espece  = serializers.DecimalField(max_digits=10, decimal_places=2,source='partie.chantier.cout_total_espece', read_only=True) 
    cout_total_cheque  = serializers.DecimalField(max_digits=10, decimal_places=2,source='partie.chantier.cout_total_cheque', read_only=True) 
    
    partie_type = serializers.CharField(source='partie.type', read_only=True)
    partie = serializers.CharField(write_only=True) 
    class Meta:
        model = BonCommande
        fields = [  
            'id', 'reference', 'date', 'partie','chantier_id', 'chantier_name', 
            'chantier_numero', 'partie_type','cout_total_global_BC', 'cout_total_materiaux','cout_total_main_oeuvre',
            'cout_total_chantier_global', 'cout_total_chantier_materiaux',
            'cout_total_chantier_materiaux_finition',
            'cout_total_chantier_materiaux_gros_oeuvre',
            'cout_total_chantier_main_d_oeuvre','materiaux',
            'cout_total_main_oeuvre_gros_oeuvre',
            'cout_total_main_oeuvre_finition',
            'cout_total_espece',
            'cout_total_cheque',
             'paiement',
        ]
        
    def create(self, validated_data):
        initial_data = self.initial_data
        chantier_id = initial_data.get('chantier_id')
        if not chantier_id:
            raise serializers.ValidationError("L'ID du chantier est requis.")
        try:
            chantier = Chantier.objects.get(id=chantier_id)
        except Chantier.DoesNotExist:
            raise serializers.ValidationError(f"Chantier avec ID {chantier_id} introuvable.")
        
        partie_type = validated_data.pop('partie', None)
        if not partie_type:
            raise serializers.ValidationError("Le type de partie est requis.")
        
        partie, created = PartieChantier.objects.get_or_create(
            chantier=chantier,
            type=partie_type
        )
        validated_data['partie'] = partie
        materiaux_objects_list = []
        
        materiaux_data = initial_data.get('materiaux', [])
        print(initial_data      )
        if not materiaux_data:
            raise serializers.ValidationError("Les matériaux sont requis.")
        paiement_data = initial_data.get('paiement', None)
        if(materiaux_data and paiement_data):
            bon_commande, created = BonCommande.objects.get_or_create(
                    reference=validated_data['reference'],
                    date=validated_data['date'],
                    type=partie_type, 
                    partie=validated_data['partie'])
            paiement = Paiement.objects.create(**paiement_data)
            bon_commande.paiement = paiement
            bon_commande.save()
        materiaux_objects = []
        for materiau in materiaux_data:
            if materiau['materiau'] == 'autre':
                liste_materiau, created = ListeMateriaux.objects.get_or_create(
                    name=materiau['nom'],
                    code=materiau['code'],
                    type=materiau['type_materiau'],
                )
            else:
                try:
                    liste_materiau = ListeMateriaux.objects.get(id=materiau['materiau'])
                except ListeMateriaux.DoesNotExist:
                    liste_materiau = ListeMateriaux.objects.create(
                        name=materiau['nom'],
                        code=materiau['code'],
                        type=materiau['type_materiau'],
                    )
            if(materiau['option_valeur']):
                if materiau['materiau']=='autre':
                    option_valeur ,created = OptionMateriau.objects.get_or_create(
                        materiau=liste_materiau,
                        valeur=materiau['option_valeur'],
                        type=materiau['option_type'],
                    )
                else:
                    try:
                        # Vérifiez si 'option_valeur' est un entier avant de l'utiliser comme ID
                        if str(materiau['option_valeur']).isdigit():
                            option_valeur = OptionMateriau.objects.get(id=materiau['option_valeur'])
                        else:
                            raise ValueError("Invalid ID for option_valeur")
                    except (OptionMateriau.DoesNotExist, ValueError):
                        # Créez une nouvelle entrée si l'ID est invalide ou non trouvé
                        option_valeur = OptionMateriau.objects.create(
                            materiau=liste_materiau,
                            valeur=materiau['option_valeur'],
                            type=materiau['option_type']
                        )
            else:
                option_valeur = None
            # if(materiau['paiement']):
            #     if materiau['paiement']=='autre':
                    
            materiaux_objects_list.append(liste_materiau)
            materiau_obj = MateriauBonCommande(
                bon_commande=bon_commande,
                materiau=liste_materiau,
                quantite=materiau['quantite'],
                prix_unitaire=materiau['prix_unitaire'],
                option = option_valeur,
            )
            materiaux_objects.append(materiau_obj)
            
        MateriauBonCommande.objects.bulk_create(materiaux_objects)
        return bon_commande
    
    def update(self, instance, validated_data):
        materiaux_data = validated_data.pop('materiaux', None)
        
        if materiaux_data is not None:
            existing_ids = {item.id for item in instance.materiaux.all()}
            new_ids = {materiau['id'] for materiau in materiaux_data if 'id' in materiau}

            # Supprimer les matériaux non présents dans les nouvelles données
            MateriauBonCommande.objects.filter(bon_commande=instance).exclude(id__in=new_ids).delete()

            # Créer ou mettre à jour les matériaux existants
            for materiau_data in materiaux_data:
                materiau_id = materiau_data.pop('id', None)
                if materiau_id and materiau_id in existing_ids:
                    MateriauBonCommande.objects.filter(id=materiau_id).update(**materiau_data)
                else:
                    MateriauBonCommande.objects.create(bon_commande=instance, **materiau_data)
                    
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class MateriauTotalSerializer(serializers.Serializer):
    material_name = serializers.CharField()
    material_type = serializers.CharField()
    bon_commande_type =  serializers.CharField()
    total_quantite = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cout = serializers.DecimalField(max_digits=10, decimal_places=2)

# class ChantierMateriauxCostSerializer(serializers.Serializer):
#     chantier_name = serializers.CharField()
#     total_materiaux_cost = serializers.DecimalField(max_digits=10, decimal_places=2)
#     materiaux_cout = serializers.SerializerMethodField()

#     def get_materiaux_cout(self, obj):
#         materiaux = MateriauBonCommande.objects.filter(bon_commande__partie__chantier=obj)
#         return [
#             {
#                 "materiau": item.materiau.name if item.materiau else "Personnalisé",
#                 "quantite": item.quantite,
#                 "prix_unitaire": item.prix_unitaire,
#                 "cout_total": item.cout_total
#             }
#             for item in materiaux
#         ]

