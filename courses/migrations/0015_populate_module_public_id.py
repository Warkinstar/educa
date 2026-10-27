import uuid
from django.db import migrations

def gen_uuid(apps, schema_editor):
    Module = apps.get_model('courses', 'Module')
    for module in Module.objects.all():
        module.public_id = uuid.uuid4()
        module.save(update_fields=['public_id'])

class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0014_add_module_public_id_nullable'),  # тут имя предыдущей миграции
    ]

    operations = [
        migrations.RunPython(gen_uuid, reverse_code=migrations.RunPython.noop),
    ]