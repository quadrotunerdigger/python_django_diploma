"""
Конфигурация приложения shopapp.

Регистрирует приложение ``shopapp`` в Django-проекте Megano.
Используется в ``INSTALLED_APPS`` настроек проекта.
"""

from django.apps import AppConfig


class ShopappConfig(AppConfig):
    """
    Класс конфигурации приложения интернет-магазина.

    Attributes:
        name: Имя приложения, используемое Django для автообнаружения
              моделей, admin-конфигурации, шаблонов и URL-маршрутов.
    """

    name: str = "shopapp"
