from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Category, KnowledgeItem, SearchLog, Feedback, UnansweredQuestion


class HomePageTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name='报到入学', slug='baodao')
        self.item = KnowledgeItem.objects.create(
            title='新生报到需要准备什么？',
            short_answer='携带录取通知书、身份证等材料。',
            detailed_answer='详细说明...',
            category=self.cat,
            is_published=True,
        )

    def test_home_page_opens(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SWUST 新生指南')

    def test_published_item_shown(self):
        response = self.client.get('/')
        self.assertContains(response, '新生报到需要准备什么')

    def test_unpublished_item_not_shown(self):
        self.item.is_published = False
        self.item.save()
        response = self.client.get('/')
        self.assertNotContains(response, '新生报到需要准备什么')

    def test_unpublished_item_returns_404_for_public(self):
        self.item.is_published = False
        self.item.save()
        response = self.client.get(reverse('question_detail', args=[self.item.pk]))
        self.assertEqual(response.status_code, 404)


class SearchTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name='转专业', slug='zhuanzhuanye')
        self.item1 = KnowledgeItem.objects.create(
            title='大一可以转专业吗？',
            short_answer='可以，大一和大二各有一次机会。',
            detailed_answer='转出无门槛...',
            category=self.cat,
            keywords='转专业,大一',
            is_published=True,
        )
        self.item2 = KnowledgeItem.objects.create(
            title='转专业需要什么条件？',
            short_answer='热门专业需要看绩点和面试。',
            detailed_answer='根据目标专业不同...',
            category=self.cat,
            keywords='转专业,条件,绩点',
            is_published=True,
        )
        self.item3 = KnowledgeItem.objects.create(
            title='宿舍条件怎么样？',
            short_answer='4人间和6人间可选。',
            detailed_answer='宿舍已全面升级...',
            category=Category.objects.create(name='宿舍生活', slug='sushe'),
            is_published=True,
        )

    def test_title_search(self):
        response = self.client.get('/search/', {'q': '转专业'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '大一可以转专业吗')
        self.assertContains(response, '转专业需要什么条件')

    def test_answer_search(self):
        response = self.client.get('/search/', {'q': '绩点'})
        self.assertContains(response, '转专业需要什么条件')

    def test_search_creates_log(self):
        count_before = SearchLog.objects.count()
        self.client.get('/search/', {'q': '转专业'})
        self.assertEqual(SearchLog.objects.count(), count_before + 1)
        log = SearchLog.objects.latest('created_at')
        self.assertEqual(log.keyword, '转专业')
        self.assertTrue(log.has_result)

    def test_no_result_search_logged(self):
        self.client.get('/search/', {'q': '钢琴房'})
        log = SearchLog.objects.latest('created_at')
        self.assertEqual(log.keyword, '钢琴房')
        self.assertFalse(log.has_result)
        self.assertEqual(log.result_count, 0)

    def test_keyword_length_limit(self):
        long_query = 'x' * 200
        response = self.client.get('/search/', {'q': long_query})
        self.assertEqual(response.status_code, 200)

    def test_search_excludes_unpublished(self):
        self.item1.is_published = False
        self.item1.save()
        response = self.client.get('/search/', {'q': '转专业'})
        self.assertNotContains(response, '大一可以转专业吗')
        self.assertContains(response, '转专业需要什么条件')


class QuestionDetailTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name='报到入学', slug='baodao')
        self.item = KnowledgeItem.objects.create(
            title='测试问题',
            short_answer='简短答案。',
            detailed_answer='详细答案。',
            category=self.cat,
            is_published=True,
            view_count=10,
        )

    def test_view_count_increases(self):
        url = reverse('question_detail', args=[self.item.pk])
        self.client.get(url)
        self.item.refresh_from_db()
        self.assertEqual(self.item.view_count, 11)

    def test_question_detail_shows_content(self):
        url = reverse('question_detail', args=[self.item.pk])
        response = self.client.get(url)
        self.assertContains(response, '测试问题')
        self.assertContains(response, '简短答案')


class FeedbackTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat = Category.objects.create(name='报到入学', slug='baodao')
        self.item = KnowledgeItem.objects.create(
            title='测试问题',
            short_answer='简短答案。',
            category=self.cat,
            is_published=True,
        )
        self.url = reverse('submit_feedback', args=[self.item.pk])

    def test_helpful_feedback(self):
        response = self.client.post(self.url, {'is_helpful': 'true', 'comment': ''})
        self.assertEqual(response.json()['ok'], True)
        self.item.refresh_from_db()
        self.assertEqual(self.item.helpful_count, 1)

    def test_unhelpful_feedback(self):
        response = self.client.post(self.url, {'is_helpful': 'false', 'comment': '不够详细'})
        self.assertEqual(response.json()['ok'], True)
        self.item.refresh_from_db()
        self.assertEqual(self.item.unhelpful_count, 1)

    def test_duplicate_feedback_cooldown(self):
        self.client.post(self.url, {'is_helpful': 'true', 'comment': ''})
        response = self.client.post(self.url, {'is_helpful': 'false', 'comment': ''})
        self.assertEqual(response.json()['ok'], False)


class UnansweredQuestionTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_submit_unanswered_question(self):
        response = self.client.post(reverse('submit_question'), {
            'question': '学校附近有健身房吗？',
            'description': '想了解价格',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '提交成功')
        self.assertEqual(UnansweredQuestion.objects.count(), 1)

    def test_empty_question_rejected(self):
        response = self.client.post(reverse('submit_question'), {
            'question': '',
            'description': '',
        })
        self.assertEqual(UnansweredQuestion.objects.count(), 0)

    def test_submit_page_opens(self):
        response = self.client.get(reverse('submit_question'))
        self.assertEqual(response.status_code, 200)


class CategoryPageTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.cat1 = Category.objects.create(name='报到入学', slug='baodao')
        self.cat2 = Category.objects.create(name='宿舍生活', slug='sushe')
        self.item1 = KnowledgeItem.objects.create(
            title='报到问题', short_answer='答案1', category=self.cat1, is_published=True
        )
        self.item2 = KnowledgeItem.objects.create(
            title='宿舍问题', short_answer='答案2', category=self.cat2, is_published=True
        )

    def test_category_only_shows_own_items(self):
        url = reverse('category_detail', args=[self.cat1.slug])
        response = self.client.get(url)
        self.assertContains(response, '报到问题')
        self.assertNotContains(response, '宿舍问题')

    def test_category_404_for_inactive(self):
        self.cat1.is_active = False
        self.cat1.save()
        url = reverse('category_detail', args=[self.cat1.slug])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class AdminTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser('admin', 'admin@test.com', 'testpass123')

    def test_admin_accessible_by_staff(self):
        self.client.login(username='admin', password='testpass123')
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)

    def test_admin_inaccessible_by_anonymous(self):
        response = self.client.get('/admin/')
        self.assertNotEqual(response.status_code, 200)


class AboutPageTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_about_page_opens(self):
        response = self.client.get('/about/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '免责声明')
        self.assertContains(response, '隐私说明')


class ContentExpiryTest(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='测试分类', slug='test')
        self.item = KnowledgeItem.objects.create(
            title='过期测试', short_answer='答案',
            category=self.cat, is_published=True,
        )

    def test_item_without_verified_at_is_expired(self):
        self.assertTrue(self.item.is_expired)

    def test_recently_verified_item_is_not_expired(self):
        self.item.verified_at = date.today()
        self.item.save()
        self.assertFalse(self.item.is_expired)

    def test_old_verified_item_is_expired(self):
        from django.conf import settings
        days = getattr(settings, 'CONTENT_VERIFY_EXPIRY_DAYS', 180)
        self.item.verified_at = date.today() - timedelta(days=days + 10)
        self.item.save()
        self.assertTrue(self.item.is_expired)


class HelpfulRateTest(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='测试', slug='test')
        self.item = KnowledgeItem.objects.create(
            title='测试问题', short_answer='答案',
            category=self.cat, is_published=True,
            helpful_count=0, unhelpful_count=0,
        )

    def test_no_feedback_returns_none(self):
        self.assertIsNone(self.item.helpful_rate)

    def test_helpful_rate_calculation(self):
        self.item.helpful_count = 8
        self.item.unhelpful_count = 2
        self.item.save()
        self.assertEqual(self.item.helpful_rate, 80.0)
