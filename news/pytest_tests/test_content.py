# news/pytest_tests/test_content.py
"""
Тесты содержимого страниц проекта ya_news на pytest.

Проверяют:
- Количество новостей на главной странице (пагинация).
- Сортировку новостей от новых к старым.
- Сортировку комментариев от старых к новым.
- Наличие формы комментария для авторизованных пользователей.
- Отсутствие формы комментария для анонимных пользователей.
"""
import pytest
from django.urls import reverse
from django.conf import settings

from news.forms import CommentForm


@pytest.mark.django_db
class TestHomePage:
    """
    Тестирование главной страницы.

    Проверяет:
    - Количество новостей на странице.
    - Сортировку новостей по дате.
    """

    def test_news_count(self, client, many_news):
        """
        Проверяет, что на главной странице отображается ровно
        NEWS_COUNT_ON_HOME_PAGE новостей.

        В фикстуре many_news создаётся 11 новостей,
        а на странице должно быть только 10.

        Аргументы:
            client: тестовый клиент
            many_news: фикстура с 11 новостями
        """
        # Получаем URL главной страницы
        url = reverse('news:home')
        # Выполняем GET-запрос
        response = client.get(url)
        # Получаем список новостей из контекста
        object_list = response.context['object_list']
        # Проверяем, что на странице 10 новостей
        assert object_list.count() == settings.NEWS_COUNT_ON_HOME_PAGE

    def test_news_order(self, client, many_news):
        """
        Проверяет, что новости отсортированы от новых к старым.

        Фикстура many_news создаёт новости с датами:
        сегодня, вчера, позавчера и т.д.
        На странице они должны идти в обратном порядке.

        Аргументы:
            client: тестовый клиент
            many_news: фикстура с новостями
        """
        # Получаем URL главной страницы
        url = reverse('news:home')
        # Выполняем GET-запрос
        response = client.get(url)
        # Получаем список новостей из контекста
        object_list = response.context['object_list']
        # Собираем даты новостей в список
        all_dates = [news.date for news in object_list]
        # Сортируем даты по убыванию (от новых к старым)
        sorted_dates = sorted(all_dates, reverse=True)
        # Проверяем, что порядок правильный
        assert all_dates == sorted_dates


@pytest.mark.django_db
class TestDetailPage:
    """
    Тестирование страницы отдельной новости.

    Проверяет:
    - Сортировку комментариев от старых к новым.
    - Наличие формы комментария для авторизованных пользователей.
    - Отсутствие формы комментария для анонимных пользователей.
    """

    def test_comments_order(self, client, detail_url, comments):
        """
        Проверяет, что комментарии отсортированы от старых к новым.

        Фикстура comments создаёт 10 комментариев с разными датами.
        На странице они должны идти от старых к новым.

        Аргументы:
            client: тестовый клиент
            detail_url: фикстура с URL страницы новости
            comments: фикстура с 10 комментариями
        """
        # Выполняем GET-запрос к странице новости
        response = client.get(detail_url)
        # Получаем новость из контекста
        news = response.context['news']
        # Получаем все комментарии к новости
        all_comments = news.comment_set.all()
        # Собираем временные метки комментариев
        all_timestamps = [comment.created for comment in all_comments]
        # Сортируем временные метки (по возрастанию — от старых к новым)
        sorted_timestamps = sorted(all_timestamps)
        # Проверяем, что порядок правильный
        assert all_timestamps == sorted_timestamps

    def test_anonymous_client_has_no_form(self, client, detail_url):
        """
        Проверяет, что анонимный пользователь не видит форму комментария.

        Форма комментария должна отображаться только для
        авторизованных пользователей.

        Аргументы:
            client: тестовый клиент (анонимный)
            detail_url: фикстура с URL страницы новости
        """
        # Выполняем GET-запрос от анонимного пользователя
        response = client.get(detail_url)
        # Проверяем, что формы нет в контексте
        assert 'form' not in response.context

    def test_authorized_client_has_form(self, client, detail_url, author):
        """
        Проверяет, что авторизованный пользователь видит форму комментария.

        Форма должна быть правильного типа (CommentForm).

        Аргументы:
            client: тестовый клиент
            detail_url: фикстура с URL страницы новости
            author: фикстура с автором
        """
        # Авторизуем пользователя
        client.force_login(author)
        # Выполняем GET-запрос
        response = client.get(detail_url)
        # Проверяем, что форма присутствует в контексте
        assert 'form' in response.context
        # Проверяем, что форма правильного типа
        assert isinstance(response.context['form'], CommentForm)