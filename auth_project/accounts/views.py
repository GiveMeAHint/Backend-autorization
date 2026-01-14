from rest_framework import generics, status, mixins
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from .serializers import RegisterSerializer, LoginSerializer, UserSerializer
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer, AddToCartSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "message": "Регистрация успешна"
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "Логин или пароль не верны"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        auth_user = authenticate(
            request=request, 
            username=user.username, 
            password=password
        )
        
        if auth_user is not None:
            refresh = RefreshToken.for_user(auth_user)
            
            return Response({
                "user": UserSerializer(auth_user).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "message": "Вход выполнен успешно"
            })
        else:
            return Response(
                {"error": "Логин или пароль не верны"},
                status=status.HTTP_401_UNAUTHORIZED
            )


class ProfileView(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class LogoutView(generics.GenericAPIView):
    permission_classes = (IsAuthenticated,)
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()  # Добавляем токен в черный список
                except TokenError as e:
                    return Response(
                        {"error": f"Неверный токен: {str(e)}"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            return Response(
                {"message": "Выход выполнен успешно. Токен инвалидирован."},
                status=status.HTTP_205_RESET_CONTENT
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class CartView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer
    
    def get_object(self):
        cart, created = Cart.objects.get_or_create(
            user=self.request.user,
            is_active=True
        )
        return cart


class AddToCartView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AddToCartSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        cart, created = Cart.objects.get_or_create(
            user=request.user,
            is_active=True
        )
        
        product_id = serializer.validated_data['product_id']
        quantity = serializer.validated_data.get('quantity', 1)
        
        cart_item, item_created = CartItem.objects.get_or_create(
            cart=cart,
            product_id=product_id,
            defaults={
                'title': serializer.validated_data['title'],
                'price': serializer.validated_data['price'],
                'quantity': quantity,
                'image_url': serializer.validated_data.get('image_url')
            }
        )
        
        if not item_created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return Response({
            'success': True,
            'message': 'Товар добавлен в корзину',
            'item': CartItemSerializer(cart_item).data,
            'cart_total': cart.total_price,
            'items_count': cart.items.count()
        }, status=status.HTTP_201_CREATED)


class UpdateCartItemView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartItemSerializer
    queryset = CartItem.objects.all()
    
    def get_object(self):
        cart = Cart.objects.get(user=self.request.user, is_active=True)
        return generics.get_object_or_404(
            CartItem,
            cart=cart,
            id=self.kwargs['item_id']
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        quantity = request.data.get('quantity')
        if quantity is not None:
            if quantity < 1:
                instance.delete()
                return Response({
                    'success': True,
                    'message': 'Товар удалён из корзины',
                    'cart': CartSerializer(instance.cart).data
                })
            else:
                instance.quantity = quantity
                instance.save()
        
        serializer = self.get_serializer(instance)
        return Response({
            'success': True,
            'item': serializer.data,
            'cart': CartSerializer(instance.cart).data
        })


class RemoveFromCartView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        cart = Cart.objects.get(user=self.request.user, is_active=True)
        return generics.get_object_or_404(
            CartItem,
            cart=cart,
            id=self.kwargs['item_id']
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        cart = instance.cart
        instance.delete()
        
        return Response({
            'success': True,
            'message': 'Товар удалён из корзины',
            'cart': CartSerializer(cart).data
        }, status=status.HTTP_200_OK)


class ClearCartView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        cart = Cart.objects.get(user=request.user, is_active=True)
        cart.items.all().delete()
        
        return Response({
            'success': True,
            'message': 'Корзина очищена',
            'cart': CartSerializer(cart).data
        })