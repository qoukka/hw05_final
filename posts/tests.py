from django.test import TestCase
from django.test import Client
from django.core import mail
from django.contrib.auth.models import User
from .models import Post, Group, Follow, Comment
from django.urls import reverse
from django.core.cache import cache



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
        self.image = "media/posts/test.png"		
        self.text = "media/posts/test.txt"
        


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

    def response_image(self, file):		
        with open(file,'rb') as img:		
            self.authorized_client.post(reverse("new_post"), data={		
                "text": 'Text',		
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

    def check_post_equal(self, link, text):
        response = self.authorized_client.get(link)
        paginator = response.context.get('paginator')
        if paginator is not None:
            self.assertEqual(paginator.count, 1)
            post = response.context['page'][0]
        else:
            post = response.context['post']
        self.assertEqual(post.text, text)
        self.assertEqual(post.author, self.user)
        self.assertEqual(post.group, self.group)

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
            self.check_post_equal(link, self.text)

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
            self.check_post_equal(link, self.text_edited)

    def test_image_tag_post(self):
        self.response_image(self.image)
        self.post_checks()
        self.urls_image()
        response = self.authorized_client.get(self.urlslist_image[1])
        self.assertContains(response, self.tag)

    def test_image_tag_other(self):
        self.response_image(self.image)
        self.post_checks()
        self.urls_image()
        for link in self.urlslist_image:
            response = self.authorized_client.get(link)
            self.assertContains(response, self.tag)

    def test__load_non_image_file(self):
        self.response_image(self.text)
        self.post_checks()
        self.assertIsNone(self.post_check)
		
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
        self.response_auth()
        self.response_auth_another_user()
        self.authorized_client.post(reverse("profile_follow", kwargs={
            'username': self.user2}))
        follow = Follow.objects.filter(user=self.user, author=self.user2).count()
        self.assertNotEqual(follow, 0)
        self.authorized_client.post(reverse("profile_unfollow", kwargs={
            'username': self.user2}))
        follow = Follow.objects.filter(user=self.user, author=self.user2).count()
        self.assertEqual(follow, 0)
