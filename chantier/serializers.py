from rest_framework import serializers
from django.db.models import Sum, F, Q, Case, When, DecimalField, Value
from django.db.models.functions import Coalesce
from decimal import Decimal
from .models import (
    Chantier, ListeMateriaux, BonCommande, MateriauBonCommande,
    PartieChantier, OptionMateriau, Paiement
)

_DFIELD = DecimalField(max_digits=15, decimal_places=2)
_ZERO = Value(Decimal('0'), output_field=_DFIELD)


def _csum(condition):
    """Conditional sum: sums (quantite * prix_unitaire) where condition is True."""
    return Coalesce(
        Sum(Case(When(condition, then=F('quantite') * F('prix_unitaire')), output_field=_DFIELD)),
        _ZERO,
    )


def _compute_chantier_all_totals(chantier_pk):
    """One single DB query computing all financial totals for a chantier."""
    fin = Q(option__isnull=False, option__type='finition') | Q(option__isnull=True, materiau__type='finition')
    go  = Q(option__isnull=False, option__type='gros_oeuvre') | Q(option__isnull=True, materiau__type='gros_oeuvre')
    mo  = Q(option__isnull=False, option__type='main_doeuvre') | Q(option__isnull=True, materiau__type='main_doeuvre')

    r = MateriauBonCommande.objects.filter(
        bon_commande__partie__chantier_id=chantier_pk
    ).aggregate(
        mat_fin  = _csum(fin),
        mat_go   = _csum(go),
        mo_all   = _csum(mo),
        mo_fin   = _csum(Q(bon_commande__type='finition') & mo),
        mo_go    = _csum(Q(bon_commande__type='gros_oeuvre') & mo),
        espece   = _csum(Q(bon_commande__paiement__type_paiement='espece')),
        cheque   = _csum(Q(bon_commande__paiement__type_paiement='cheque')),
    )

    return {
        'cout_total_materiaux_finition':      r['mat_fin'],
        'cout_total_materiaux_gros_oeuvre':   r['mat_go'],
        'cout_total_materiaux':               r['mat_fin'] + r['mat_go'],
        'cout_total_main_oeuvre':             r['mo_all'],
        'cout_total_main_oeuvre_finition':    r['mo_fin'],
        'cout_total_main_oeuvre_gros_oeuvre': r['mo_go'],
        'cout_total_global':                  r['mat_fin'] + r['mat_go'] + r['mo_all'],
        'cout_total_espece':                  r['espece'],
        'cout_total_cheque':                  r['cheque'],
    }


def _compute_partie_all_totals(partie_pk):
    """One single DB query computing all financial totals for a partie."""
    fin = Q(option__isnull=False, option__type='finition') | Q(option__isnull=True, materiau__type='finition')
    go  = Q(option__isnull=False, option__type='gros_oeuvre') | Q(option__isnull=True, materiau__type='gros_oeuvre')
    mo  = Q(option__isnull=False, option__type='main_doeuvre') | Q(option__isnull=True, materiau__type='main_doeuvre')

    r = MateriauBonCommande.objects.filter(
        bon_commande__partie_id=partie_pk
    ).aggregate(
        mat_fin  = _csum(fin),
        mat_go   = _csum(go),
        mo_all   = _csum(mo),
        mo_fin   = _csum(Q(bon_commande__type='finition') & mo),
        mo_go    = _csum(Q(bon_commande__type='gros_oeuvre') & mo),
        espece   = _csum(Q(bon_commande__paiement__type_paiement='espece')),
        cheque   = _csum(Q(bon_commande__paiement__type_paiement='cheque')),
    )

    return {
        'cout_total_materiaux_finition':      r['mat_fin'],
        'cout_total_materiaux_gros_oeuvre':   r['mat_go'],
        'cout_total_materiaux':               r['mat_fin'] + r['mat_go'],
        'cout_total_main_oeuvre':             r['mo_all'],
        'cout_total_main_oeuvre_finition':    r['mo_fin'],
        'cout_total_main_oeuvre_gros_oeuvre': r['mo_go'],
        'cout_total_espece':                  r['espece'],
        'cout_total_cheque':                  r['cheque'],
    }


# ---------------------------------------------------------------------------
# Simple serializers
# ---------------------------------------------------------------------------

class OptionMateriauSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptionMateriau
        fields = ['id', 'name', 'valeur', 'type', 'materiau']

    def create(self, validated_data):
        if not validated_data.get('materiau'):
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
            option_id = option_data.get('id')
            if option_id:
                option = OptionMateriau.objects.get(id=option_id)
                option.valeur = option_data['valeur']
                option.save()
            else:
                OptionMateriau.objects.create(liste_materiau=instance, **option_data)
        return instance


class PaiementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = ['id', 'type_paiement', 'date_paiement', 'numero_cheque', 'nom_banque']

    def validate(self, data):
        if data['type_paiement'] == 'cheque':
            if not data.get('numero_cheque'):
                raise serializers.ValidationError("Le numero de cheque est requis.")
            if not data.get('nom_banque'):
                raise serializers.ValidationError("Le nom de la banque est requis.")
        elif data['type_paiement'] == 'espece':
            if data.get('numero_cheque') or data.get('nom_banque'):
                raise serializers.ValidationError(
                    "Les champs cheque/banque ne sont pas valides pour un paiement en especes."
                )
        return data


class PaiementLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paiement
        fields = ['id', 'type_paiement', 'date_paiement']


# ---------------------------------------------------------------------------
# Chantier
# ---------------------------------------------------------------------------

class ChantierSerializer(serializers.ModelSerializer):
    cout_total_materiaux               = serializers.SerializerMethodField()
    cout_total_main_oeuvre             = serializers.SerializerMethodField()
    cout_total_materiaux_finition      = serializers.SerializerMethodField()
    cout_total_materiaux_gros_oeuvre   = serializers.SerializerMethodField()
    cout_total_main_oeuvre_finition    = serializers.SerializerMethodField()
    cout_total_main_oeuvre_gros_oeuvre = serializers.SerializerMethodField()
    cout_total_global                  = serializers.SerializerMethodField()
    cout_total_espece                  = serializers.SerializerMethodField()
    cout_total_cheque                  = serializers.SerializerMethodField()

    class Meta:
        model = Chantier
        fields = [
            'id', 'numero', 'nom',
            'cout_total_materiaux', 'cout_total_main_oeuvre',
            'cout_total_materiaux_gros_oeuvre', 'cout_total_materiaux_finition',
            'cout_total_main_oeuvre_finition', 'cout_total_main_oeuvre_gros_oeuvre',
            'cout_total_global', 'cout_total_espece', 'cout_total_cheque',
        ]

    def _totals(self, obj):
        cache = self.context.setdefault('chantier_totals_cache', {})
        if obj.pk not in cache:
            cache[obj.pk] = _compute_chantier_all_totals(obj.pk)
        return cache[obj.pk]

    def get_cout_total_materiaux(self, obj):               return self._totals(obj)['cout_total_materiaux']
    def get_cout_total_main_oeuvre(self, obj):             return self._totals(obj)['cout_total_main_oeuvre']
    def get_cout_total_materiaux_finition(self, obj):      return self._totals(obj)['cout_total_materiaux_finition']
    def get_cout_total_materiaux_gros_oeuvre(self, obj):   return self._totals(obj)['cout_total_materiaux_gros_oeuvre']
    def get_cout_total_main_oeuvre_finition(self, obj):    return self._totals(obj)['cout_total_main_oeuvre_finition']
    def get_cout_total_main_oeuvre_gros_oeuvre(self, obj): return self._totals(obj)['cout_total_main_oeuvre_gros_oeuvre']
    def get_cout_total_global(self, obj):                  return self._totals(obj)['cout_total_global']
    def get_cout_total_espece(self, obj):                  return self._totals(obj)['cout_total_espece']
    def get_cout_total_cheque(self, obj):                  return self._totals(obj)['cout_total_cheque']


# ---------------------------------------------------------------------------
# PartieChantier
# ---------------------------------------------------------------------------

