import json
from datetime import timedelta
from django.conf import settings
from django.db.models import Q, F, Count
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from .models import Category, KnowledgeItem, SearchLog, Feedback, UnansweredQuestion


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def get_stats():
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        'total_published': KnowledgeItem.objects.filter(is_published=True).count(),
        'total_categories': Category.objects.filter(is_active=True).count(),
        'total_searches': SearchLog.objects.count(),
        'today_searches': SearchLog.objects.filter(created_at__gte=today_start).count(),
        'no_result_searches': SearchLog.objects.filter(has_result=False).count(),
        'total_helpful': Feedback.objects.filter(is_helpful=True).count(),
        'total_unhelpful': Feedback.objects.filter(is_helpful=False).count(),
    }


def home(request):
    categories = Category.objects.filter(is_active=True).order_by('sort_order')
    featured_items = KnowledgeItem.objects.filter(
        is_published=True, is_featured=True
    ).select_related('category')[:6]
    recent_items = KnowledgeItem.objects.filter(
        is_published=True
    ).select_related('category').order_by('-updated_at')[:6]
    popular_items = KnowledgeItem.objects.filter(
        is_published=True
    ).select_related('category').order_by('-view_count', '-is_featured')[:8]
    popular_keywords = SearchLog.objects.filter(
        has_result=True
    ).values('keyword').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    stats = get_stats()

    return render(request, 'home.html', {
        'categories': categories,
        'featured_items': featured_items,
        'recent_items': recent_items,
        'popular_items': popular_items,
        'popular_keywords': popular_keywords,
        'stats': stats,
    })


def search(request):
    query = request.GET.get('q', '').strip()
    if not query:
        return render(request, 'search_results.html', {
            'query': '',
            'results': [],
            'result_count': 0,
        })

    if len(query) > settings.MAX_SEARCH_KEYWORD_LENGTH:
        query = query[:settings.MAX_SEARCH_KEYWORD_LENGTH]

    results = KnowledgeItem.objects.filter(is_published=True).select_related('category')

    # 搜索：标题、关键词、简短答案、详细答案
    results = results.filter(
        Q(title__icontains=query) |
        Q(keywords__icontains=query) |
        Q(short_answer__icontains=query) |
        Q(detailed_answer__icontains=query)
    )

    # 排序：标题完全匹配 > 标题包含 > 关键词包含 > 答案包含
    results = results.annotate(
        title_exact=Q(title__iexact=query),
        title_contains=Q(title__icontains=query),
        keywords_contains=Q(keywords__icontains=query),
    ).order_by(
        '-title_exact', '-title_contains', '-keywords_contains', '-updated_at'
    )

    result_count = results.count()
    results = results[:settings.MAX_SEARCH_RESULTS]

    # 记录搜索日志
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    SearchLog.objects.create(
        keyword=query,
        result_count=result_count,
        has_result=result_count > 0,
        session_key=session_key or '',
        ip_address=get_client_ip(request),
    )

    return render(request, 'search_results.html', {
        'query': query,
        'results': results,
        'result_count': result_count,
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug, is_active=True)
    items = KnowledgeItem.objects.filter(
        is_published=True, category=category
    ).order_by('-is_featured', '-updated_at')

    return render(request, 'category_detail.html', {
        'category': category,
        'items': items,
    })


def question_detail(request, pk):
    item = get_object_or_404(KnowledgeItem, pk=pk)

    # 未发布的问题只允许管理员预览
    if not item.is_published and not request.user.is_staff:
        return render(request, '404.html', status=404)

    # 增加浏览次数
    KnowledgeItem.objects.filter(pk=pk).update(view_count=F('view_count') + 1)
    item.refresh_from_db()

    # 相关问题：同分类 + 相似关键词
    related_items = KnowledgeItem.objects.filter(
        is_published=True
    ).exclude(pk=pk)

    related = related_items.filter(category=item.category)[:3]
    if related.count() < 5 and item.keywords:
        keyword_list = [k.strip() for k in item.keywords.split(',') if k.strip()]
        q = Q()
        for kw in keyword_list[:3]:
            q |= Q(keywords__icontains=kw)
        extra = related_items.filter(q).exclude(
            pk__in=[r.pk for r in related] + [pk]
        )[:5 - related.count()]
        related = list(related) + list(extra)

    # 不足则用推荐填充
    if len(related) < 5:
        extra = KnowledgeItem.objects.filter(
            is_published=True, is_featured=True
        ).exclude(
            pk__in=[r.pk for r in related] + [pk]
        )[:5 - len(related)]
        related = list(related) + list(extra)

    return render(request, 'question_detail.html', {
        'item': item,
        'related_items': related[:5],
    })


@require_POST
def submit_feedback(request, pk):
    item = get_object_or_404(KnowledgeItem, pk=pk, is_published=True)

    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key

    # Session 限制重复提交
    cooldown = getattr(settings, 'FEEDBACK_COOLDOWN_SECONDS', 300)
    recent = Feedback.objects.filter(
        knowledge_item=item,
        session_key=session_key,
        created_at__gte=timezone.now() - timedelta(seconds=cooldown)
    )
    if recent.exists():
        return JsonResponse({'ok': False, 'msg': '您刚刚已提交过反馈，请稍后再试。'})

    is_helpful = request.POST.get('is_helpful', 'true') == 'true'
    comment = request.POST.get('comment', '').strip()
    if len(comment) > settings.MAX_FEEDBACK_COMMENT_LENGTH:
        comment = comment[:settings.MAX_FEEDBACK_COMMENT_LENGTH]

    Feedback.objects.create(
        knowledge_item=item,
        is_helpful=is_helpful,
        comment=comment,
        session_key=session_key,
        ip_address=get_client_ip(request),
    )

    # 更新计数
    if is_helpful:
        KnowledgeItem.objects.filter(pk=pk).update(helpful_count=F('helpful_count') + 1)
    else:
        KnowledgeItem.objects.filter(pk=pk).update(unhelpful_count=F('unhelpful_count') + 1)

    return JsonResponse({'ok': True})


def submit_question(request):
    if request.method == 'POST':
        question = request.POST.get('question', '').strip()
        description = request.POST.get('description', '').strip()

        if not question:
            return render(request, 'submit_question.html', {
                'error': '请输入您想咨询的问题。',
            })

        if len(question) > settings.MAX_UNANSWERED_QUESTION_LENGTH:
            question = question[:settings.MAX_UNANSWERED_QUESTION_LENGTH]
        if len(description) > settings.MAX_UNANSWERED_DESCRIPTION_LENGTH:
            description = description[:settings.MAX_UNANSWERED_DESCRIPTION_LENGTH]

        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key

        # Session 限制：短时间内不能重复提交相同问题
        recent = UnansweredQuestion.objects.filter(
            question=question,
            session_key=session_key,
            created_at__gte=timezone.now() - timedelta(seconds=300)
        )
        if recent.exists():
            return render(request, 'submit_success.html', {
                'message': '您已提交过相同问题，我们会尽快处理。'
            })

        UnansweredQuestion.objects.create(
            question=question,
            description=description,
            session_key=session_key,
        )

        return render(request, 'submit_success.html', {
            'message': '您的问题已提交成功，我们会尽快整理补充。'
        })

    return render(request, 'submit_question.html')


def about(request):
    return render(request, 'about.html', {
        'stats': get_stats(),
    })


def handler404(request, exception=None):
    return render(request, '404.html', status=404)


def handler500(request):
    return render(request, '500.html', status=500)
