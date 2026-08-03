"""
从 100 问文档解析并导入知识条目
python manage.py import_100q doc_100.txt
"""
import re
from django.core.management.base import BaseCommand
from knowledge.models import Category, KnowledgeItem, SearchLog, Feedback, UnansweredQuestion

CAT_SLUG_MAP = {
    '报到入学': 'baodao', '宿舍生活': 'sushe', '军训准备': 'junxun',
    '选课考试': 'xuanke', '转专业': 'zhuanzhuanye', '专业学习': 'xuexi',
    '电脑选购': 'diannao', '社团班委': 'shetuan', '奖助学金': 'jiangzhu',
    '校园生活': 'xiaoyuan', '交通出行': 'jiaotong', '其他问题': 'qita',
}
INFO_TYPE_MAP = {
    '学校官方信息': 'official', '学长学姐经验': 'experience',
    '管理员整理': 'curated', '普通参考信息': 'reference',
}


def parse_meta_line(line):
    """Parse a meta line like: 分类：报到入学　｜　信息类型：学校官方信息　｜　适用对象：..."""
    result = {}
    # Split by full-width pipe
    parts = line.split('　｜　')
    if len(parts) <= 1:
        parts = line.split('｜')
    for part in parts:
        part = part.strip()
        # Match: field_name：value or field_name:value
        m = re.match(r'^([^：:]+)[：:]\s*(.*)', part)
        if m:
            result[m.group(1).strip()] = m.group(2).strip()
    return result


def parse_doc(filepath):
    with open(filepath, encoding='utf-8') as f:
        text = f.read()

    questions = []
    blocks = re.split(r'\n(?=Q\d{3}｜)', text)

    for block in blocks:
        if not block.startswith('Q'):
            continue

        lines = block.strip().split('\n')
        # Parse title: Q001｜title
        title_match = re.match(r'Q\d{3}｜(.+)', lines[0])
        if not title_match:
            continue
        title = title_match.group(1).strip()

        # The second line contains meta fields (分类, 信息类型, 适用对象)
        meta = {}
        content_lines = lines[1:]
        if len(content_lines) > 0:
            meta = parse_meta_line(content_lines[0])
            content_lines = content_lines[1:]

        # Parse remaining fields
        fields = dict(meta)
        current_field = None
        current_value = []

        for line in content_lines:
            m = re.match(r'^([^：:]+)[：:]\s*(.*)', line)
            if m:
                field_name = m.group(1).strip()
                # Check if this looks like a known field
                if field_name in ('关键词', '简短答案', '详细答案', '来源依据', '来源链接', '最后核验时间', '时效提醒'):
                    if current_field:
                        fields[current_field] = '\n'.join(current_value).strip()
                    current_field = field_name
                    current_value = [m.group(2)]
                    continue
            if current_field:
                current_value.append(line.strip())

        if current_field:
            fields[current_field] = '\n'.join(current_value).strip()

        questions.append({'title': title, **fields})

    return questions


class Command(BaseCommand):
    help = '导入100问知识库'

    def add_arguments(self, parser):
        parser.add_argument('filepath', type=str, help='100问文本文件路径')

    def handle(self, *args, **options):
        filepath = options['filepath']
        questions = parse_doc(filepath)
        self.stdout.write(f'Parsed {len(questions)} questions from document')

        # Reset data
        Feedback.objects.all().delete()
        SearchLog.objects.all().delete()
        UnansweredQuestion.objects.all().delete()
        KnowledgeItem.objects.all().delete()
        Category.objects.all().delete()
        from django.db import connection
        if connection.vendor == 'sqlite':
            cursor = connection.cursor()
            for table in ['knowledge_category', 'knowledge_knowledgeitem',
                          'knowledge_searchlog', 'knowledge_feedback',
                          'knowledge_unansweredquestion']:
                cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{table}'")

        # Create 12 categories
        cat_names = list(CAT_SLUG_MAP.keys())
        cats = {}
        for i, name in enumerate(cat_names):
            slug = CAT_SLUG_MAP[name]
            cat = Category.objects.create(name=name, slug=slug, sort_order=i, is_active=True)
            cats[name] = cat

        import random
        from datetime import date

        created = 0
        type_stats = {}
        for q in questions:
            # Category
            cat_name = q.get('分类', '').strip()
            cat = cats.get(cat_name)
            if not cat:
                for k in cats:
                    if k in cat_name or cat_name in k:
                        cat = cats[k]
                        break
            if not cat:
                cat = cats[cat_names[0]]

            # Info type
            info_type_raw = q.get('信息类型', '').strip()
            info_type = INFO_TYPE_MAP.get(info_type_raw, 'curated')
            type_stats[info_type_raw] = type_stats.get(info_type_raw, 0) + 1

            keywords = q.get('关键词', '').strip()
            short_answer = q.get('简短答案', '').strip()
            detailed_answer = q.get('详细答案', '').strip()
            source_raw = q.get('来源依据', '').strip()
            source_url = q.get('来源链接', '').strip()
            if source_url in ('未提供（导入时留空）', '未提供', ''):
                source_url = ''
            audience = q.get('适用对象', '').strip()
            verified_raw = q.get('最后核验时间', '').strip()

            source_name = source_raw
            if '｜' in source_name:
                source_name = source_name.split('｜')[0].strip()

            verified_at = None
            if verified_raw:
                m = re.search(r'(\d{4})\D*(\d{1,2})\D*(\d{1,2})', verified_raw)
                if m:
                    verified_at = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

            KnowledgeItem.objects.create(
                title=q['title'],
                short_answer=short_answer,
                detailed_answer=detailed_answer,
                category=cat,
                keywords=keywords,
                information_type=info_type,
                source_name=source_name,
                source_url=source_url,
                applicable_audience=audience,
                verified_at=verified_at,
                view_count=random.randint(5, 200),
                helpful_count=0,
                unhelpful_count=0,
                is_featured=False,
                is_published=True,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Imported {created} items'))
        self.stdout.write(f'  Categories: {Category.objects.count()}')
        self.stdout.write(f'  Info types: {type_stats}')
        self.stdout.write('  Next: python manage.py createsuperuser')
