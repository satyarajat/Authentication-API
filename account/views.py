from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from .models import User
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .serializers import UserSerializer
from .utils import send_activation_email, send_reset_password_email
# from .utils import send_activation_email, send_reset_password_email
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.utils.decorators import method_decorator
from django.conf import settings
# Create your views here.


@method_decorator(ensure_csrf_cookie, name='dispatch')
class GetCSRFToken(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        return Response({'success': 'CSRF Cookie Set'})


@method_decorator(ensure_csrf_cookie, name='dispatch')
class CheckAuthenticatedView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        if request.user.is_authenticated:
            return Response({'IsAuthenticated':True})
        else:
            return Response({'IsAuthenticated':False})

@method_decorator(csrf_protect, name='dispatch')
class RegistrationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.create(serializer.validated_data)

            #Send Account Activation Email
            uid = urlsafe_base64_encode(force_bytes(user.id))
            token = default_token_generator.make_token(user)
            activation_link = reverse('activate', kwargs={'uid':uid, 'token':token})
            activation_url = f'{settings.SITE_DOMAIN}{activation_link}'
            print('----activation_url------', activation_url)
            send_activation_email(user.email, activation_url)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_protect, name='dispatch')
class ActivateView(APIView):
    permission_classes = [AllowAny]

@method_decorator(csrf_protect, name='dispatch')
class ActivationConfirm(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')

        # Fixing the condition to check for both uid and token
        if not uid or not token:
            return Response({'detail': 'Missing UID or TOKEN'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid)
            if default_token_generator.check_token(user, token):
                if user.is_active:
                    return Response({'detail': 'Account is already activated.'}, status=status.HTTP_200_OK)
                else:
                    user.is_active = True
                    user.save()
                    return Response({'detail': 'Account has been activated.'}, status=status.HTTP_200_OK)
            else:
                return Response({'detail': 'Invalid token.'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'detail': 'Invalid Activation Link'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@method_decorator(csrf_protect, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        # User.objects.all()
        user = authenticate(request, email=email, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return Response({'detail': 'Logged in Successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response({'detail': 'Email or Password are Incorrect!'}, status=status.HTTP_400_BAD_REQUEST)


class UserDetailView(APIView):
    def get(self, request):
        serializer = UserSerializer(request.user)
        data = serializer.data
        data['is_staff'] = request.user.is_staff
        return Response(data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data = request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        user = request.user
        if not user.check_password(old_password):
            return Response({'detail': 'Invalid old password.'}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(new_password)
        user.save()
        return Response({'detail':'Password change successfully.'}, status=status.HTTP_200_OK)


@method_decorator(csrf_protect, name='dispatch')
class ResetPasswordEmailView(APIView):
    permission_classes = [AllowAny]
    def post(self, request):
        email = request.data.get('email')
        if not User.objects.filter(email=email).exists():
            return Response({'detail':'User with this email does not exists!'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.get(email=email)

        #Generate password reset token
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = reverse('reset_password', kwargs={'uid': uid, 'token': token})
        reset_url = f'{settings.SITE_DOMAIN}{reset_link}'
        print('----reset_url------', reset_url)
        send_reset_password_email(user.email, reset_url)
        return Response({'detail': 'Password reset email sent successfully.'}, status=status.HTTP_200_OK)



class DeleteAccountView(APIView):
    def delete(self, request):
        user = request.user
        user.delete()
        logout(request)
        return Response({'detail':'Account deleted successfully.'}, status=status.HTTP_204_NO_CONTENT)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'detal': 'Logged out Successfully.'}, status=status.HTTP_200_OK)


@method_decorator(csrf_protect, name='dispatch')
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]


@method_decorator(csrf_protect, name='dispatch')
class ResetPasswordConfirm(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        uid = request.data.get('uid')
        token = request.data.get('token')

        if not uid or not token:
            return Response({'detail': 'Missing UID or TOKEN'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            uid = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=uid)
            if default_token_generator.check_token(user, token):
                new_password = request.data.get('new_password')

                if not new_password:
                    return Response({'detail': 'New Password is Required.'}, status=status.HTTP_400_BAD_REQUEST)

                user.set_password(new_password)
                user.save()
                return Response({'detail':'Password reset successfull.'}, status=status.HTTP_200_OK)

            else:
                return Response({'detail':'Invalid reset password link.'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({'detail': 'Invalid reset password link.'}, status=status.HTTP_400_BAD_REQUEST)


