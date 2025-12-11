from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase


class UsersManagersTests(TestCase):

    def test_create_user(self):
        User = get_user_model()
        user = User.objects.create_user(email="normal@user.com", password="foo")
        self.assertEqual(user.email, "normal@user.com")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        try:
            # username is None for the AbstractUser option
            # username does not exist for the AbstractBaseUser option
            self.assertIsNone(user.username)
        except AttributeError:
            pass
        with self.assertRaises(TypeError):
            User.objects.create_user()
        with self.assertRaises(TypeError):
            User.objects.create_user(email="")
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="foo")

    def test_create_superuser(self):
        User = get_user_model()
        admin_user = User.objects.create_superuser(email="super@user.com", password="foo")
        self.assertEqual(admin_user.email, "super@user.com")
        self.assertTrue(admin_user.is_active)
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)
        try:
            # username is None for the AbstractUser option
            # username does not exist for the AbstractBaseUser option
            self.assertIsNone(admin_user.username)
        except AttributeError:
            pass
        with self.assertRaises(ValueError):
            User.objects.create_superuser(
                email="super@user.com", password="foo", is_superuser=False)

    def test_email_normalization(self):
        """Emails should be normalized by the manager (domain lowercased)."""
        User = get_user_model()
        user = User.objects.create_user(email="Test@EXAMPLE.COM", password="foo")
        # BaseUserManager.normalize_email lowercases the domain part
        self.assertEqual(user.email, "Test@example.com")

    def test_duplicate_email_raises_integrity_error(self):
        """Creating two users with same email should raise IntegrityError."""
        User = get_user_model()
        User.objects.create_user(email="dup@user.com", password="foo")
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="dup@user.com", password="bar")

    def test_user_is_active_by_default(self):
        """New users should be active by default."""
        User = get_user_model()
        user = User.objects.create_user(email="active@user.com", password="foo")
        self.assertTrue(user.is_active)

    def test_str_returns_email(self):
        """__str__ should return the user's email."""
        User = get_user_model()
        user = User.objects.create_user(email="repr@user.com", password="foo")
        self.assertEqual(str(user), user.email)

class CustomUserModelTests(TestCase):

    def test_additional_fields(self):
        """CustomUser should have additional fields."""
        User = get_user_model()
        user = User.objects.create_user(
            email="test@gmail.com", password="foo",
            first_name="Test", last_name="User", phone_number="1234567890",
            address="123 Test St", city="Testville"
        )
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")
        self.assertEqual(user.phone_number, "1234567890")
        self.assertEqual(user.address, "123 Test St")               
        self.assertEqual(user.city, "Testville")
    
    def test_profile_picture_field(self):
        """CustomUser should have a profile_picture field."""
        User = get_user_model()
        user = User.objects.create_user(
            email="test@gmail.com", password="foo"
        )
        # ImageField returns an empty ImageFieldFile when no file is uploaded
        self.assertFalse(user.profile_picture)  # Should be empty/falsy

# view tests

from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from rest_framework import status


User = get_user_model()

