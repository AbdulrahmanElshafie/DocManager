from rest_framework.generics import CreateAPIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet
from .serializers import *
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

User = get_user_model()


class RegisterView(CreateAPIView):
    """
    Create new account
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer


class MyTokenObtainPairView(TokenObtainPairView):
    """
    Login
    """
    serializer_class = TokenObtainPairSerializer

    # Define possible responses
    token_response = openapi.Response(
        description="Authentication successful.",
        schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token'),
                'access': openapi.Schema(type=openapi.TYPE_STRING, description='Access token'),
            }
        ),
        examples={
            "application/json": {
                "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
            }
        }
    )

    error_response = openapi.Response(
        description="Authentication failed due to invalid credentials.",
        schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'detail': openapi.Schema(type=openapi.TYPE_STRING, description='Error message'),
            }
        ),
        examples={
            "application/json": {
                "detail": "No active account found with the given credentials"
            }
        }
    )

    @swagger_auto_schema(
        request_body=TokenObtainPairSerializer,
        responses={
            200: token_response,
            401: error_response,
        },
        operation_description="Authenticate user and obtain JWT access and refresh tokens."
    )
    def post(self, request, *args, **kwargs):
        """
        Handle POST request to obtain JWT tokens.
        """
        response = super().post(request, *args, **kwargs)
        return response


class LogoutView(APIView):
    """
    logout
    """
    permission_classes = [IsAuthenticated]

    logout_request_body = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='refresh token'),
        },
        required=['refresh'],  # Specify required fields
    )

    @swagger_auto_schema(
        request_body=logout_request_body
    )
    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    """
    Reset the password.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordResetConfirmSerializer

    # Define possible responses
    success_response = openapi.Response(
        description="Password has been reset successfully.",
        schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'message': openapi.Schema(type=openapi.TYPE_STRING, description='Success message'),
            }
        )
    )

    @swagger_auto_schema(
        request_body=PasswordResetConfirmSerializer,
        responses={
            200: success_response,
            400: openapi.Response(
                description="Bad Request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                        'email': openapi.Schema(type=openapi.TYPE_STRING),
                        'new_password': openapi.Schema(type=openapi.TYPE_STRING),
                        'new_password2': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
        },
        operation_description="Reset the user's password by providing email and new password."
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email=request.data['email'])
        except  User.DoesNotExist:
            return Response(
                {
                    "error": "Invalid email or user does not exist."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if user.check_password(serializer.validated_data['new_password']):
            return Response(
                {
                    "error": "Can't use the same password, kindly change it."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(serializer.validated_data['new_password'])
        user.save()

        return Response(
            {
                "message": "Password has been reset."
            },
            status=status.HTTP_200_OK
        )


class UserView(APIView):
    """
    Get and update user details
    """
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    lookup_field = ('id', 'username', 'email') 

    # Define possible responses
    user_response = openapi.Response(
        description="User details retrieved successfully.",
        schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'id': openapi.Schema(type=openapi.TYPE_INTEGER, description='User ID'),
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='Username'),
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='User email'),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name'),
                'date_joined': openapi.Schema(type=openapi.TYPE_STRING, description='Date user joined'),
                'is_active': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='User active status'),
            }
        )
    )

    error_response = openapi.Response(
        description="Bad Request",
        schema=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='Email validation error'),
                'first_name': openapi.Schema(type=openapi.TYPE_STRING, description='First name validation error'),
                'last_name': openapi.Schema(type=openapi.TYPE_STRING, description='Last name validation error'),
            }
        )
    )

    @swagger_auto_schema(
        responses={
            200: user_response,
            401: 'Authentication credentials were not provided.',
        },
        operation_description="Retrieve the authenticated user's details."
    )
    def get(self, request):
        """
        Handle GET request to retrieve user details.
        """
        serializer = self.serializer_class(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        request_body=UserSerializer,
        responses={
            200: user_response,
            400: error_response,
            401: 'Authentication credentials were not provided.',
        },
        operation_description="Update the authenticated user's details."
    )
    def put(self, request):
        """
        Handle PUT request to fully update user details.
        """
        serializer = self.serializer_class(
            request.user, 
            data=request.data,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @swagger_auto_schema(
        request_body=UserSerializer,
        responses={
            200: user_response,
            400: error_response,
            401: 'Authentication credentials were not provided.',
        },
        operation_description="Partially update the authenticated user's details."
    )
    def patch(self, request):
        """
        Handle PATCH request to partially update user details.
        """
        serializer = self.serializer_class(
            request.user, 
            data=request.data, 
            partial=True,
            context={'request': request}
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserListView(ModelViewSet):
    """
    List all users for permission management
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def list(self, request, *args, **kwargs):
        users = User.objects.all().values('id', 'username', 'email', 'first_name', 'last_name')
        return Response(list(users))