class PartieChantierSerializer(serializers.ModelSerializer):
    cout_total_materiaux                      = serializers.SerializerMethodField()
    cout_total_main_oeuvre                    = serializers.SerializerMethodField()
    cout_total_chantier_materiaux_finition    = serializers.SerializerMethodField()
    cout_total_chantier_materiaux_gros_oeuvre = serializers.SerializerMethodField()
    cout_total_main_oeuvre_finition           = serializers.SerializerMethodField()
    cout_total_main_oeuvre_gros_oeuvre        = serializers.SerializerMethodField()
    cout_total_espece                         = serializers.SerializerMethodField()
    cout_total_cheque                         = serializers.SerializerMethodField()

    class Meta:
        model = PartieChantier
        fields = [
            'id', 'chantier', 'type',
            'cout_total_materiaux', 'cout_total_main_oeuvre',
            'cout_total_chantier_materiaux_finition', 'cout_total_main_oeuvre_finition',
            'cout_total_main_oeuvre_gros_oeuvre', 'cout_total_chantier_materiaux_gros_oeuvre',
            'cout_total_espece', 'cout_total_cheque',
        ]

    def _totals(self, obj):
        cache = self.context.setdefault('partie_totals_cache', {})
        if obj.pk not in cache:
            cache[obj.pk] = _compute_partie_all_totals(obj.pk)
        return cache[obj.pk]

    def get_cout_total_materiaux(self, obj):                      return self._totals(obj)['cout_total_materiaux']
    def get_cout_total_main_oeuvre(self, obj):                    return self._totals(obj)['cout_total_main_oeuvre']
    def get_cout_total_chantier_materiaux_finition(self, obj):    return self._totals(obj)['cout_total_materiaux_finition']
    def get_cout_total_chantier_materiaux_gros_oeuvre(self, obj): return self._totals(obj)['cout_total_materiaux_gros_oeuvre']
    def get_cout_total_main_oeuvre_finition(self, obj):           return self._totals(obj)['cout_total_main_oeuvre_finition']
    def get_cout_total_main_oeuvre_gros_oeuvre(self, obj):        return self._totals(obj)['cout_total_main_oeuvre_gros_oeuvre']
    def get_cout_total_espece(self, obj):                         return self._totals(obj)['cout_total_espece']
    def get_cout_total_cheque(self, obj):                         return self._totals(obj)['cout_total_cheque']


# ---------------------------------------------------------------------------
# MateriauBonCommande
# ---------------------------------------------------------------------------

class MateriauBonCommandeSerializer(serializers.ModelSerializer):
    materiau      = serializers.CharField(required=False)
    materiau_id   = serializers.CharField(source='materiau.id', read_only=True)
    materiau_name = serializers.CharField(source='materiau.name', read_only=True)
    type_materiau = serializers.CharField(source='materiau.type', read_only=True)
    code          = serializers.CharField(source='materiau.code', read_only=True)
    cout_total    = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    prix_unitaire = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    option        = serializers.SerializerMethodField()
    option_id     = serializers.IntegerField(write_only=True, required=False)

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
            raise serializers.ValidationError("L'option specifiee n'existe pas.")

    def validate_materiau_id(self, value):
        if value == 'autre':
            return value
        try:
            return ListeMateriaux.objects.get(id=value)
        except (ListeMateriaux.DoesNotExist, ValueError):
            raise serializers.ValidationError(f"Le materiau avec l'ID {value} n'existe pas.")

    def update(self, instance, validated_data):
        initial = self.initial_data

        if 'materiau_id' in initial:
            try:
                instance.materiau = ListeMateriaux.objects.get(id=initial['materiau_id'])
            except ListeMateriaux.DoesNotExist:
                raise serializers.ValidationError(
                    f"Le materiau avec l'ID {initial['materiau_id']} n'existe pas."
                )

        if 'option' in initial:
            option_data = initial['option']
            if option_data:
                try:
                    instance.option = OptionMateriau.objects.get(id=option_data)
                except OptionMateriau.DoesNotExist:
                    raise serializers.ValidationError("L'option specifiee n'existe pas.")
            else:
                instance.option = None

        if 'prix_unitaire' in initial:
            instance.prix_unitaire = initial['prix_unitaire']
        if 'quantite' in initial:
            instance.quantite = initial['quantite']

        instance.save()
        return instance

    def get_option(self, obj):
        if not obj.option:
            return None
        return {
            'option_id':     obj.option.id,
            'code_option':   obj.option.valeur,
            'type_option':   obj.option.type,
            'nom_option':    obj.option.name,
            'code_materiau': obj.materiau.code if obj.materiau else None,
            'nom_materiau':  obj.materiau.name if obj.materiau else None,
            'type_materiau': obj.materiau.type if obj.materiau else None,
        }


# ---------------------------------------------------------------------------
# BonCommande — list (lightweight, no materiaux array)
# ---------------------------------------------------------------------------

