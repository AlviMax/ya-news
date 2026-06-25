# news/tests/test_content.py
# Импортируйте нужные классы.
from datetime import datetime, timedelta

from django.conf import settings
from django.test import TestCase
# Импортируем функцию reverse(), она понадобится для получения адреса страницы.
from django.urls import reverse
# Импортируем функцию для получения модели пользователя.
from django.contrib.auth import get_user_model
from django.utils import timezone

from news.models import Comment, News
# Импортируем класс формы.
from news.forms import CommentForm


User = get_user_model()


class TestHomePage(TestCase):
    """Тестирование домашней страницы."""

    # Вынесем ссылку на домашнюю страницу в атрибуты класса.
    HOME_URL = reverse('news:home')

    @classmethod
    def setUpTestData(cls):
        """Настраиваем фикстуру.

        В частности здесь мы формируем базу данных новостей,
        убывающих по дате
        """
        # Вычисляем текущую дату.
        today = datetime.today()

        # Создаем пустой список, который наполним ниже 10-ю объектами
        all_news = []
        for index in range(settings.NEWS_COUNT_ON_HOME_PAGE + 1):
            news = News(
                title=f'Новость {index}',
                text='Просто текст.',
                date=today - timedelta(days=index)
            )
            all_news.append(news)  # дополняем список новым объектом

        # Используем метод группового создания объектов bulk_create()
        News.objects.bulk_create(all_news)

    def test_news_count(self):
        """Получаем длину списка с объектами новостей.

        Сравниваем её с константой из настроек settings.NEWS_COUNT_ON_HOME_PAGE
        """
        # Загружаем главную страницу.
        response = self.client.get(self.HOME_URL)

        # Код ответа не проверяем, его уже проверили в тестах маршрутов.
        # Получаем список объектов из словаря контекста.
        object_list = response.context['object_list']

        # Определяем количество записей в списке.
        news_count = object_list.count()

        # Проверяем, что на странице именно 10 новостей.
        self.assertEqual(news_count, settings.NEWS_COUNT_ON_HOME_PAGE)

    def test_news_order(self):
        """
        Тестируем сортировку новостей.

        Проверяем: новости отсортированы от самой свежей к самой старой.
        Свежие новости в начале списка.
        """
        # Запрос к главной странице
        response = self.client.get(self.HOME_URL)

        # Django забирает новости из БД (отсортированные по Meta.ordering)
        object_list = response.context['object_list']

        # Получаем даты новостей в том порядке, как они выведены на странице.
        # используем генератор списка (list comprehension): "Для каждой новости
        # (news) из списка object_list возьми её дату (news.date) и добавь
        # в новый список all_dates."
        all_dates = [news.date for news in object_list]

        # Сортируем полученный список по убыванию.
        sorted_dates = sorted(all_dates, reverse=True)

        # Проверяем, что исходный список был отсортирован правильно.
        self.assertEqual(all_dates, sorted_dates)


class TestDetailPage(TestCase):
    """Тестирование страницы отдельной новости.

    Тестируем сортировку комментариев на странице новости
    """

    @classmethod
    def setUpTestData(cls):
        """Создаём тестовые данные: новость, автора и 10 комментариев."""
        # Создаем в БД запись новости
        cls.news = News.objects.create(
            title='Тестовая новость', text='Просто текст.'
        )

        # Сохраняем в переменную адрес страницы с новостью:
        cls.detail_url = reverse('news:detail', args=(cls.news.id,))

        # Создаём автора комментариев
        cls.author = User.objects.create(username='Комментатор')

        # Запоминаем текущее время (изменили datetime.now() на timezone.now(),
        # т.к. поле created поддерживает время с часовыми поясами и это
        # вызывало ошибку Django при datetime.now()) - без часового пояса):
        now = timezone.now()

        # Создаём комментарии в цикле.
        for index in range(10):
            # Создаём объект и записываем его в переменную.
            comment = Comment.objects.create(
                news=cls.news, author=cls.author, text=f'Tекст {index}',
            )

            # Сразу после создания меняем время создания комментария.
            comment.created = now + timedelta(days=index)

            # И сохраняем эти изменения.
            comment.save()

    def test_comments_order(self):
        """Тестируем сортировку комментариев.

        Получим список всех временных меток комментариев, отсортируем их и
        убедимся, что отсортированный список идентичен исходному.
        """
        # Запрос к странице новости
        response = self.client.get(self.detail_url)

        # Проверяем, что объект новости находится в словаре контекста
        # под ожидаемым именем - названием модели.
        self.assertIn('news', response.context)

        # Получаем объект новости.
        news = response.context['news']

        # Получаем все комментарии к новости.
        all_comments = news.comment_set.all()

        # Собираем временные метки всех комментариев.
        all_timestamps = [comment.created for comment in all_comments]

        # Сортируем временные метки, менять порядок сортировки не надо.
        sorted_timestamps = sorted(all_timestamps)

        # Проверяем, что временные метки отсортированы правильно.
        self.assertEqual(all_timestamps, sorted_timestamps)

    #
    def test_anonymous_client_has_no_form(self):
        """Тест проверяет.

        Что при запросе анонимного пользователя форма
        не передаётся в словаре контекста.
        """
        response = self.client.get(self.detail_url)
        self.assertNotIn('form', response.context)

    #
    def test_authorized_client_has_form(self):
        """Тест проверяет.

        Что при запросе авторизованного пользователя
        форма передаётся в словаре.
        """
        # Авторизуем клиент при помощи ранее созданного пользователя.
        self.client.force_login(self.author)
        response = self.client.get(self.detail_url)
        self.assertIn('form', response.context)

        # Проверим, что объект формы соответствует нужному классу формы.
        self.assertIsInstance(response.context['form'], CommentForm)
