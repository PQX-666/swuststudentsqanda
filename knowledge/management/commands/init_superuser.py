"""自动创建超级用户（仅在不存在时）"""
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = '创建超级用户（安全：已存在则跳过）'

    def handle(self, *_args, **_options):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.WARNING('超级用户已存在，跳过'))
            return

        username = os.environ.get('SUPERUSER_USERNAME', 'admin')
        email = os.environ.get('SUPERUSER_EMAIL', 'admin@swust.edu')
        password = os.environ.get('SUPERUSER_PASSWORD', 'swust2026guide')
        User.objects.create_superuser(username, email, password)
        self.stdout.write(self.style.SUCCESS(f'超级用户 {username} 创建成功'))