class BonCommandeListSerializer(serializers.ModelSerializer):
    chantier_id          = serializers.CharField(source='partie.chantier.id', read_only=True)
    chantier_name        = serializers.CharField(source='partie.chantier.nom', read_only=True)
    chantier_numero      = serializers.CharField(source='partie.chantier.numero', read_only=True)
    partie_type          = serializers.CharField(source='partie.type', read_only=True)
    paiement             = PaiementLightSerializer(read_only=True)
    cout_total_global_BC = serializers.SerializerMethodField()
    nb_materiaux         = serializers.SerializerMethodField()

    class Meta:
        model = BonCommande
        fields = [
            'id', 'reference', 'date', 'type',
            'chantier_id', 'chantier_name', 'chantier_numero',
            'partie_type', 'cout_total_global_BC', 'nb_materiaux', 'paiement',
        ]

    def _bc_totals(self, obj):
        cache = self.context.setdefault('bc_list_cache', {})
        if obj.pk not in cache:
            total = Decimal('0')
            count = 0
            for m in obj.materiaux.all():  # uses prefetch cache, zero extra queries
                total += m.quantite * m.prix_unitaire
                count += 1
            cache[obj.pk] = {'total': total, 'count': count}
        return cache[obj.pk]

    def get_cout_total_global_BC(self, obj):
        return self._bc_totals(obj)['total']

    def get_nb_materiaux(self, obj):
        return self._bc_totals(obj)['count']


# ---------------------------------------------------------------------------
# BonCommande — detail (full, with materiaux + all chantier totals)
# ---------------------------------------------------------------------------

