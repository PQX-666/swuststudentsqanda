from django import template
from django.utils.safestring import mark_safe
from markdown_it import MarkdownIt

register = template.Library()

_md = MarkdownIt('commonmark', {'html': False, 'linkify': True, 'typographer': True})


@register.filter(name='render_markdown')
def render_markdown(text):
    """安全地将 Markdown 文本渲染为 HTML，不允许原始 HTML 标签。"""
    if not text:
        return ''
    html = _md.render(text)
    return mark_safe(html)
