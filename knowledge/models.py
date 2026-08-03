from django.db import models
from django.conf import settings
from django.utils import timezone


class Category(models.Model):
    name = models.CharField('分类名称', max_length=100)
    slug = models.SlugField('分类标识', max_length=100, unique=True)
    description = models.TextField('分类说明', blank=True, default='')
    sort_order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '问题分类'
        verbose_name_plural = verbose_name
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.name


class KnowledgeItem(models.Model):
    INFORMATION_TYPES = [
        ('official', '学校官方信息'),
        ('curated', '管理员整理'),
        ('experience', '学长学姐经验'),
        ('reference', '普通参考信息'),
    ]

    title = models.CharField('问题标题', max_length=200)
    short_answer = models.TextField('简短答案')
    detailed_answer = models.TextField('详细答案', blank=True, default='')
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='items', verbose_name='所属分类'
    )
    keywords = models.CharField(
        '关键词', max_length=300, blank=True, default='',
        help_text='多个关键词用逗号分隔'
    )
    information_type = models.CharField(
        '信息类型', max_length=20, choices=INFORMATION_TYPES, default='curated'
    )
    source_name = models.CharField('来源名称', max_length=200, blank=True, default='')
    source_url = models.URLField('来源链接', blank=True, default='')
    applicable_audience = models.CharField(
        '适用对象', max_length=200, blank=True, default=''
    )
    verified_at = models.DateField('最后核验时间', null=True, blank=True)
    view_count = models.PositiveIntegerField('浏览次数', default=0)
    helpful_count = models.PositiveIntegerField('有帮助数量', default=0)
    unhelpful_count = models.PositiveIntegerField('没有帮助数量', default=0)
    is_featured = models.BooleanField('是否推荐', default=False)
    is_published = models.BooleanField('是否发布', default=False)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '知识条目'
        verbose_name_plural = verbose_name
        ordering = ['-is_featured', '-updated_at']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['category']),
            models.Index(fields=['is_published']),
            models.Index(fields=['is_featured']),
            models.Index(fields=['updated_at']),
        ]

    def __str__(self):
        return self.title

    @property
    def total_feedback(self):
        return self.helpful_count + self.unhelpful_count

    @property
    def helpful_rate(self):
        total = self.total_feedback
        if total == 0:
            return None
        return round(self.helpful_count / total * 100, 1)

    @property
    def is_expired(self):
        if self.verified_at is None:
            return True
        days = getattr(settings, 'CONTENT_VERIFY_EXPIRY_DAYS', 180)
        return (timezone.now().date() - self.verified_at).days > days


class SearchLog(models.Model):
    keyword = models.CharField('搜索关键词', max_length=200)
    result_count = models.PositiveIntegerField('结果数量', default=0)
    has_result = models.BooleanField('是否有结果', default=False)
    session_key = models.CharField('Session标识', max_length=100, blank=True, default='')
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    clicked_result = models.BooleanField('是否点击结果', default=False)
    created_at = models.DateTimeField('搜索时间', auto_now_add=True)

    class Meta:
        verbose_name = '搜索记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.keyword


class Feedback(models.Model):
    knowledge_item = models.ForeignKey(
        KnowledgeItem, on_delete=models.CASCADE, related_name='feedbacks',
        verbose_name='对应问题'
    )
    is_helpful = models.BooleanField('是否有帮助')
    comment = models.TextField('补充意见', blank=True, default='')
    session_key = models.CharField('Session标识', max_length=100, blank=True, default='')
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    created_at = models.DateTimeField('反馈时间', auto_now_add=True)

    class Meta:
        verbose_name = '内容反馈'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        status = '有帮助' if self.is_helpful else '没有帮助'
        return f'{self.knowledge_item.title} - {status}'


class UnansweredQuestion(models.Model):
    STATUS_CHOICES = [
        ('pending', '待处理'),
        ('answered', '已补充答案'),
        ('ignored', '暂不处理'),
    ]

    question = models.CharField('问题内容', max_length=200)
    description = models.TextField('补充说明', blank=True, default='')
    session_key = models.CharField('Session标识', max_length=100, blank=True, default='')
    status = models.CharField(
        '处理状态', max_length=20, choices=STATUS_CHOICES, default='pending'
    )
    created_at = models.DateTimeField('提交时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '未解决问题'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.question
