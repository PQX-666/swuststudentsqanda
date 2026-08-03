"""首次部署时初始化数据库（仅在数据为空时导入）"""
from django.core.management.base import BaseCommand
from knowledge.models import KnowledgeItem


class Command(BaseCommand):
    help = '首次部署时初始化数据（安全：已有数据则跳过）'

    def handle(self, *_args, **_options):
        if KnowledgeItem.objects.count() > 0:
            self.stdout.write(self.style.WARNING('数据已存在，跳过初始化'))
            return
        self.stdout.write('数据库为空，开始导入 100 问...')
        from django.core.management import call_command
        call_command('import_100q', 'doc_100.txt')
