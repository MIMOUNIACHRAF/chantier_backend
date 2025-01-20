from django.contrib import admin
from .models import *

admin.site.register(Chantier)
admin.site.register(ListeMateriaux)
admin.site.register(BonCommande)
admin.site.register(MateriauBonCommande)
admin.site.register(PartieChantier)
admin.site.register(OptionMateriau)
admin.site.register(Paiement)