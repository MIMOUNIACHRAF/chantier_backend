from django.contrib import admin
from .models import *

admin.site.register(Chantier)
admin.site.register(ListeMateriaux)
admin.site.register(BonCommande)
admin.site.register(MateriauBonCommande)