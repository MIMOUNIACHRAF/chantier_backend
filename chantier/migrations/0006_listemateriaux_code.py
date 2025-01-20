from django.db import migrations, models
from django.utils.crypto import get_random_string

def set_default_codes(apps, schema_editor):
    ListeMateriaux = apps.get_model("chantier", "ListeMateriaux")
    for materiau in ListeMateriaux.objects.all():
        # Génère un code aléatoire unique
        unique_code = get_random_string(8)
        while ListeMateriaux.objects.filter(code=unique_code).exists():
            unique_code = get_random_string(8)  # Assure unicité
        materiau.code = unique_code
        materiau.save()

class Migration(migrations.Migration):

    dependencies = [
        ('chantier', '0005_materiauboncommande_option'),
    ]

    operations = [
        migrations.AddField(
            model_name='listemateriaux',
            name='code',
            field=models.CharField(max_length=10, null=True, unique=True),
        ),
        migrations.RunPython(set_default_codes),  # Exécute la fonction pour remplir les codes
    ]
