# news/pytest_tests/conftest.py
"""
Общие фикстуры для всех тестов проекта ya_news на pytest.

Содержит фикстуры для создания:
- Пользователей (автор, читатель)
- Новостей
- Комментариев
- URL-адресов
- Тестовых данных (формы, тексты)
"""
import pytest
from datetime import datetime, timedelta
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from news.models import Comment, News


# === ФИКСТУРЫ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ===
@pytest.fixture
def author(django_user_model):
    """
    Фикстура создаёт пользователя-автора.

    Используется в тестах, где нужен владелец комментария или новости.
    Возвращает: объект User с username='Я автор'.
    """
    return django_user_model.objects.create(username='Я автор')


@pytest.fixture
def reader(django_user_model):
    """
    Фикстура создаёт пользователя-читателя.

    Используется в тестах, где нужно проверить, что чужой контент недоступен.
    Возвращает: объект User с username='Я читатель'.
    """
    return django_user_model.objects.create(username='Я читатель')


# === ФИКСТУРЫ ДЛЯ НОВОСТЕЙ И КОММЕНТАРИЕВ ===
@pytest.fixture
def news():
    """
    Фикстура создаёт тестовую новость.

    Используется в тестах, где нужна новость для привязки комментариев.
    Возвращает: объект News с заголовком 'Заголовок' и текстом 'Текст'.
    """
    return News.objects.create(
        title='Заголовок',
        text='Текст'
    )


@pytest.fixture
def comment(author, news):
    """
    Фикстура создаёт комментарий от имени автора к новости.

    Используется в тестах на редактирование и удаление комментариев.
    Возвращает: объект Comment с текстом 'Текст комментария', привязанный
    к новости и автору.
    """
    return Comment.objects.create(
        news=news,
        author=author,
        text='Текст комментария'
    )


@pytest.fixture
def comment_text():
    """
    Фикстура возвращает текст комментария для создания.

    Используется в тестах на создание комментариев.
    Возвращает: строку с текстом комментария.
    """
    return 'Текст комментария'


@pytest.fixture
def new_comment_text():
    """
    Фикстура возвращает обновлённый текст комментария.

    Используется в тестах на редактирование.
    Возвращает: строку с обновлённым текстом - 'Обновлённый комментарий'.
    """
    return 'Обновлённый комментарий'


@pytest.fixture
def form_data(comment_text):
    """
    Фикстура возвращает данные формы для создания комментария.

    Используется в POST-запросах при создании комментария.
    Возвращает: словарь с данными формы {'text': 'Текст комментария'}.
    """
    return {'text': comment_text}


@pytest.fixture
def update_data(new_comment_text):
    """
    Фикстура возвращает данные формы для обновления комментария.

    Используется в POST-запросах при редактировании комментария.
    Возвращает: словарь с обновлёнными данными формы.
    """
    return {'text': new_comment_text}


# === ФИКСТУРЫ ДЛЯ URL-АДРЕСОВ ===
@pytest.fixture
def detail_url(news):
    """
    Фикстура возвращает URL страницы новости.

    Используется в тестах для проверки страницы деталей новости.
    Возвращает: строку с URL-адресом.
    """
    return reverse('news:detail', args=(news.id,))


@pytest.fixture
def edit_url(comment):
    """
    Фикстура возвращает URL редактирования комментария.

    Используется в тестах на редактирование.
    Возвращает: строку с URL-адресом.
    """
    return reverse('news:edit', args=(comment.id,))


@pytest.fixture
def delete_url(comment):
    """
    Фикстура возвращает URL удаления комментария.

    Используется в тестах на удаление.
    Возвращает: строку с URL-адресом.
    """
    return reverse('news:delete', args=(comment.id,))


# === ФИКСТУРЫ ДЛЯ НАБОРОВ ДАННЫХ ===
@pytest.fixture
def many_news():
    """
    Фикстура создаёт 11 новостей для проверки пагинации.

    Новости создаются с убывающими датами (от сегодня до 10 дней назад).
    Это позволяет проверить сортировку и количество на странице.
    Возвращает: список объектов News.
    """
    # Получаем текущую дату как точку отсчёта
    today = datetime.today()

    # Создаём список новостей
    news_list = []
    for index in range(settings.NEWS_COUNT_ON_HOME_PAGE + 1):
        # Для каждой новости дата сдвигается на index дней назад
        news = News(
            title=f'Новость {index}',
            text='Просто текст.',
            date=today - timedelta(days=index)
        )
        news_list.append(news)

    # Одним запросом создаём все новости в БД
    return News.objects.bulk_create(news_list)


@pytest.fixture
def comments(author, news):
    """
    Фикстура создаёт 10 комментариев с разными датами.

    Каждый комментарий имеет уникальную дату (от текущей + index дней).
    Это позволяет проверить сортировку комментариев от старых к новым.
    Возвращает: список объектов Comment.
    """
    # Получаем текущее время с учётом часового пояса
    now = timezone.now()

    # Создаём список комментариев
    comments_list = []
    for index in range(10):
        comment = Comment.objects.create(
            news=news,
            author=author,
            text=f'Текст {index}'
        )
        # Устанавливаем разную дату для каждого комментария
        comment.created = now + timedelta(days=index)
        comment.save()
        comments_list.append(comment)
    return comments_list