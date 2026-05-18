"""SaaS app — funcionalidad de signup público + planes + suscripciones.

App OPCIONAL. Para activarla, agregar `'saas'` a INSTALLED_APPS y
correr migraciones. Se diseñó para que NO afecte el funcionamiento de
core: no toca modelos de core ni endpoints existentes. Sólo agrega
nuevos endpoints en `/api/saas/...`.

Pensada para una segunda instancia del sistema (otro dominio/sitio
web) que sirva el flujo de "registrate como empresa nueva". Las
empresas creadas vía SaaS conviven sin problema con la existente
AUTO OFERTAS gracias al multi-tenancy ya en place.
"""

from django.apps import AppConfig


class SaasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'saas'
    verbose_name = 'SaaS — Suscripciones y signup público'
