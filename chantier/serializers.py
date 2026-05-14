from rest_framework import serializers
from django.db.models import Sum, F, Q
from decimal import Decimal
from .models import (
    Chantier, ListeMateriaux, BonCommande, MateriauBonCommande,
    PartieChantier, OptionMateriau, Paiement
)


class OptionMateriauSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionMateriau
        fields = ['id', 'name', 'valeur', 'type', 'materiau']

    def create(self, validated_data):
        materiau = validated_data.get('materiau')
        if not materiau:
            raise serializers.ValidationError("Le champ 'materiau' est requis.")
        return OptionMateriau.objects.create(**validated_data)


class ListeMateriauxSerializer(serializers.ModelSerializer):
    options = OptionMateriauSerializer(many=True, read_only=True)

    class Meta:
        model = ListeMateriaux
        fields = ['id', 'code', 'name', 'type', 'options']

    def update(self, instance, validated_data):
        options_data = validated_data.pop('options', [])
        instance = super().update(instance, validated_data)
        for option_data in options_data:
            option_id = option_data.get('id', None)
            if option_id:
                option = OptionMateriau.objects.get(id=option_id)
                option.valeur = option_data['valeur']
                option.save()
            else:
                OptionMateriau.objects.create(liste_materiau=instance, **option_data)
        return instance


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

    class Meta:
        model = Chantier
        fields = [
            'id', 'numero', 'nom',
            'cout_total_materiaux', 'cout_total_main_oeuvre',
            'cout_total_materiaux_gros_oeuvre', 'cout_total_materiaux_finition',
            'cout_total_main_oeuvre_finition', 'cout_total_main_oeuvre_gros_oeuvre',
            'cout_total_global', 'cout_total_espece', 'cout_total_cheque',
        ]

    def get_cout_total_global(self, obj):
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
                raise serializers.ValidationError(
                    "Les champs 'numéro de chèque' et 'nom de banque' ne sont pas valides pour un paiement en espèces."
                )
        return data


class PartieChantierSerializer(serializers.ModelSerializer):
    cout_total_materiaux = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_main_oeuvre = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_chantier_materiaux_finition = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_chantier_materiaux_gros_oeuvre = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_main_oeuvre_finition = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_main_oeuvre_gros_oeuvre = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_espece = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    cout_total_cheque = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = PartieChantier
        fields = [
            'id', 'chantier', 'type',
            'cout_total_materiaux', 'cout_total_main_oeuvre',
            'cout_total_chantier_materiaux_finition', 'cout_total_main_oeuvre_finition',
            'cout_total_main_oeuvre_gros_oeuvre', 'cout_total_chantier_materiaux_gros_oeuvre',
            'cout_total_espece', 'cout_total_cheque',
        ]


class MateriauBonCommandeSerializer(serializers.ModelSerializer):
    materiau = serializers.CharField(required=False)
    materiau_id = serializers.CharField(source='materiau.id', read_only=True)
    materiau_name = serializers.CharField(source='materiau.name', read_only=True)
    type_materiau = serializers.CharField(source='materiau.type', read_only=True)
    code = serializers.CharField(source='materiau.code', read_only=True)
    cout_total = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    prix_unitaire = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    option = serializers.SerializerMethodField()
    option_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = MateriauBonCommande
        fields = [
            'id', 'materiau_id', 'materiau', 'materiau_name', 'prix_unitaire',
            'quantite', 'code', 'type_materiau', 'cout_total', 'option', 'option_id',
        ]

    def validate_option_id(self, value):
        try:
            return OptionMateriau.objects.get(id=value)
        except OptionMateriau.DoesNotExist:
            raise serializers.ValidationError("L'option spécifiée n'existe pas.")

    def validate_materiau_id(self, value):
        if value == "autre":
            return value
        try:
            return ListeMateriaux.objects.get(id=value)
        except (ListeMateriaux.DoesNotExist, ValueError):
            raise serializers.ValidationError(f"Le matériau spécifié avec l'ID {value} n'existe pas.")

    def update(self, instance, validated_data):
        if 'materiau_id' in self.initial_data:
            try:
                instance.materiau = ListeMateriaux.objects.get(id=self.initial_data['materiau_id'])
            except ListeMateriaux.DoesNotExist:
                raise serializers.ValidationError(
                    f"Le matériau spécifié avec l'ID {self.initial_data['materiau_id']} n'existe pas."
                )

        if 'option' in self.initial_data:
            option_data = self.initial_data['option']
            if option_data:
                try:
                    instance.option = OptionMateriau.objects.get(id=option_data)
                except OptionMateriau.DoesNotExist:
                    raise serializers.ValidationError("L'option spécifiée n'existe pas.")
            else:
                instance.option = None
        else:
            raise serializers.ValidationError("Le champ 'option' doit être soit un ID, soit un objet valide.")

        if 'prix_unitaire' in self.initial_data:
            instance.prix_unitaire = self.initial_data['prix_unitaire']
        if 'quantite' in self.initial_data:
            instance.quantite = self.initial_data['quantite']
        instance.save()
        return instance

    def get_option(self, obj):
        if obj.option:
            return {
                "option_id": obj.option.id,
                "code_option": obj.option.valeur,
                "type_option": obj.option.type,
                "nom_option": obj.option.name,
                "code_materiau": obj.materiau.code if obj.materiau else None,
                "nom_materiau": obj.materiau.name if obj.materiau else None,
                "type_materiau": obj.materiau.type if obj.materiau else None,
            }
        return None


class PaiementLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = ['id', 'type_paiement', 'date_paiement']


class BonCommandeListSerializer(serializers.ModelSerializer):
    """Serializer léger pour les listes — sans matériaux embarqués ni totaux chantier."""
    chantier_id = serializers.CharField(source='partie.chantier.id', read_only=True)
    chantier_name = serializers.CharField(source='partie.chantier.nom', read_only=True)
    chantier_numero = serializers.CharField(source='partie.chantier.numero', read_only=True)
    partie_type = serializers.CharField(source='partie.type', read_only=True)
    paiement = PaiementLightSerializer(read_only=True)
    cout_total_global_BC = serializers.SerializerMethodField()
    nb_materiaux = serializers.SerializerMethodField()

    class Meta:
        model = BonCommande
        fields = [
            'id', 'reference', 'date', 'type',
            'chantier_id', 'chantier_name', 'chantier_numero',
            'partie_type', 'cout_total_global_BC', 'nb_materiaux', 'paiement',
        ]

    def get_cout_total_global_BC(self, obj):
        total = Decimal('0')
        for m in obj.materiaux.all():
            total += m.quantite * m.prix_unitaire
        return total

    def get_nb_materiaux(self, obj):
        return len(obj.materiaux.all())


class BonCommandeSerializer(serializers.ModelSerializer):
    materiaux = MateriauBonCommandeSerializer(many=True, read_only=True)
    paiement = PaiementSerializer()

    chantier_id = serializers.CharField(source='partie.chantier.id', read_only=True)
    chantier_name = serializers.CharField(source='partie.chantier.nom', read_only=True)
    chantier_numero = serializers.CharField(source='partie.chantier.numero', read_only=True)
    partie_type = serializers.CharField(source='partie.type', read_only=True)
    partie = serializers.CharField(write_only=True)

    cout_total_materiaux = serializers.SerializerMethodField()
    cout_total_main_oeuvre = serializers.SerializerMethodField()
    cout_total_global_BC = serializers.SerializerMethodField()
    cout_total_chantier_materiaux = serializers.SerializerMethodField()
    cout_total_chantier_main_d_oeuvre = serializers.SerializerMethodField()
    cout_total_chantier_global = serializers.SerializerMethodField()
    cout_total_chantier_materiaux_finition = serializers.SerializerMethodField()
    cout_total_chantier_materiaux_gros_oeuvre = serializers.SerializerMethodField()
    cout_total_main_oeuvre_finition = serializers.SerializerMethodField()
    cout_total_main_oeuvre_gros_oeuvre = serializers.SerializerMethodField()
    cout_total_espece = serializers.SerializerMethodField()
    cout_total_cheque = serializers.SerializerMethodField()

    class Meta:
        model = BonCommande
        fields = [
            'id', 'reference', 'date', 'partie', 'chantier_id', 'chantier_name',
            'chantier_numero', 'partie_type', 'cout_total_global_BC',
            'cout_total_materiaux', 'cout_total_main_oeuvre',
            'cout_total_chantier_global', 'cout_total_chantier_materiaux',
            'cout_total_chantier_materiaux_finition', 'cout_total_chantier_materiaux_gros_oeuvre',
            'cout_total_chantier_main_d_oeuvre', 'materiaux',
            'cout_total_main_oeuvre_gros_oeuvre', 'cout_total_main_oeuvre_finition',
            'cout_total_espece', 'cout_total_cheque', 'paiement',
        ]

    # ------------------------------------------------------------------ #
    #  Helpers — calculs mis en cache pour éviter les requêtes répétées   #
    # ------------------------------------------------------------------ #

    def _compute_bc_totals(self, obj):
        """Calcule les totaux du BonCommande en itérant les matériaux déjà préchargés."""
        cache = self.context.setdefault('bc_totals_cache', {})
        if obj.pk not in cache:
            total_mat = Decimal('0')
            total_mo = Decimal('0')
            for m in obj.materiaux.all():
                otype = m.option.type if m.option else None
                effective_type = otype or (m.materiau.type if m.materiau else None)
                val = m.quantite * m.prix_unitaire
                if effective_type in ('gros_oeuvre', 'finition'):
                    total_mat += val
                elif effective_type == 'main_doeuvre':
                    total_mo += val
            cache[obj.pk] = {'materiaux': total_mat, 'main_oeuvre': total_mo}
        return cache[obj.pk]

    def _get_chantier_totals(self, chantier):
        """Calcule tous les totaux du Chantier en une seule passe de requêtes, mis en cache."""
        cache = self.context.setdefault('chantier_cache', {})
        if chantier.pk not in cache:
            ZERO = Decimal('0')
            base = MateriauBonCommande.objects.filter(bon_commande__partie__chantier=chantier)
            mat_filter = (
                Q(option__isnull=False, option__type__in=['gros_oeuvre', 'finition']) |
                Q(option__isnull=True, materiau__type__in=['gros_oeuvre', 'finition'])
            )
            mo_filter = (
                Q(option__isnull=False, option__type='main_doeuvre') |
                Q(option__isnull=True, materiau__type='main_doeuvre')
            )

            def agg(qs):
                return qs.aggregate(total=Sum(F('quantite') * F('prix_unitaire')))['total'] or ZERO

            total_mat = agg(base.filter(mat_filter))
            total_mo = agg(base.filter(mo_filter))
            cache[chantier.pk] = {
                'cout_total_materiaux': total_mat,
                'cout_total_main_oeuvre': total_mo,
                'cout_total_global': total_mat + total_mo,
                'cout_total_materiaux_finition': agg(base.filter(
                    Q(option__isnull=False, option__type='finition') |
                    Q(option__isnull=True, materiau__type='finition')
                )),
                'cout_total_materiaux_gros_oeuvre': agg(base.filter(
                    Q(option__isnull=False, option__type='gros_oeuvre') |
                    Q(option__isnull=True, materiau__type='gros_oeuvre')
                )),
                'cout_total_main_oeuvre_gros_oeuvre': agg(
                    base.filter(bon_commande__type='gros_oeuvre').filter(mo_filter)
                ),
                'cout_total_main_oeuvre_finition': agg(
                    base.filter(bon_commande__type='finition').filter(mo_filter)
                ),
                'cout_total_espece': agg(
                    base.filter(bon_commande__paiement__type_paiement='espece')
                ),
                'cout_total_cheque': agg(
                    base.filter(bon_commande__paiement__type_paiement='cheque')
                ),
            }
        return cache[chantier.pk]

    # ------------------------------------------------------------------ #
    #  Champs calculés du BonCommande                                     #
    # ------------------------------------------------------------------ #

    def get_cout_total_materiaux(self, obj):
        return self._compute_bc_totals(obj)['materiaux']

    def get_cout_total_main_oeuvre(self, obj):
        return self._compute_bc_totals(obj)['main_oeuvre']

    def get_cout_total_global_BC(self, obj):
        t = self._compute_bc_totals(obj)
        return t['materiaux'] + t['main_oeuvre']

    # ------------------------------------------------------------------ #
    #  Champs calculés du Chantier parent (mis en cache par chantier_id)  #
    # ------------------------------------------------------------------ #

    def get_cout_total_chantier_materiaux(self, obj):
        return self._get_chantier_totals(obj.partie.chantier)['cout_total_materiaux']

    def get_cout_total_chantier_main_d_oeuvre(self, obj):
        return self._get_chantier_totals(obj.partie.chantier)['cout_total_main_oeuvre']

    def get_cout_total_chantier_global(self, obj):
        return self._get_chantier_totals(obj.partie.chantier)['cout_total_global']

    def get_cout_total_chantier_materiaux_finition(self, obj):
        return self._get_chantier_totals(obj.partie.chantier)['cout_total_materiaux_finition']

    def get_cout_total_chantier_materiaux_gros_oeuvre(self, obj):
        return self._get_chantier_totals(obj.partie.chantier)['cout_total_materiaux_gros_oeuvre']

    def get_cout_total_main_oeuvre_finition(self, obj):
        return self._get_chantier_totals(obj.partie.chantier)['cout_total_main_oeuvre_finition']

    def get_cout_total_main_oeuvre_gros_oeuvre(self, obj):
        return self._get_chantier_totals(obj.partie.chantier)['cout_total_main_oeuvre_gros_oeuvre']

    def get_cout_total_espece(self, obj):
        return self._get_chantier_totals(obj.partie.chantier)['cout_total_espece']

    def get_cout_total_cheque(self, obj):
        return self._get_chantier_totals(obj.partie.chantier)['cout_total_cheque']

    # ------------------------------------------------------------------ #
    #  Create / Update                                                    #
    # ------------------------------------------------------------------ #

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

        partie, _ = PartieChantier.objects.get_or_create(chantier=chantier, type=partie_type)
        validated_data['partie'] = partie

        materiaux_data = initial_data.get('materiaux', [])
        if not materiaux_data:
            raise serializers.ValidationError("Les matériaux sont requis.")

        paiement_data = initial_data.get('paiement', None)
        if materiaux_data and paiement_data:
            bon_commande, _ = BonCommande.objects.get_or_create(
                reference=validated_data['reference'],
                date=validated_data['date'],
                type=partie_type,
                partie=validated_data['partie'],
            )
            paiement = Paiement.objects.create(**paiement_data)
            bon_commande.paiement = paiement
            bon_commande.save()

        materiaux_objects = []
        for materiau in materiaux_data:
            if materiau['materiau'] == 'autre':
                liste_materiau, _ = ListeMateriaux.objects.get_or_create(
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

            if materiau['option_valeur']:
                if materiau['materiau'] == 'autre':
                    option_valeur, _ = OptionMateriau.objects.get_or_create(
                        materiau=liste_materiau,
                        valeur=materiau['option_valeur'],
                        type=materiau['option_type'],
                    )
                else:
                    try:
                        if str(materiau['option_valeur']).isdigit():
                            option_valeur = OptionMateriau.objects.get(id=materiau['option_valeur'])
                        else:
                            raise ValueError("Invalid ID for option_valeur")
                    except (OptionMateriau.DoesNotExist, ValueError):
                        option_valeur = OptionMateriau.objects.create(
                            materiau=liste_materiau,
                            valeur=materiau['option_valeur'],
                            type=materiau['option_type'],
                        )
            else:
                option_valeur = None

            materiaux_objects.append(MateriauBonCommande(
                bon_commande=bon_commande,
                materiau=liste_materiau,
                quantite=materiau['quantite'],
                prix_unitaire=materiau['prix_unitaire'],
                option=option_valeur,
            ))

        MateriauBonCommande.objects.bulk_create(materiaux_objects)
        return bon_commande

    def update(self, instance, validated_data):
        materiaux_data = validated_data.pop('materiaux', None)
        if materiaux_data is not None:
            existing_ids = {item.id for item in instance.materiaux.all()}
            new_ids = {m['id'] for m in materiaux_data if 'id' in m}
            MateriauBonCommande.objects.filter(bon_commande=instance).exclude(id__in=new_ids).delete()
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
    bon_commande_type = serializers.CharField()
    total_quantite = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cout = serializers.DecimalField(max_digits=10, decimal_places=2)
