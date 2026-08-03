from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from .models import Category, KnowledgeItem, SearchLog, Feedback, UnansweredQuestion


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'sort_order', 'is_active', 'item_count', 'updated_at']
    list_editable = ['sort_order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ['name']}
    ordering = ['sort_order']

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _item_count=Count('items', filter=Q(items__is_published=True))
        )

    def item_count(self, obj):
        return getattr(obj, '_item_count', 0)
    item_count.short_description = '已发布条目数'
    item_count.admin_order_field = '_item_count'


@admin.register(KnowledgeItem)
class KnowledgeItemAdmin(admin.ModelAdmin):
    list_display = [
        'title', 'category', 'information_type', 'is_published', 'is_featured',
        'view_count', 'helpful_rate_display', 'verified_at', 'updated_at'
    ]
    list_filter = ['is_published', 'is_featured', 'information_type', 'category']
    search_fields = ['title', 'keywords', 'short_answer', 'detailed_answer']
    list_editable = ['is_published', 'is_featured']
    readonly_fields = ['view_count', 'helpful_count', 'unhelpful_count',
                       'created_at', 'updated_at']
    actions = ['make_published', 'make_unpublished', 'make_featured', 'make_not_featured']
    fieldsets = [
        ('基本信息', {
            'fields': ['title', 'short_answer', 'detailed_answer', 'category', 'keywords']
        }),
        ('信息属性', {
            'fields': ['information_type', 'source_name', 'source_url',
                       'applicable_audience', 'verified_at']
        }),
        ('发布状态', {
            'fields': ['is_published', 'is_featured']
        }),
        ('统计数据', {
            'fields': ['view_count', 'helpful_count', 'unhelpful_count']
        }),
        ('时间信息', {
            'fields': ['created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]

    @admin.display(description='帮助率')
    def helpful_rate_display(self, obj):
        rate = obj.helpful_rate
        if rate is None:
            return '暂无反馈'
        return f'{rate}%'

    @admin.action(description='批量发布')
    def make_published(self, request, queryset):
        queryset.update(is_published=True)

    @admin.action(description='批量下架')
    def make_unpublished(self, request, queryset):
        queryset.update(is_published=False)

    @admin.action(description='设为推荐')
    def make_featured(self, request, queryset):
        queryset.update(is_featured=True)

    @admin.action(description='取消推荐')
    def make_not_featured(self, request, queryset):
        queryset.update(is_featured=False)


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ['keyword', 'result_count', 'has_result', 'clicked_result', 'created_at']
    list_filter = ['has_result', 'clicked_result', 'created_at']
    search_fields = ['keyword', 'session_key']
    readonly_fields = ['keyword', 'result_count', 'has_result', 'session_key',
                       'ip_address', 'clicked_result', 'created_at']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ['knowledge_item', 'is_helpful', 'comment_preview', 'created_at']
    list_filter = ['is_helpful', 'created_at']
    search_fields = ['knowledge_item__title', 'comment']
    readonly_fields = ['knowledge_item', 'is_helpful', 'comment', 'session_key',
                       'ip_address', 'created_at']
    date_hierarchy = 'created_at'

    @admin.display(description='补充意见')
    def comment_preview(self, obj):
        if obj.comment:
            return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
        return '-'

    def has_add_permission(self, request):
        return False


@admin.register(UnansweredQuestion)
class UnansweredQuestionAdmin(admin.ModelAdmin):
    list_display = ['question', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    list_editable = ['status']
    search_fields = ['question', 'description']
    readonly_fields = ['question', 'description', 'session_key', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False
