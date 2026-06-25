# news/tests/test_logic.py
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

# Импортируем из файла с формами список стоп-слов и предупреждение формы.
# Загляните в news/forms.py, разберитесь с их назначением.
from news.forms import BAD_WORDS, WARNING
from news.models import Comment, News

User = get_user_model()


class TestCommentCreation(TestCase):
    # Текст комментария понадобится в нескольких местах кода, 
    # поэтому запишем его в атрибуты класса.
    COMMENT_TEXT = 'Текст комментария'

    @classmethod
    def setUpTestData(cls):
        """."""
        cls.news = News.objects.create(title='Заголовок', text='Текст')

        # Адрес страницы с новостью.
        cls.url = reverse('news:detail', args=(cls.news.id,))

        # Создаём тестового пользователя.
        cls.user = User.objects.create(username='Мимо Крокодил')

        # Создаём тестовый клиент для отправки запросов.
        cls.auth_client = Client()

        # Принудительно авторизуем пользователя в клиенте.
        # self.auth_client - авторизованный, т.к. залогинился
        cls.auth_client.force_login(cls.user)

        # Готовим данные для формы - данные для POST-запроса при создании
        # комментария. Тесты будут использовать эти данные. Создаем словарь,
        # назовем переменную form_data, которая будет в дальнейшем
        # использоваться в тестах
        cls.form_data = {'text': cls.COMMENT_TEXT}

    def test_anonymous_user_cant_create_comment(self):
        """."""
        # Совершаем запрос от анонимного клиента, в POST-запросе отправляем
        # предварительно подготовленные данные формы с текстом комментария.
        self.client.post(self.url, data=self.form_data)

        # Считаем количество комментариев.
        comments_count = Comment.objects.count()

        # Ожидаем, что комментариев в базе нет - сравниваем с нулём.
        self.assertEqual(comments_count, 0)

    def test_user_can_create_comment(self):
        """."""
        # Совершаем запрос через авторизованный клиент - вернет HttpResponse.
        response = self.auth_client.post(self.url, data=self.form_data)

        # Проверяем, что редирект привёл к разделу с комментами.
        self.assertRedirects(response, f'{self.url}#comments')

        # Считаем количество комментариев.
        comments_count = Comment.objects.count()

        # Убеждаемся, что есть один комментарий.
        self.assertEqual(comments_count, 1)

        # Получаем объект комментария из базы.
        comment = Comment.objects.get()

        # Проверяем, что все атрибуты комментария совпадают с ожидаемыми.
        self.assertEqual(comment.text, self.COMMENT_TEXT)
        self.assertEqual(comment.news, self.news)
        self.assertEqual(comment.author, self.user)


    def test_user_cant_use_bad_words(self):
        """Проверка блокировки стоп-слов (запрещенных слов)."""
        # Формируем данные для отправки формы; текст включает
        # первое слово из списка стоп-слов.
        bad_words_data = {'text': f'Какой-то текст, {BAD_WORDS[0]}, еще текст'}

        # Отправляем POST-запрос c запрещенным словом через авторизованный
        # клиент.
        response = self.auth_client.post(self.url, data=bad_words_data)

        # Забираем форму из контекста (она содержит ошибки)
        form = response.context['form']

        # Проверяем, есть ли в ответе в поле text есть ошибка формы
        # с текстом WARNING.
        self.assertFormError(
            form=form,  # ← форма с ошибками
            field='text',  # ← поле, в котором ошибка
            errors=WARNING  # ← ожидаемый текст ошибки
        )
        # Дополнительно убедимся, что комментарий не был создан.
        comments_count = Comment.objects.count()
        self.assertEqual(comments_count, 0)


