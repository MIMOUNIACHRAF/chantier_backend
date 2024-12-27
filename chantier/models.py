from django.db import models


class Chantier(models.Model):
    numero = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=100, blank=True)

    @property
    def cout_total_materiaux(self):
        return sum(bon.cout_total for bon in self.bons_commande.all())

    @property
    def cout_total_main_oeuvre(self):
        # Placeholder for main d'oeuvre logic
        return 0
    def __str__(self):
        return self.nom
    


class ListeMateriaux(models.Model):
    name = models.CharField(max_length=50, unique=True)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    def __str__(self):
        return self.name


class BonCommande(models.Model):
    reference = models.CharField(max_length=100, unique=True)
    date = models.DateField()
    chantier = models.ForeignKey(Chantier, on_delete=models.CASCADE, related_name='bons_commande')

    @property
    def cout_total(self):
        return sum(item.cout_total for item in self.materiaux.all())


class MateriauBonCommande(models.Model):
    bon_commande = models.ForeignKey(BonCommande, on_delete=models.CASCADE, related_name='materiaux')
    materiau = models.ForeignKey(ListeMateriaux, on_delete=models.CASCADE)
    
    quantite = models.DecimalField(max_digits=10, decimal_places=2)
    unite = models.CharField(max_length=20, choices=[('kg', 'Kilogramme'), ('tonne', 'Tonne'), ('m³', 'Mètre cube')])

    @property
    def cout_total(self):
        return self.quantite * self.materiau.prix_unitaire
