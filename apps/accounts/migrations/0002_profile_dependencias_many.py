# Migration: replace dependencia ForeignKey with dependencias ManyToManyField on Profile.
# We copy existing FK data into the M2M table before removing the FK.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('documents', '0002_dependencia_document_dependencia'),
    ]

    operations = [
        # 1. Add the new M2M field (intermediary table created automatically)
        migrations.AddField(
            model_name='profile',
            name='dependencias',
            field=models.ManyToManyField(
                blank=True,
                related_name='profiles_m2m',
                to='documents.dependencia',
                verbose_name='dependencias',
            ),
        ),
        # 2. Copy existing FK values into the M2M table
        migrations.RunSQL(
            sql="""
                INSERT INTO accounts_profile_dependencias (profile_id, dependencia_id)
                SELECT id, dependencia_id
                FROM accounts_profile
                WHERE dependencia_id IS NOT NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
        # 3. Remove the old FK field
        migrations.RemoveField(
            model_name='profile',
            name='dependencia',
        ),
    ]
