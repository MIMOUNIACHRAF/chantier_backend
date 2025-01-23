from django.db import models
from django.core.exceptions import ValidationError


class Chantier(models.Model):
    numero = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=100, blank=True)

    @property
    def cout_total_materiaux(self):
        # Somme des coûts des matériaux pour toutes les parties du chantier
        return sum(partie.cout_total_materiaux for partie in self.parties.all())

    @property
    def cout_total_main_oeuvre(self):
        # Somme des coûts de la main-d'œuvre pour toutes les parties du chantier
        return sum(partie.cout_total_main_oeuvre for partie in self.parties.all())
    
    @property
    def cout_total_materiaux_finition(self):
        # Somme des coûts de la main-d'œuvre pour toutes les parties du chantier
        return sum(partie.cout_total_materiaux_finition for partie in self.parties.all())
    @property
    def cout_total_materiaux_gros_oeuvre(self):
        # Somme des coûts de la main-d'œuvre pour toutes les parties du chantier
        return sum(partie.cout_total_materiaux_gros_oeuvre for partie in self.parties.all())
    @property
    def cout_total_main_oeuvre_gros_oeuvre(self):
        # Somme des coûts de la main-d'œuvre pour toutes les parties du chantier
        return sum(partie.cout_total_main_oeuvre_gros_oeuvre for partie in self.parties.all())
    @property
    def cout_total_main_oeuvre_finition(self):
        # Somme des coûts de la main-d'œuvre pour toutes les parties du chantier
        return sum(partie.cout_total_main_oeuvre_finition for partie in self.parties.all())
    @property
    def cout_total_global(self):
        return self.cout_total_materiaux + self.cout_total_main_oeuvre
    
    def __str__(self):
        return self.nom


from django.db.models import Sum, F

class PartieChantier(models.Model):
    CHOICES_TYPE = [
        ('gros_oeuvre', 'Gros œuvre'),
        ('finition', 'Finition'),
    ]
    chantier = models.ForeignKey(Chantier, on_delete=models.CASCADE, related_name='parties')
    type = models.CharField(max_length=20, choices=CHOICES_TYPE)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['chantier', 'type'], name='unique_partie_per_type')
        ]
    @property
    def cout_total_materiaux(self):
        # Calcul des matériaux (hors main-d'œuvre)
        total_materiaux = MateriauBonCommande.objects.filter(
            bon_commande__partie=self,
            option__type__in=['gros_oeuvre', 'finition']
        ).aggregate(total=Sum(F('quantite') * F('prix_unitaire')))['total'] or 0
        return total_materiaux
    @property
    def cout_total_materiaux_finition(self):
        total_materiaux = MateriauBonCommande.objects.filter(
            bon_commande__partie=self,
            option__type='finition'
        ).aggregate(total=Sum(F('quantite') * F('prix_unitaire')))['total'] or 0
        return total_materiaux
    @property
    def cout_total_materiaux_gros_oeuvre(self):
        total_materiaux = MateriauBonCommande.objects.filter(
            bon_commande__partie=self,
            option__type='gros_oeuvre'
        ).aggregate(total=Sum(F('quantite') * F('prix_unitaire')))['total'] or 0
        return total_materiaux
    @property
    def cout_total_main_oeuvre(self):
        # Calcul de la main-d'œuvre
        total_main_oeuvre = MateriauBonCommande.objects.filter(
            bon_commande__partie=self,
            option__type='main_doeuvre',
        ).aggregate(total=Sum(F('quantite') * F('prix_unitaire')))['total'] or 0
        return total_main_oeuvre
    @property
    def cout_total_main_oeuvre_gros_oeuvre(self):
        # Calcul de la main-d'œuvre
        total_main_oeuvre = MateriauBonCommande.objects.filter(
            bon_commande__partie=self,
            bon_commande__type='gros_oeuvre',
            option__type='main_doeuvre',
        ).aggregate(total=Sum(F('quantite') * F('prix_unitaire')))['total'] or 0
        return total_main_oeuvre
    @property
    def cout_total_main_oeuvre_finition(self):
        # Calcul de la main-d'œuvre
        total_main_oeuvre = MateriauBonCommande.objects.filter(
            bon_commande__partie=self,
            bon_commande__type='finition',
            option__type='main_doeuvre'
        ).aggregate(total=Sum(F('quantite') * F('prix_unitaire')))['total'] or 0
        return total_main_oeuvre

    # @property
    # def cout_total_main_oeuvre(self):
    #     # Calcul de la main-d'œuvre
    #     total_main_oeuvre = MateriauBonCommande.objects.filter(
    #         bon_commande__partie=self,
    #         option__type='main_doeuvre'
    #     ).aggregate(total=Sum(F('quantite') * F('prix_unitaire')))['total'] or 0
    #     return total_main_oeuvre
    
    def __str__(self):
        return f"{self.type} - {self.chantier.nom}"


class ListeMateriaux(models.Model):
    TYPE_CHOICES = [
        ('gros_oeuvre', 'Gros œuvre'),
        ('finition', 'Finition'),
        ('main_doeuvre', 'Main d’œuvre'),
    ]
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=10,null=True, unique=True) 
    type = models.CharField(max_length=20, choices=TYPE_CHOICES) 
    def __str__(self):
        return  f"{self.name} - {self.type}"
    
