# news/pytest_tests/test_logic.py
"""
Тесты логики работы с комментариями на pytest.

Проверяют:
- Создание комментариев авторизованными пользователями.
- Запрет создания комментариев анонимными пользователями.
- Блокировку запрещённых слов в комментариях.
- Редактирование комментариев только автором.
- Удаление комментариев только автором.
"""
import pytest
from http import HTTPStatus

from news.models import Comment
from news.forms import BAD_WORDS, WARNING


@pytest.mark.django_db
class TestCommentCreation:
    """
    Тестирование создания комментариев.

    Проверяет три сценария:
    1. Анонимный пользователь не может создать комментарий.
    2. Авторизованный пользователь может создать комментарий.
    3. Авторизованный пользователь не может использовать запрещённые слова.
    """

    def test_anonymous_user_cant_create_comment(self, client, detail_url, form_data):
        """
        Проверяет, что анонимный пользователь не может создать комментарий.

        После попытки создания комментарий НЕ появляется в базе данных.

        Аргументы:
            client: тестовый клиент (анонимный)
            detail_url: фикстура с URL страницы новости
            form_data: фикстура с данными формы
        """
        # Отправляем POST-запрос от анонимного пользователя
        client.post(detail_url, data=form_data)
        # Проверяем, что комментарий НЕ создался
        assert Comment.objects.count() == 0

    def test_user_can_create_comment(
            self, client, author, detail_url, form_data, news
    ):
        """
        Проверяет, что авторизованный пользователь может создать комментарий.

        После успешного создания:
        - Происходит редирект на страницу новости с якорем #comments
        - В базе появляется 1 комментарий
        - Все поля комментария заполнены правильно

        Аргументы:
            client: тестовый клиент
            author: фикстура с автором
            detail_url: фикстура с URL страницы новости
            form_data: фикстура с данными формы
            news: фикстура с новостью
        """
        # Авторизуем пользователя
        client.force_login(author)
        # Отправляем POST-запрос на создание комментария
        response = client.post(detail_url, data=form_data)

        # Проверяем, что произошёл редирект (302)
        assert response.status_code == HTTPStatus.FOUND
        # Проверяем, что редирект ведёт на страницу с якорем #comments
        assert response.url == f'{detail_url}#comments'

        # Проверяем, что комментарий появился в базе (1 запись)
        assert Comment.objects.count() == 1

        # Получаем созданный комментарий
        comment = Comment.objects.get()
        # Проверяем, что текст совпадает
        assert comment.text == form_data['text']
        # Проверяем, что комментарий привязан к правильной новости
        assert comment.news == news
        # Проверяем, что автор комментария — текущий пользователь
        assert comment.author == author

    def test_user_cant_use_bad_words(self, client, author, detail_url):
        """
        Проверяет, что пользователь не может использовать запрещённые слова.

        При использовании запрещённого слова:
        - Форма возвращает ошибку с текстом WARNING
        - Комментарий НЕ создаётся

        Аргументы:
            client: тестовый клиент
            author: фикстура с автором
            detail_url: фикстура с URL страницы новости
        """
        # Авторизуем пользователя
        client.force_login(author)
        # Формируем данные с запрещённым словом (первое из списка BAD_WORDS)
        bad_words_data = {'text': f'Какой-то текст, {BAD_WORDS[0]}, еще текст'}
        # Отправляем POST-запрос
        response = client.post(detail_url, data=bad_words_data)

        # Получаем форму из контекста ответа
        form = response.context['form']
        # Проверяем, что в поле 'text' есть ошибка с текстом WARNING
        assert form.errors['text'] == [WARNING]
        # Проверяем, что комментарий НЕ создался
        assert Comment.objects.count() == 0


@pytest.mark.django_db
class TestCommentEditDelete:
    """
    Тестирование редактирования и удаления комментариев.

    Проверяет четыре сценария:
    1. Автор может удалить свой комментарий.
    2. Читатель не может удалить чужой комментарий.
    3. Автор может редактировать свой комментарий.
    4. Читатель не может редактировать чужой комментарий.
    """

    def test_author_can_delete_comment(self, client, author, delete_url, comment):
        """
        Проверяет, что автор может удалить свой комментарий.

        После успешного удаления:
        - Происходит редирект (302)
        - Комментарий исчезает из базы (0 записей)

        Аргументы:
            client: тестовый клиент
            author: фикстура с автором
            delete_url: фикстура с URL удаления комментария
            comment: фикстура с комментарием
        """
        # Авторизуем автора
        client.force_login(author)
        # Отправляем DELETE-запрос на удаление
        response = client.delete(delete_url)

        # Проверяем, что произошёл редирект (302)
        assert response.status_code == HTTPStatus.FOUND
        # Проверяем, что комментарий удалён из базы
        assert Comment.objects.count() == 0

    def test_user_cant_delete_comment_of_another_user(
            self, client, reader, delete_url, comment
    ):
        """
        Проверяет, что пользователь не может удалить чужой комментарий.

        При попытке удаления чужого комментария:
        - Возвращается статус 404 (Not Found)
        - Комментарий остаётся в базе (1 запись)

        Аргументы:
            client: тестовый клиент
            reader: фикстура с читателем
            delete_url: фикстура с URL удаления комментария
            comment: фикстура с комментарием
        """
        # Авторизуем читателя
        client.force_login(reader)
        # Пытаемся удалить чужой комментарий
        response = client.delete(delete_url)

        # Проверяем, что вернулась ошибка 404 (Not Found)
        assert response.status_code == HTTPStatus.NOT_FOUND
        # Проверяем, что комментарий остался в базе
        assert Comment.objects.count() == 1

    def test_author_can_edit_comment(
            self, client, author, edit_url, comment, update_data
    ):
        """
        Проверяет, что автор может редактировать свой комментарий.

        После успешного редактирования:
        - Происходит редирект (302)
        - Текст комментария обновляется

        Аргументы:
            client: тестовый клиент
            author: фикстура с автором
            edit_url: фикстура с URL редактирования комментария
            comment: фикстура с комментарием
            update_data: фикстура с обновлёнными данными
        """
        # Авторизуем автора
        client.force_login(author)
        # Отправляем POST-запрос с обновлёнными данными
        response = client.post(edit_url, data=update_data)

        # Проверяем, что произошёл редирект (302)
        assert response.status_code == HTTPStatus.FOUND

        # Обновляем объект комментария из базы данных
        comment.refresh_from_db()
        # Проверяем, что текст комментария обновился
        assert comment.text == update_data['text']

    def test_user_cant_edit_comment_of_another_user(
            self, client, reader, edit_url, comment
    ):
        """
        Проверяет, что пользователь не может редактировать чужой комментарий.

        При попытке редактирования чужого комментария:
        - Возвращается статус 404 (Not Found)
        - Текст комментария НЕ изменяется

        Аргументы:
            client: тестовый клиент
            reader: фикстура с читателем
            edit_url: фикстура с URL редактирования комментария
            comment: фикстура с комментарием
        """
        # Авторизуем читателя
        client.force_login(reader)
        # Пытаемся отредактировать чужой комментарий
        response = client.post(edit_url, data={'text': 'Новый текст'})

        # Проверяем, что вернулась ошибка 404 (Not Found)
        assert response.status_code == HTTPStatus.NOT_FOUND

        # Обновляем объект комментария из базы данных
        comment.refresh_from_db()
        # Проверяем, что текст НЕ изменился
        assert comment.text == 'Текст комментария'