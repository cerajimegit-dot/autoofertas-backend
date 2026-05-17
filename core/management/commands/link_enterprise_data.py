from django.core.management.base import BaseCommand
from core.models import Enterprise, Brand, Vehicle

class Command(BaseCommand):
    help = 'Relaciona vehículos y marcas con la empresa de pruebas'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("RELACIONANDO VEHÍCULOS Y MARCAS CON EMPRESA")
        self.stdout.write("=" * 80)

        # Obtener primera empresa (de pruebas)
        enterprise = Enterprise.objects.first()
        if not enterprise:
            self.stdout.write(self.style.ERROR('ERROR: No hay empresas'))
            return

        self.stdout.write(f"\nEmpresa destino: {enterprise.name} (ID: {enterprise.id})\n")

        # Actualizar marcas
        self.stdout.write("1. ACTUALIZANDO MARCAS...")
        self.stdout.write("-" * 80)
        
        orphan_brands = Brand.objects.filter(enterprise__isnull=True)
        count = orphan_brands.count()
        if count > 0:
            Brand.objects.filter(enterprise__isnull=True).update(enterprise=enterprise)
            self.stdout.write(self.style.SUCCESS(f'✓ {count} marcas asignadas'))

        total_brands = Brand.objects.filter(enterprise=enterprise).count()
        self.stdout.write(f'✓ Total marcas: {total_brands}')

        # Actualizar vehículos
        self.stdout.write("\n2. ACTUALIZANDO VEHÍCULOS...")
        self.stdout.write("-" * 80)
        
        orphan_vehicles = Vehicle.objects.filter(enterprise__isnull=True)
        count = orphan_vehicles.count()
        if count > 0:
            Vehicle.objects.filter(enterprise__isnull=True).update(enterprise=enterprise)
            self.stdout.write(self.style.SUCCESS(f'✓ {count} vehículos asignados'))

        total_vehicles = Vehicle.objects.filter(enterprise=enterprise).count()
        self.stdout.write(f'✓ Total vehículos: {total_vehicles}')

        # Resumen
        self.stdout.write("\n3. RESUMEN...")
        self.stdout.write("-" * 80)
        self.stdout.write(f'Empresa: {enterprise.name}')
        self.stdout.write(f'Marcas: {total_brands}')
        self.stdout.write(f'Vehículos: {total_vehicles}')
        self.stdout.write(self.style.SUCCESS('\n✓ ACTUALIZACIÓN COMPLETADA'))