class OptionMateriau(models.Model):
    name=models.CharField(max_length=50,null=True, blank=True)
    materiau = models.ForeignKey(ListeMateriaux, related_name='options', on_delete=models.CASCADE)  # Lien avec le matériau
    valeur = models.CharField(max_length=20)  # Option spécifique (ex : 45, 55)
    TYPE_CHOICES = [
        ('gros_oeuvre', 'Gros œuvre'),
        ('finition', 'Finition'),
        ('main_doeuvre', 'Main d’œuvre'),
    ]
    type = models.CharField(max_length=20, choices=TYPE_CHOICES) 
    
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['materiau', 'valeur','type'], name='unique_materiau_valeur')
        ]
    def clean(self):
        if self.pk is None and OptionMateriau.objects.filter(
            materiau=self.materiau, valeur=self.valeur, type=self.type
        ).exists():
            raise ValidationError(f"L'option '{self.valeur}' existe déjà pour ce matériau.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.materiau.code} - Option: {self.id}---{self.valeur}/{self.type}"

class Paiement(models.Model):
    TYPE_CHOICES = [
        ('espece', 'Espèces'),
        ('cheque', 'Chèque'),
    ]

    type_paiement = models.CharField(max_length=10, choices=TYPE_CHOICES)
    date_paiement = models.DateField(auto_now_add=True)

    numero_cheque = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Numéro de chèque",
    )
    nom_banque = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Nom de la banque",
    )
    @property
    def bon_commande(self):
        return getattr(self, 'boncommande', None)

    @property
    def montant(self):
        if self.bon_commande:
            return self.bon_commande.cout_total_global_BC
        return 0

    def clean(self):
        if self.type_paiement == 'cheque':
            if not self.numero_cheque:
                raise ValidationError("Le numéro de chèque est requis pour un paiement par chèque.")
            if not self.nom_banque:
                raise ValidationError("Le nom de la banque est requis pour un paiement par chèque.")
            if Paiement.objects.filter(numero_cheque=self.numero_cheque).exists():
                raise ValidationError(f"Le numéro de chèque {self.numero_cheque} existe déjà.")
        elif self.type_paiement == 'espece':
            if self.numero_cheque or self.nom_banque:
                raise ValidationError("Les champs 'numéro de chèque' et 'nom de banque' ne sont pas valides pour un paiement en espèces.")

    def __str__(self):
        if self.type_paiement == 'cheque':
            return f"Chèque {self.numero_cheque} ({self.nom_banque}) - {self.montant:.2f} DH"
        return f"Espèces - {self.montant:.2f} DH"
    
from django.utils.translation import gettext as _

class BonCommande(models.Model):
    TYPE_CHOICES = [
        ('gros_oeuvre', 'Gros Œuvre'),
        ('finition', 'Finition'),
    ]
    
    reference = models.CharField(
        max_length=100, 
        error_messages={
            'unique': _("Un bon de commande avec cette référence existe déjà.")
        },
    )
    date = models.DateField()

    # Type du bon de commande avec une valeur par défaut
    type = models.CharField(
        max_length=20, 
        choices=TYPE_CHOICES, 
        default='gros_oeuvre'
    )

    # Lien avec la partie du chantier
    partie = models.ForeignKey(
        'PartieChantier', 
        on_delete=models.CASCADE, 
        related_name='bons_commande',
    )

    # Lien avec le paiement, optionnel
    paiement = models.OneToOneField(
        'Paiement',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='bons_commande',
    )
    
    # Méthode save pour gérer automatiquement le type si non défini
    def save(self, *args, **kwargs):
        if not self.type:
            self.type = self.partie.type
        super().save(*args, **kwargs)

    # Calcul du coût total des matériaux
    @property
    def cout_total_materiaux(self):
        return self.materiaux.filter(option__type__in=['gros_oeuvre', 'finition']).aggregate(
            total=models.Sum(models.F('quantite') * models.F('prix_unitaire'))
        )['total'] or 0

    # Calcul du coût total de la main-d'œuvre
    @property
    def cout_total_main_oeuvre(self):
        return self.materiaux.filter(option__type='main_doeuvre').aggregate(
            total=models.Sum(models.F('quantite') * models.F('prix_unitaire'))
        )['total'] or 0
    
    # Contraintes d'unicité
    class Meta:
        unique_together = (('reference', 'partie')) 

    # Représentation en chaîne
    def __str__(self):
        return self.reference

    # Calcul du coût total global
    @property
    def cout_total_global_BC(self):
        return self.cout_total_materiaux + self.cout_total_main_oeuvre
from decimal import Decimal
class MateriauBonCommande(models.Model):
    bon_commande = models.ForeignKey(BonCommande, on_delete=models.CASCADE, related_name='materiaux')
    materiau = models.ForeignKey(ListeMateriaux, null=True, blank=True, on_delete=models.SET_NULL)
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2,default=100)
    option = models.ForeignKey(
        OptionMateriau, 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='materiau_bon_commandes'
    )
    @property
    def cout_total(self):
        try:
            quantite = Decimal(self.quantite) if not isinstance(self.quantite, Decimal) else self.quantite
            prix_unitaire = Decimal(self.prix_unitaire) if not isinstance(self.prix_unitaire, Decimal) else self.prix_unitaire
            return quantite * prix_unitaire
        except (ValueError, TypeError):
            return Decimal(0)

    def __str__(self):
        return f"{self.materiau.name if self.materiau else 'Matériel personnalisé'} - {self.bon_commande.reference}"

