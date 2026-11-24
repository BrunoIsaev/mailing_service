from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView, PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from .forms import RegisterForm, LoginForm


class RegisterView(LoginView):
    template_name = 'users/register.html'
    form_class = RegisterForm
    
    def get(self, request):
        form = self.form_class()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = self.form_class(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Блокируем до подтверждения email
            user.save()
            
            # Отправляем письмо с подтверждением
            token = default_token_generator.make_token(user)
            uid = user.pk
            confirm_url = request.build_absolute_uri(
                reverse('confirm_email', kwargs={'uid': uid, 'token': token})
            )
            send_mail(
                subject='Подтверждение регистрации',
                message=f'Здравствуйте, {user.username}!\n\nПерейдите по ссылке для подтверждения email:\n{confirm_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            messages.success(request, 'Регистрация успешна! Подтвердите email по ссылке в письме.')
            return redirect('login')
        return render(request, self.template_name, {'form': form})


class ConfirmEmailView(LoginView):
    def get(self, request, uid, token):
        try:
            user = User.objects.get(pk=uid)
        except User.DoesNotExist:
            messages.error(request, 'Неверная ссылка подтверждения.')
            return redirect('login')
        
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            if hasattr(user, 'profile'):
                user.profile.is_email_confirmed = True
                user.profile.save()
            messages.success(request, 'Email подтверждён! Теперь вы можете войти.')
            return redirect('login')
        else:
            messages.error(request, 'Ссылка недействительна или истекла.')
            return redirect('login')


class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    form_class = LoginForm


class CustomLogoutView(LogoutView):
    next_page = 'home'


class CustomPasswordResetView(PasswordResetView):
    template_name = 'users/password_reset.html'
    email_template_name = 'users/password_reset_email.html'
    success_url = '/password-reset/done/'


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'users/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'users/password_reset_confirm.html'
    success_url = '/password-reset/complete/'


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'users/password_reset_complete.html'