class BonCommandeSerializer(serializers.ModelSerializer):
    materiaux = MateriauBonCommandeSerializer(many=True, read_only=True)
    paiement  = PaiementSerializer()

    chantier_id     = serializers.CharField(source='partie.chantier.id', read_only=True)
    chantier_name   = serializers.CharField(source='partie.chantier.nom', read_only=True)
    chantier_numero = serializers.CharField(source='partie.chantier.numero', read_only=True)
    partie_type     = serializers.CharField(source='partie.type', read_only=True)
    partie          = serializers.CharField(write_only=True)

    cout_total_materiaux               = serializers.SerializerMethodField()
    cout_total_main_oeuvre             = serializers.SerializerMethodField()
    cout_total_global_BC               = serializers.SerializerMethodField()
    cout_total_chantier_materiaux      = serializers.SerializerMethodField()
    cout_total_chantier_main_d_oeuvre  = serializers.SerializerMethodField()
    cout_total_chantier_global         = serializers.SerializerMethodField()
    cout_total_chantier_materiaux_finition      = serializers.SerializerMethodField()
    cout_total_chantier_materiaux_gros_oeuvre   = serializers.SerializerMethodField()
    cout_total_main_oeuvre_finition    = serializers.SerializerMethodField()
    cout_total_main_oeuvre_gros_oeuvre = serializers.SerializerMethodField()
    cout_total_espece                  = serializers.SerializerMethodField()
    cout_total_cheque                  = serializers.SerializerMethodField()

    class Meta:
        model = BonCommande
        fields = [
            'id', 'reference', 'date', 'partie', 'type',
            'chantier_id', 'chantier_name', 'chantier_numero', 'partie_type',
            'cout_total_global_BC', 'cout_total_materiaux', 'cout_total_main_oeuvre',
            'cout_total_chantier_global', 'cout_total_chantier_materiaux',
            'cout_total_chantier_materiaux_finition', 'cout_total_chantier_materiaux_gros_oeuvre',
            'cout_total_chantier_main_d_oeuvre',
            'cout_total_main_oeuvre_gros_oeuvre', 'cout_total_main_oeuvre_finition',
            'cout_total_espece', 'cout_total_cheque',
            'materiaux', 'paiement',
        ]

    # --- BC-level totals (computed from prefetched materiaux, zero extra queries) ---

    def _bc_totals(self, obj):
        cache = self.context.setdefault('bc_totals_cache', {})
        if obj.pk not in cache:
            total_mat = Decimal('0')
            total_mo  = Decimal('0')
            for m in obj.materiaux.all():
                eff_type = (m.option.type if m.option else None) or (m.materiau.type if m.materiau else None)
                val = m.quantite * m.prix_unitaire
                if eff_type in ('gros_oeuvre', 'finition'):
                    total_mat += val
                elif eff_type == 'main_doeuvre':
                    total_mo += val
            cache[obj.pk] = {'materiaux': total_mat, 'main_oeuvre': total_mo}
        return cache[obj.pk]

    def get_cout_total_materiaux(self, obj):
        return self._bc_totals(obj)['materiaux']

    def get_cout_total_main_oeuvre(self, obj):
        return self._bc_totals(obj)['main_oeuvre']

    def get_cout_total_global_BC(self, obj):
        t = self._bc_totals(obj)
        return t['materiaux'] + t['main_oeuvre']

    # --- Chantier-level totals (one query per chantier, cached across BCs) ---

    def _chantier_totals(self, obj):
        cache = self.context.setdefault('chantier_cache', {})
        chantier = obj.partie.chantier
        if chantier.pk not in cache:
            cache[chantier.pk] = _compute_chantier_all_totals(chantier.pk)
        return cache[chantier.pk]

    def get_cout_total_chantier_materiaux(self, obj):             return self._chantier_totals(obj)['cout_total_materiaux']
    def get_cout_total_chantier_main_d_oeuvre(self, obj):         return self._chantier_totals(obj)['cout_total_main_oeuvre']
    def get_cout_total_chantier_global(self, obj):                return self._chantier_totals(obj)['cout_total_global']
    def get_cout_total_chantier_materiaux_finition(self, obj):    return self._chantier_totals(obj)['cout_total_materiaux_finition']
    def get_cout_total_chantier_materiaux_gros_oeuvre(self, obj): return self._chantier_totals(obj)['cout_total_materiaux_gros_oeuvre']
    def get_cout_total_main_oeuvre_finition(self, obj):           return self._chantier_totals(obj)['cout_total_main_oeuvre_finition']
    def get_cout_total_main_oeuvre_gros_oeuvre(self, obj):        return self._chantier_totals(obj)['cout_total_main_oeuvre_gros_oeuvre']
    def get_cout_total_espece(self, obj):                         return self._chantier_totals(obj)['cout_total_espece']
    def get_cout_total_cheque(self, obj):                         return self._chantier_totals(obj)['cout_total_cheque']

    # --- Create ---

    def create(self, validated_data):
        initial = self.initial_data
        chantier_id = initial.get('chantier_id')
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

        materiaux_data = initial.get('materiaux', [])
        if not materiaux_data:
            raise serializers.ValidationError("Les materiaux sont requis.")

        paiement_data = initial.get('paiement')
        bon_commande, _ = BonCommande.objects.get_or_create(
            reference=validated_data['reference'],
            date=validated_data['date'],
            type=partie_type,
            partie=validated_data['partie'],
        )

        if paiement_data:
            paiement = Paiement.objects.create(**paiement_data)
            bon_commande.paiement = paiement
            bon_commande.save()

        materiaux_objects = []
        for mat in materiaux_data:
            if mat['materiau'] == 'autre':
                liste_materiau, _ = ListeMateriaux.objects.get_or_create(
                    name=mat['nom'], code=mat['code'], type=mat['type_materiau'],
                )
            else:
                try:
                    liste_materiau = ListeMateriaux.objects.get(id=mat['materiau'])
                except ListeMateriaux.DoesNotExist:
                    liste_materiau = ListeMateriaux.objects.create(
                        name=mat['nom'], code=mat['code'], type=mat['type_materiau'],
                    )

            option_valeur = None
            if mat.get('option_valeur'):
                if mat['materiau'] == 'autre':
                    option_valeur, _ = OptionMateriau.objects.get_or_create(
                        materiau=liste_materiau,
                        valeur=mat['option_valeur'],
                        type=mat['option_type'],
                    )
                else:
                    raw = mat['option_valeur']
                    try:
                        if str(raw).isdigit():
                            option_valeur = OptionMateriau.objects.get(id=raw)
                        else:
                            raise ValueError
                    except (OptionMateriau.DoesNotExist, ValueError):
                        option_valeur, _ = OptionMateriau.objects.get_or_create(
                            materiau=liste_materiau,
                            valeur=raw,
                            type=mat['option_type'],
                        )

            materiaux_objects.append(MateriauBonCommande(
                bon_commande=bon_commande,
                materiau=liste_materiau,
                quantite=mat['quantite'],
                prix_unitaire=mat['prix_unitaire'],
                option=option_valeur,
            ))

        MateriauBonCommande.objects.bulk_create(materiaux_objects)
        return bon_commande

    # --- Update ---

    def update(self, instance, validated_data):
        paiement_data = validated_data.pop('paiement', None)
        if paiement_data:
            if instance.paiement:
                for attr, value in paiement_data.items():
                    setattr(instance.paiement, attr, value)
                instance.paiement.save()
            else:
                paiement = Paiement.objects.create(**paiement_data)
                instance.paiement = paiement

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


# ---------------------------------------------------------------------------
# ChantierMateriauxTotals (used by ChantierMateriauxTotalsView)
# ---------------------------------------------------------------------------

class MateriauTotalSerializer(serializers.Serializer):
    material_name     = serializers.CharField()
    material_type     = serializers.CharField()
    bon_commande_type = serializers.CharField()
    total_quantite    = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_cout        = serializers.DecimalField(max_digits=10, decimal_places=2)

