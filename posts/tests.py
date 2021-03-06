from django.test import TestCase
from django.test import Client
from django.core import mail
from django.contrib.auth.models import User
from .models import Post, Group, Follow, Comment
from django.urls import reverse
from django.core.cache import cache
import mock
from django.core.files import File
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import SimpleUploadedFile


class PostsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alena")
        self.user2 = User.objects.create_user(username="vasya")
        self.authorized_client = Client()
        self.authorized_client2 = Client()
        self.unauthorized_client = Client()
        self.group = Group.objects.create(
            title="Тестовая группа",
            slug="test_group"
            )
        self.authorized_client.force_login(self.user)
        self.authorized_client2.force_login(self.user2)
        self.text_edited = "Редактированный тестовый пост"
        self.text = "Ку-ку"
        self.tag = "<img"			


    def response_auth(self):
        self.response_auth = self.authorized_client.post(reverse("new_post"), data={
            'text': self.text, 
            'group': self.group.id,
            'author': self.authorized_client
            }, 
            follow=True
        )
    
    def response_auth_another_user(self):
        self.response_auth = self.authorized_client2.post(reverse("new_post"), data={
            'text': self.text, 
            'group': self.group.id,
            'author': self.authorized_client2
            }, 
            follow=True
        )

    def response_unauth(self):
        self.response_unauth = self.unauthorized_client.post(reverse("new_post"), data={
            'text': self.text, 
            'group': self.group.id,
            'author': self.authorized_client
            }, 
            follow=True
        )

    def response_image(self):		
        file = BytesIO()
        image = Image.new('RGBA',
                      size=(960, 339),
                      color=(0, 5, 0)
                      )
        image.save(file, 'png')
        file.name = 'test.png'
        file.seek(0)
        img = SimpleUploadedFile(
            file.name,
            file.read(),
            content_type='image/png'
            )
        self.authorized_client.post(reverse("new_post"), data={		
                "text": self.text,		
                "author": self.authorized_client,		
                "group": self.group.id,		
                "image": img,		
                }, 		
            follow=True		
            )

    def post_checks(self):
        self.post_check = Post.objects.first()
        self.post_count = Post.objects.count()
        
    def urls(self):
        self.urlslist = [
            reverse("index"),
            reverse("profile", kwargs={"username": self.post_check.author.username}),
            reverse("post", kwargs={
                    "username": self.post_check.author.username,
                    "post_id": self.post_check.id,})
        ]
	
    def urls_image(self):		
        self.urlslist_image = [		
        reverse("profile", kwargs={"username": self.post_check.author.username}),		
        reverse("post", kwargs={		
                "username": self.post_check.author.username,		
                "post_id": self.post_check.id,}),		
        reverse("group_posts", kwargs={		
                "slug": self.group.slug})		
        ]

    def check_post_equal(self, link, text, user):
        response = self.authorized_client.get(link)
        paginator = response.context.get('paginator')
        if paginator is not None:
            self.assertEqual(paginator.count, 1)
            post = response.context['page'][0]
        else:
            post = response.context['post']
        self.assertEqual(post.text, text)
        self.assertEqual(post.author, user)
        self.assertEqual(post.group, self.group)

    def check_post_not_equal(self, link, text):
        response = self.authorized_client.get(link)
        paginator = response.context.get('paginator')
        self.assertEqual(paginator.count, 0)

    def test_profile(self):
        response = self.authorized_client.get("/alena/")
        self.assertEqual(response.status_code, 200, msg="Страница не создается")

    def test_auth_post(self):
        self.response_auth()
        self.post_checks()
        self.assertEqual(self.response_auth.status_code, 200, msg="Пост не опубликован")
        self.assertEqual(self.post_count, 1)
        self.assertEqual(self.post_check.text, self.text)
        self.assertEqual(self.post_check.group.slug, "test_group")
        self.assertEqual(self.post_check.author.username, "alena")

    def test_no_auth_post(self):
        self.response_unauth()
        self.post_checks()
        login = reverse("login") 
        new = reverse("new_post") 
        self.assertRedirects(self.response_unauth, f"{login}?next={new}")

    def test_new_post(self):
        self.response_auth()
        self.post_checks()
        self.urls()
        for link in self.urlslist:
            cache.clear()
            self.check_post_equal(link, self.text, self.user)

    def test_auth_edit_post(self):
        self.response_auth()
        self.post_checks()
        self.urls()
        response = self.authorized_client.post(reverse("post_edit", kwargs={
                "username": self.post_check.author.username, 
                "post_id": self.post_check.id}), 
            data={
                "username": self.post_check.author.username,
                "post_id": self.post_check.id,
                'group': self.group.id,
                "text": self.text_edited,
                }, 
            follow=True
            )
        post_check = Post.objects.first()
        self.assertEqual(post_check.text, self.text_edited)
        for link in self.urlslist:
            cache.clear()
            self.check_post_equal(link, self.text_edited, self.user)

    def test_image_tag_post(self):
        self.response_image()
        self.post_checks()
        self.urls_image()
        cache.clear()
        response = self.authorized_client.get(self.urlslist_image[1])
        self.assertContains(response, self.tag)

    def test_image_tag_other(self):
        self.response_image()
        self.post_checks()
        self.urls_image()
        for link in self.urlslist_image:
            cache.clear()
            response = self.authorized_client.get(link)
            self.assertContains(response, self.tag)

    def test__load_non_image_file(self):
        file_mock = mock.MagicMock(spec=File, name='test.txt')
        response = self.authorized_client.post(reverse('new_post'),
                                             {'text': self.text,
                                              'group': self.group.id,
                                              'image': file_mock},
                                             follow=True)
        cache.clear()
        self.assertFormError(response,form='form', field='image', errors='Загрузите правильное изображение. Файл, который вы загрузили, поврежден или не является изображением.')
		
    def test_cache_index(self):
        self.authorized_client.post(
            reverse("new_post"),
            data={
            "text": "Джонни Кэш",
            "group": self.group.id
            },
            follow=True
        )
        response = self.authorized_client.get(reverse("index"))
        self.assertNotContains(response, "Джонни Кэш")

    def test_subscribe(self):
        self.authorized_client.post(reverse("profile_follow", kwargs={
            'username': self.user2}))
        follow = Follow.objects.filter(user=self.user, author=self.user2).count()
        self.assertNotEqual(follow, 0)

    def test_unsubscribe(self):
        self.authorized_client.post(reverse("profile_follow", kwargs={
            'username': self.user2}))
        self.authorized_client.post(reverse("profile_unfollow", kwargs={
            'username': self.user2}))
        follow = Follow.objects.filter(user=self.user, author=self.user2).count()
        self.assertEqual(follow, 0)
    
    def comments(self, auth):
        if auth == "authorized":
            self.authorized_client.post(reverse("add_comment", kwargs={
            'username': self.user,
            'post_id': self.post_check.id
            }), data={
            'text': self.text,
            'post': self.post_check.id,
            'author': self.user.id})
        else:
            self.unauthorized_client.post(reverse("add_comment", kwargs={
            'username': self.user,
            'post_id': self.post_check.id
            }), data={
            'text': self.text,
            'post': self.post_check.id,
            'author': self.user.id})
        self.comment = self.post_check.comments.select_related('author').first()

    def test_check_comments(self):
        self.response_auth()
        self.post_checks()
        self.comments(auth="authorized")
        self.assertEqual(Comment.objects.count(), 1)
        self.assertEqual(self.comment.text, self.text)
        self.assertEqual(self.comment.post, self.post_check)
        self.assertEqual(self.comment.author, self.user)

    def test_check_comments_no_auth(self):
        self.response_auth()
        self.post_checks()
        self.comments(auth="unauthorized")
        self.assertEqual(Comment.objects.count(), 0)

    def test_index_follow(self):
        self.response_auth_another_user()
        self.authorized_client.post(reverse("profile_follow", kwargs={
            'username': self.user2}))
        self.check_post_equal(reverse("follow_index"), self.text, self.user2)

    def test_index_unfollow(self):
        self.response_auth_another_user()
        self.check_post_not_equal(reverse("follow_index"), self.text)