class UserSignupViewTests(APITestCase):
    """Test cases for user signup endpoint"""

    def setUp(self):
        self.client = APIClient()
        self.signup_url = reverse("signup")

    def test_signup_with_valid_email_and_password(self):
        """Test successful user signup"""
        data = {
            "email": "unverified@gmail.com",
            "password": "pass123",
            "password_confirm": "pass123",
            "first_name": "testuser",
            "last_name": "testuser",
            "phone_number": "0205692078"
        }
        response = self.client.post(self.signup_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="unverified@gmail.com").exists())

    def test_signup_with_duplicate_email(self):
        """Test signup fails with duplicate email"""
        User.objects.create_user(email="existing@gmail.com", password="pass123")
        data = {
            "email": "existing@gmail.com",
            "password": "newpass123",
        }
        response = self.client.post(self.signup_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_without_email(self):
        """Test signup fails without email"""
        data = {
            "password": "securepass123",
            "first_name": "Jane",
        }
        response = self.client.post(self.signup_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_without_password(self):
        """Test signup fails without password"""
        data = {
            "email": "nopass@gmail.com",
            "first_name": "John",
        }
        response = self.client.post(self.signup_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_signup_creates_unverified_user(self):
        """Test that new users are created with verified=False by default"""
        data = {
            "email": "unverified@gmail.com",
            "password": "pass123",
            "password_confirm": "pass123",
            "first_name": "testuser",
            "last_name": "testuser",
            "phone_number": "0205692078"
        }
        response = self.client.post(self.signup_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="unverified@gmail.com")
        self.assertFalse(user.verified)


class UserLoginViewTests(APITestCase):
    """Test cases for user login endpoint"""

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse("login")
        self.user = User.objects.create_user(
            email="testuser@gmail.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
        )

    def test_login_with_valid_credentials(self):
        """Test successful login"""
        data = {
            "email": "testuser@gmail.com",
            "password": "testpass123",
        }
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.cookies) # token is stored in cookies

    def test_login_with_invalid_email(self):
        """Test login fails with non-existent email"""
        data = {
            "email": "nonexistent@gmail.com",
            "password": "testpass123",
        }
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_login_with_wrong_password(self):
        """Test login fails with incorrect password"""
        data = {
            "email": "testuser@gmail.com",
            "password": "wrongpassword",
        }
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_without_email(self):
        """Test login fails without email"""
        data = {
            "password": "testpass123",
        }
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_login_without_password(self):
        """Test login fails without password"""
        data = {
            "email": "testuser@gmail.com",
        }
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_sets_jwt_cookie(self):
        """Test that login sets JWT cookie"""
        data = {
            "email": "testuser@gmail.com",
            "password": "testpass123",
        }
        response = self.client.post(self.login_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that cookies are set (access and/or refresh tokens)
        self.assertIn("access", response.cookies or response.data)


class UserProfileViewTests(APITestCase):
    """Test cases for user profile endpoint"""

    def setUp(self):
        self.client = APIClient()
        self.profile_url = reverse("profile")
        self.user = User.objects.create_user(
            email="profileuser@gmail.com",
            password="pass123",
            first_name="Profile",
            last_name="User",
            phone_number="1234567890",
            address="123 Test St",
            city="Test City",
        )

    def test_get_profile_requires_authentication(self):
        """Test that profile endpoint requires authentication"""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_profile_authenticated(self):
        """Test retrieving profile when authenticated"""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["email"], "profileuser@gmail.com")
        self.assertEqual(response.data["data"]["first_name"], "Profile")

    def test_update_profile_authenticated(self):
        """Test updating profile data"""
        self.client.force_authenticate(user=self.user)
        data = {
            "first_name": "Updated",
            "last_name": "Name",
            "phone_number": "9876543210",
        }
        response = self.client.patch(self.profile_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")
        self.assertEqual(self.user.phone_number, "9876543210")

    def test_delete_profile_authenticated(self):
        """Test deleting user profile (account deletion)"""
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # User should be deleted from database
        self.assertFalse(User.objects.filter(email="profileuser@gmail.com").exists())

    def test_profile_put_replaces_user_data(self):
        """Test replacing entire profile with PUT"""
        self.client.force_authenticate(user=self.user)
        data = {
            "email": "profileuser@gmail.com",
            "first_name": "Completely",
            "last_name": "Replaced",
        }
        response = self.client.put(self.profile_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Completely")


# class UserLogoutViewTests(APITestCase):
#     """Test cases for user logout endpoint"""

#     def setUp(self):
#         self.client = APIClient()
#         self.logout_url = reverse("logout")
#         self.user = User.objects.create_user(
#             email="logoutuser@gmail.com",
#             password="pass123",
#         )
#         # Mark user as verified (required by IsVerifiedUser permission)
#         self.user.verified = True
#         self.user.save()

#     def test_logout_requires_authentication(self):
#         """Test that logout endpoint requires authentication"""
#         response = self.client.post(self.logout_url)
#         self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

#     def test_logout_authenticated(self):
#         """Test successful logout"""
#         self.client.force_authenticate(user=self.user)
#         response = self.client.post(self.logout_url)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)


class ChangePasswordRequestViewTests(APITestCase):
    """Test cases for password reset request endpoint (email-based)"""

    def setUp(self):
        self.client = APIClient()
        self.change_password_url = reverse("request_passsword_change")
        self.user = User.objects.create_user(
            email="passuser@gmail.com",
            password="oldpass123",
        )

    def test_change_password_request_with_valid_email(self):
        """Test requesting password change sends email"""
        data = {
            "email": "passuser@gmail.com",
        }
        response = self.client.post(self.change_password_url, data, format="json")
        # Should return 202 (Accepted) as per ChangePasswordRequestView implementation
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data["success"])

    def test_change_password_request_with_invalid_email(self):
        """Test password change request fails with non-existent email"""
        data = {
            "email": "nonexistent@gmail.com",
        }
        response = self.client.post(self.change_password_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data["success"])

    def test_change_password_request_without_email(self):
        """Test password change request fails without email"""
        data = {}
        response = self.client.post(self.change_password_url, data, format="json")
        # Should fail because email is required
        self.assertNotEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_change_password_request_sends_reset_link(self):
        """Test that password reset link is generated and sent"""
        data = {
            "email": "passuser@gmail.com"
        }
        response = self.client.post(self.change_password_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data["success"])
        self.assertIn("link", response.data["data"]) 


from django.urls import reverse
from django.core.cache import cache
from django.core import mail
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.utils.encoding import force_bytes
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import CustomUser
from users.views import TokenGenerator  # adjust import to your file


class PasswordResetFlowTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="test@example.com",
            password="password123"
        )
        self.request_url = reverse("request_passsword_change")
        self.confirm_url = reverse("confirm_password_reset")  

    def test_change_password_request_sends_email_and_stores_token(self):
        """
        Tests:
        - user enters valid email
        - token is created
        - token is stored in cache
        - reset link is emailed
        """
        response = self.client.post(self.request_url, {"email": self.user.email})
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn("link", response.data["data"])

        # 1. Check email sent
        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]
        self.assertIn(self.user.email, sent_email.to)

        # 2. Extract uid and token from link
        link = response.data["data"]["link"]
        self.assertIn("uid=", link)
        self.assertIn("token=", link)

        # 3. Verify token stored in cache
        uid = link.split("uid=")[1].split("&")[0]
        token = link.split("token=")[1]

        user_id = urlsafe_base64_decode(uid).decode()
        
        # The view stores the token with key 'password_token_{user_pk}', not 'password_reset_token'
        cached_token = cache.get(f"password_token_{user_id}")
        self.assertIsNotNone(cached_token)
        self.assertEqual(cached_token, token)

    def test_reset_password_confirm_valid_token(self):
        """
        Tests:
        - view returns success if token matches cached token
        """
        # prepare uid + token as in view logic
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = TokenGenerator().get_url_safe_bytes()

        # store in cache manually (what your view does)
        cache.set(f"password_token_{self.user.pk}", token, timeout=900)

        # now call confirm endpoint
        response = self.client.get(self.confirm_url, {"uid": uid, "token": token})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["token"], token)

    def test_reset_password_confirm_invalid_token(self):
        """
        Tests:
        - invalid/expired token returns 400
        """
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        # store a REAL token
        real_token = TokenGenerator().get_url_safe_bytes()
        cache.set(f"password_token_{self.user.pk}", real_token, timeout=900)

        # call API with wrong token
        wrong_token = "INVALIDTOKEN"
        response = self.client.get(self.confirm_url, {"uid": uid, "token": wrong_token})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])



    
