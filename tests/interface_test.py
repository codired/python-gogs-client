import base64
import json
import unittest

import responses
from future.moves.urllib.parse import parse_qs
from builtins import bytes

import gogs_client
import gogs_client.http_utils as http_utils


class GogsClientInterfaceTest(unittest.TestCase):

    def setUp(self):
        self.api_endpoint = "https://www.example.com/api/v1/"
        self.base_url = "https://www.example.com/"
        self.client = gogs_client.GogsApi(self.base_url)
        self.repo_json_str = """{
                "id": 27,
                "owner": {
                    "id": 1,
                    "username": "unknwon",
                    "full_name": "",
                    "email": "u@gogs.io",
                    "avatar_url": "/avatars/1"
                  },
                  "full_name": "unknwon/Hello-World",
                  "private": false,
                  "fork": false,
                  "html_url": "http://localhost:3000/unknwon/Hello-World",
                  "clone_url": "http://localhost:3000/unknwon/hello-world.git",
                  "ssh_url": "jiahuachen@localhost:unknwon/hello-world.git",
                  "permissions": {
                    "admin": true,
                    "push": true,
                    "pull": true
                  }
                }"""
        self.user_json_str = """{
                  "id": 1,
                  "username": "unknwon",
                  "full_name": "",
                  "email": "u@gogs.io",
                  "avatar_url": "/avatars/1"
                }"""
        self.token = gogs_client.GogsToken("mytoken")
        self.username_password = gogs_client.GogsUsernamePassword(
            "auth_username", "password")
        self.expected_repo = gogs_client.GogsRepo.from_json(json.loads(self.repo_json_str))
        self.expected_user = gogs_client.GogsUser.from_json(json.loads(self.user_json_str))

    @responses.activate
    def test_create_repo1(self):
        uri = self.path("/user/repos")
        responses.add(responses.POST, uri, body=self.repo_json_str)
        repo = self.client.create_repo(self.token, "AGreatRepo")
        self.assert_repos_equal(repo, self.expected_repo)
        self.assertEqual(len(responses.calls), 1)
        call = responses.calls[0]
        self.assertEqual(call.request.url, self.path_with_token(uri))

    @responses.activate
    def test_repo_exists1(self):
        uri1 = self.path("/repos/username/repo1")
        uri2 = self.path("/repos/username/repo2")
        responses.add(responses.GET, uri1, body=self.repo_json_str, status=200)
        responses.add(responses.GET, uri2, status=404)
        self.assertTrue(self.client.repo_exists(self.token, "username", "repo1"))
        self.assertFalse(self.client.repo_exists(self.token, "username", "repo2"))
        self.assertEqual(len(responses.calls), 2)
        first_call = responses.calls[0]
        self.assertEqual(first_call.request.url, self.path_with_token(uri1))
        last_call = responses.calls[1]
        self.assertEqual(last_call.request.url, self.path_with_token(uri2))

    @responses.activate
    def test_get_repo1(self):
        uri1 = self.path("/repos/username/repo1")
        uri2 = self.path("/repos/username/repo2")
        responses.add(responses.GET, uri1, body=self.repo_json_str, status=200)
        responses.add(responses.GET, uri2, status=404)
        repo = self.client.get_repo(self.token, "username", "repo1")
        self.assert_repos_equal(repo, self.expected_repo)
        self.assertRaises(gogs_client.GogsApi.ApiFailure, self.client.get_repo,
                          self.token, "username", "repo2")
        self.assertEqual(len(responses.calls), 2)
        first_call = responses.calls[0]
        self.assertEqual(first_call.request.url, self.path_with_token(uri1))
        last_call = responses.calls[1]
        self.assertEqual(last_call.request.url, self.path_with_token(uri2))

    @responses.activate
    def test_delete_repo1(self):
        uri1 = self.path("/repos/username/repo1")
        uri2 = self.path("/repos/otherusername/repo2")
        responses.add(responses.DELETE, uri1, status=204)
        responses.add(responses.DELETE, uri2, status=401)
        self.client.delete_repo(self.token, "username", "repo1")
        self.assertRaises(gogs_client.GogsApi.ApiFailure, self.client.delete_repo,
                          self.token, "otherusername", "repo2")
        self.assertEqual(len(responses.calls), 2)
        first_call = responses.calls[0]
        self.assertEqual(first_call.request.url, self.path_with_token(uri1))
        last_call = responses.calls[1]
        self.assertEqual(last_call.request.url, self.path_with_token(uri2))

    @responses.activate
    def test_create_user1(self):
        uri = self.path("/admin/users")
        responses.add(responses.POST, uri, body=self.user_json_str, status=201)
        user = self.client.create_user(self.token, login_name="loginname",
                                       username="username", email="user@example.com",
                                       password="password")
        self.assert_users_equals(user, self.expected_user)
        self.assertEqual(len(responses.calls), 1)
        call = responses.calls[0]
        self.assertEqual(call.request.url, self.path_with_token(uri))

    @responses.activate
    def test_user_exists1(self):
        uri1 = self.path("/users/username1")
        uri2 = self.path("/users/username2")
        responses.add(responses.GET, uri1, body=self.user_json_str, status=200)
        responses.add(responses.GET, uri2, status=404)
        self.assertTrue(self.client.user_exists("username1"))
        self.assertFalse(self.client.user_exists("username2"))
        self.assertEqual(len(responses.calls), 2)
        first_call = responses.calls[0]
        self.assertEqual(first_call.request.url, uri1)
        last_call = responses.calls[1]
        self.assertEqual(last_call.request.url, uri2)

    @responses.activate
    def test_search_users(self):
        uri = self.path("/users/search")

        def callback(request):
            url = request.url
            index = url.find("?")
            self.assertTrue(index >= 0)  # assert a ? was actually found
            self.assertEqual(url[:index], uri)
            data = self.data_of_query(url[index + 1:])
            self.assertEqual(data["q"], "keyword")
            self.assertEqual(int(data["limit"]), 4)
            return 200, {}, "{\"data\": [%s], \"ok\": true}" % self.user_json_str
        responses.add_callback(responses.GET, uri, callback=callback)
        users = self.client.search_users("keyword", limit=4)
        self.assertEqual(len(users), 1)
        self.assert_users_equals(users[0], self.expected_user)

    @responses.activate
    def test_get_user1(self):
        uri1 = self.path("/users/username1")
        uri2 = self.path("/users/username2")
        responses.add(responses.GET, uri1, body=self.user_json_str, status=200)
        responses.add(responses.GET, uri2, status=404)
        user = self.client.get_user(None, "username1")
        self.assert_users_equals(user, self.expected_user)
        self.assertRaises(gogs_client.GogsApi.ApiFailure, self.client.get_user,
                          None, "username2")
        self.assertEqual(len(responses.calls), 2)
        first_call = responses.calls[0]
        self.assertEqual(first_call.request.url, uri1)
        last_call = responses.calls[1]
        self.assertEqual(last_call.request.url, uri2)

    @responses.activate
    def test_update_user1(self):
        update = gogs_client.GogsUserUpdate.Builder("loginname", "user@example.com")\
            .set_full_name("Example User")\
            .set_password("Password")\
            .set_website("mywebsite.net")\
            .build()

        def callback(request):
            data = self.data_of_query(request.body)
            self.assertEqual(data["login_name"], "loginname")
            self.assertEqual(data["full_name"], "Example User")
            self.assertEqual(data["email"], "user@example.com")
            self.assertEqual(data["password"], "Password")
            self.assertEqual(data["website"], "mywebsite.net")
            return 200, {}, self.user_json_str
        uri = self.path("/admin/users/username")
        responses.add_callback(responses.PATCH, uri, callback=callback)
        user = self.client.update_user(self.token, "username", update)
        self.assert_users_equals(user, self.expected_user)

    @responses.activate
    def test_delete_user1(self):
        uri1 = self.path("/admin/users/username1")
        uri2 = self.path("/admin/users/username2")
        responses.add(responses.DELETE, uri1, status=204)
        responses.add(responses.DELETE, uri2, status=401)
        self.client.delete_user(self.username_password, "username1")
        self.assertRaises(gogs_client.GogsApi.ApiFailure, self.client.delete_user,
                          self.username_password, "username2")
        self.assertEqual(len(responses.calls), 2)
        first_call = responses.calls[0]
        self.assertEqual(first_call.request.url, uri1)
        self.check_for_basic_auth(first_call.request)
        last_call = responses.calls[1]
        self.assertEqual(last_call.request.url, uri2)
        self.check_for_basic_auth(last_call.request)

    # helper methods

    @staticmethod
    def data_of_query(query):
        return {k: v[0] for (k, v) in parse_qs(query).items()}

    def path(self, relative):
        return http_utils.append_url(self.api_endpoint, relative)

    def path_with_token(self, path):
        return "{p}?token={t}".format(p=path, t=self.token.token)

    def check_for_basic_auth(self, request):
        auth = "{u}:{p}".format(u=self.username_password.username,
                                p=self.username_password.password)
        b64 = base64.b64encode(auth.encode()).decode()
        self.assertEqual(request.headers["Authorization"], "Basic {}".format(b64))

    def assert_repos_equal(self, repo, expected):
        self.assertEqual(repo.repo_id, expected.repo_id)
        self.assert_users_equals(repo.owner, expected.owner)
        self.assertEqual(repo.full_name, expected.full_name)
        self.assertEqual(repo.private, expected.private)
        self.assertEqual(repo.fork, expected.fork)
        self.assertEqual(repo.urls.html_url, expected.urls.html_url)
        self.assertEqual(repo.urls.clone_url, expected.urls.clone_url)
        self.assertEqual(repo.urls.ssh_url, expected.urls.ssh_url)
        self.assertEqual(repo.permissions.admin, expected.permissions.admin)
        self.assertEqual(repo.permissions.push, expected.permissions.push)
        self.assertEqual(repo.permissions.pull, expected.permissions.pull)

    def assert_users_equals(self, user, expected):
        self.assertEqual(user.user_id, expected.user_id)
        self.assertEqual(user.username, expected.username)
        self.assertEqual(user.full_name, expected.full_name)
        self.assertEqual(user.email, expected.email)
        self.assertEqual(user.avatar_url, expected.avatar_url)


if __name__ == "__main__":
    unittest.main()