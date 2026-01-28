import uuid
from django.db import migrations, models

def gen_uuid(apps, schema_editor):
    GeneratedOutput = apps.get_model('profiler', 'GeneratedOutput')
    for row in GeneratedOutput.objects.all():
        row.uuid_id = uuid.uuid4()
        row.save(update_fields=['uuid_id'])

class Migration(migrations.Migration):

    dependencies = [
        ('profiler', '0001_initial'),
    ]

    operations = [
        # 1. Add other fields first
        migrations.AddField(
            model_name='generatedoutput',
            name='raw_content',
            field=models.TextField(default=''),
        ),
        migrations.AddField(
            model_name='generatedoutput',
            name='structured_content',
            field=models.JSONField(blank=True, null=True),
        ),
        # 2. Add UUID as nullable without unique=True initially
        migrations.AddField(
            model_name='generatedoutput',
            name='uuid_id',
            field=models.UUIDField(editable=False, null=True),
        ),
        # 3. Run the Python script to give everyone a unique ID
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
        # 4. Now that they are unique, alter the field to be unique and non-nullable
        migrations.AlterField(
            model_name='generatedoutput',
            name='uuid_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        # 5. Fix the output_type choices as you had in 0002
        migrations.AlterField(
            model_name='generatedoutput',
            name='output_type',
            field=models.CharField(choices=[('profile', 'Profile'), ('comparison', 'Comparison')], max_length=20),
        ),
    ]