class TestCommentEditDelete(TestCase):
    """Проверка удаления и редактирования комментария.

    Проверяем:
    - Автор может редактировать свой комментарий
    - Автор может удалять свой комментарий
    - Читатель НЕ может редактировать чужой комментарий
    - Читатель НЕ может удалять чужой комментарий
    - После редактирования текст комментария обновляется
    - После удаления комментарий исчезает из базы

    Тексты для комментариев не нужно дополнительно создавать
    (в отличие от объектов в БД), им не нужны ссылки на self или cls,
    поэтому их можно перечислить просто в атрибутах класса.
    """

    # Тексты для комментариев не нужно дополнительно создавать (в отличие от
    # объектов в БД), им не нужны ссылки на self или cls, поэтому их можно
    # перечислить просто в атрибутах класса.
    COMMENT_TEXT = 'Текст комментария'
    NEW_COMMENT_TEXT = 'Обновлённый комментарий'

    @classmethod
    def setUpTestData(cls):
        """Создаём тестовые данные: новость, двух users и комментарий."""
        # Создаём новость в БД.
        cls.news = News.objects.create(title='Заголовок', text='Текст')

        # Формируем адрес блока с комментариями, который понадобится
        # для тестов: 1) Адрес новости, 2) Адрес блока с комментариями.
        # Сохраняем URL для редиректа после создания/редактирования
        news_url = reverse('news:detail', args=(cls.news.id,))
        cls.url_to_comments = news_url + '#comments'

        # Создаём пользователя - автора комментария.
        cls.author = User.objects.create(username='Автор комментария')

        # Создаём клиент для пользователя-автора.
        cls.author_client = Client()

        # "Логиним" пользователя в клиенте.
        cls.author_client.force_login(cls.author)

        # Делаем всё то же самое для пользователя-читателя.
        cls.reader = User.objects.create(username='Читатель')
        cls.reader_client = Client()
        cls.reader_client.force_login(cls.reader)

        # Создаём объект комментария (от имени автора).
        cls.comment = Comment.objects.create(
            news=cls.news,
            author=cls.author,
            text=cls.COMMENT_TEXT
        )
        # Сохраняем URL для редактирования комментария.
        cls.edit_url = reverse('news:edit', args=(cls.comment.id,))

        # сохраняем URL для удаления комментария.
        cls.delete_url = reverse('news:delete', args=(cls.comment.id,))

        # Формируем данные для POST-запроса по обновлению комментария.
        cls.form_data = {'text': cls.NEW_COMMENT_TEXT}

    def test_author_can_delete_comment(self):
        """Проверка: может ли автор удалить свой комментарий."""
        # Проверка утверждения «в БД содержится один комментарий»
        # comments_count = Comment.objects.count()
        # self.assertEqual(comments_count, 1)

        # От имени автора комментария отправляем DELETE-запрос на удаление.
        response = self.author_client.delete(self.delete_url)

        # Проверяем, что редирект привёл к разделу с комментариями.
        self.assertRedirects(response, self.url_to_comments)

        # Заодно проверим статус-коды ответов.
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

        # Считаем количество комментариев в системе.
        comments_count = Comment.objects.count()

        # Ожидаем ноль комментариев в системе.
        self.assertEqual(comments_count, 0)

    def test_user_cant_delete_comment_of_another_user(self):
        """Проверка: пользователь не может удалить чужой комментарий."""
        # Выполняем запрос на удаление от пользователя-читателя.
        response = self.reader_client.delete(self.delete_url)

        # Проверяем, что вернулась 404 ошибка.
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # Убедимся, что комментарий по-прежнему на месте.
        # 1. Получаем количество комментариев в базе данных.
        comments_count = Comment.objects.count()

        # 2. Проверяем, что в БД остался один коментарий
        self.assertEqual(comments_count, 1)

    def test_author_can_edit_comment(self):
        """Проверка: редактировать комментарии может только их автор."""
        # Выполняем запрос на редактирование от имени автора комментария.
        response = self.author_client.post(self.edit_url, data=self.form_data)

        # Проверяем, что сработал редирект.
        self.assertRedirects(response, self.url_to_comments)

        # Обновляем объект комментария.
        self.comment.refresh_from_db()

        # Проверяем, что текст комментария соответствует обновленному.
        self.assertEqual(self.comment.text, self.NEW_COMMENT_TEXT)

    def test_user_cant_edit_comment_of_another_user(self):
        """Проверка:.

        Редактирование комментария недоступно для другого пользователя.
        """
        # Выполняем запрос на редактирование от имени другого пользователя.
        response = self.reader_client.post(self.edit_url, data=self.form_data)

        # Проверяем, что вернулась 404 ошибка.
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # Обновляем объект комментария.
        self.comment.refresh_from_db()

        # Проверяем, что текст остался тем же, что и был.
        self.assertEqual(self.comment.text, self.COMMENT_TEXT)
