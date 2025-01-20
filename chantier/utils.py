# chantier/utils.py
from chantier.models import PartieChantier

def get_default_partie():
    # Returns a default PartieChantier instance or the first one
    return PartieChantier.objects.first()
