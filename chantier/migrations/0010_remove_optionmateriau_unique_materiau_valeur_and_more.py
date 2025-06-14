# Generated by Django 5.1.4 on 2025-01-15 23:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chantier', '0009_paiement_boncommande_paiement'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='optionmateriau',
            name='unique_materiau_valeur',
        ),
        migrations.AddField(
            model_name='optionmateriau',
            name='type',
            field=models.CharField(choices=[('gros_oeuvre', 'Gros œuvre'), ('finition', 'Finition'), ('main_doeuvre', 'Main d’œuvre')], default='main_doeuvre', max_length=20),
        ),
        migrations.AlterField(
            model_name='listemateriaux',
            name='type',
            field=models.CharField(choices=[('gros_oeuvre', 'Gros œuvre'), ('finition', 'Finition'), ('main_doeuvre', 'Main d’œuvre')], max_length=20),
        ),
        migrations.AddConstraint(
            model_name='optionmateriau',
            constraint=models.UniqueConstraint(fields=('materiau', 'valeur', 'type'), name='unique_materiau_valeur'),
        ),
    ]
