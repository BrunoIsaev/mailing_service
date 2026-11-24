from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.views.decorators.cache import cache_control
from django.utils.decorators import method_decorator

from .models import Client, Message, Mailing, Attempt
from .forms import ClientForm, MessageForm, MailingForm


def is_manager(user):
    return user.is_superuser or user.groups.filter(name='Менеджер').exists()


class HomeView(View):
    """Главная страница со статистикой."""
    def get(self, request):
        total_mailings = Mailing.objects.count()
        active_mailings = Mailing.objects.filter(
            start_time__lte=timezone.now(),
            end_time__gte=timezone.now(),
            status=Mailing.STATUS_STARTED
        ).count()
        total_clients = Client.objects.count()
        context = {
            'total_mailings': total_mailings,
            'active_mailings': active_mailings,
            'total_clients': total_clients,
        }
        return render(request, 'mailing/home.html', context)


# ---------- Клиенты ----------
class ClientListView(LoginRequiredMixin, View):
    def get(self, request):
        if is_manager(request.user):
            clients = Client.objects.all()
        else:
            clients = Client.objects.filter(owner=request.user)
        return render(request, 'mailing/client_list.html', {'clients': clients})


class ClientCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = ClientForm()
        return render(request, 'mailing/client_form.html', {'form': form})

    def post(self, request):
        form = ClientForm(request.POST)
        if form.is_valid():
            client = form.save(commit=False)
            client.owner = request.user
            client.save()
            messages.success(request, 'Клиент успешно создан.')
            return redirect('client_list')
        return render(request, 'mailing/client_form.html', {'form': form})


class ClientUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        if client.owner != request.user:
            messages.error(request, 'Нет прав на редактирование этого клиента.')
            return redirect('client_list')
        form = ClientForm(instance=client)
        return render(request, 'mailing/client_form.html', {'form': form, 'client': client})

    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        if client.owner != request.user:
            messages.error(request, 'Нет прав на редактирование этого клиента.')
            return redirect('client_list')
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Клиент успешно обновлён.')
            return redirect('client_list')
        return render(request, 'mailing/client_form.html', {'form': form, 'client': client})


class ClientDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        if client.owner != request.user:
            messages.error(request, 'Нет прав на удаление этого клиента.')
            return redirect('client_list')
        client.delete()
        messages.success(request, 'Клиент успешно удалён.')
        return redirect('client_list')


# ---------- Сообщения ----------
class MessageListView(LoginRequiredMixin, View):
    def get(self, request):
        if is_manager(request.user):
            msgs = Message.objects.all()
        else:
            msgs = Message.objects.filter(owner=request.user)
        return render(request, 'mailing/message_list.html', {'messages_list': msgs})


class MessageCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = MessageForm()
        return render(request, 'mailing/message_form.html', {'form': form})

    def post(self, request):
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.owner = request.user
            msg.save()
            messages.success(request, 'Сообщение успешно создано.')
            return redirect('message_list')
        return render(request, 'mailing/message_form.html', {'form': form})


class MessageUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        message = get_object_or_404(Message, pk=pk)
        if message.owner != request.user:
            messages.error(request, 'Нет прав на редактирование этого сообщения.')
            return redirect('message_list')
        form = MessageForm(instance=message)
        return render(request, 'mailing/message_form.html', {'form': form, 'message': message})

    def post(self, request, pk):
        message = get_object_or_404(Message, pk=pk)
        if message.owner != request.user:
            messages.error(request, 'Нет прав на редактирование этого сообщения.')
            return redirect('message_list')
        form = MessageForm(request.POST, instance=message)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сообщение успешно обновлено.')
            return redirect('message_list')
        return render(request, 'mailing/message_form.html', {'form': form, 'message': message})


class MessageDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        message = get_object_or_404(Message, pk=pk)
        if message.owner != request.user:
            messages.error(request, 'Нет прав на удаление этого сообщения.')
            return redirect('message_list')
        message.delete()
        messages.success(request, 'Сообщение успешно удалено.')
        return redirect('message_list')


# ---------- Рассылки ----------
class MailingListView(LoginRequiredMixin, View):
    def get(self, request):
        if is_manager(request.user):
            mailings = Mailing.objects.all()
        else:
            mailings = Mailing.objects.filter(owner=request.user)
        for mailing in mailings:
            mailing.update_status()
        return render(request, 'mailing/mailing_list.html', {'mailings': mailings})


class MailingCreateView(LoginRequiredMixin, View):
    def get(self, request):
        form = MailingForm()
        return render(request, 'mailing/mailing_form.html', {'form': form})

    def post(self, request):
        form = MailingForm(request.POST)
        if form.is_valid():
            mailing = form.save(commit=False)
            mailing.owner = request.user
            mailing.save()
            form.save_m2m()
            messages.success(request, 'Рассылка успешно создана.')
            return redirect('mailing_list')
        return render(request, 'mailing/mailing_form.html', {'form': form})


class MailingUpdateView(LoginRequiredMixin, View):
    def get(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        if mailing.owner != request.user:
            messages.error(request, 'Нет прав на редактирование этой рассылки.')
            return redirect('mailing_list')
        mailing.update_status()
        form = MailingForm(instance=mailing)
        return render(request, 'mailing/mailing_form.html', {'form': form, 'mailing': mailing})

    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        if mailing.owner != request.user:
            messages.error(request, 'Нет прав на редактирование этой рассылки.')
            return redirect('mailing_list')
        form = MailingForm(request.POST, instance=mailing)
        if form.is_valid():
            form.save()
            messages.success(request, 'Рассылка успешно обновлена.')
            return redirect('mailing_list')
        return render(request, 'mailing/mailing_form.html', {'form': form, 'mailing': mailing})


class MailingDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        if mailing.owner != request.user:
            messages.error(request, 'Нет прав на удаление этой рассылки.')
            return redirect('mailing_list')
        mailing.delete()
        messages.success(request, 'Рассылка успешно удалена.')
        return redirect('mailing_list')


class MailingDetailView(LoginRequiredMixin, View):
    def get(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        if not is_manager(request.user) and mailing.owner != request.user:
            messages.error(request, 'Нет прав на просмотр этой рассылки.')
            return redirect('mailing_list')
        mailing.update_status()
        attempts = Attempt.objects.filter(mailing=mailing)
        return render(request, 'mailing/mailing_detail.html', {
            'mailing': mailing,
            'attempts': attempts
        })


class SendMailingView(LoginRequiredMixin, View):
    """Отправка рассылки по требованию."""
    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        if mailing.owner != request.user:
            messages.error(request, 'Нет прав на запуск этой рассылки.')
            return redirect('mailing_list')
        mailing.update_status()

        if mailing.is_disabled:
            messages.error(request, 'Рассылка отключена менеджером.')
            return redirect('mailing_detail', pk=pk)

        now = timezone.now()
        if now < mailing.start_time or now > mailing.end_time:
            messages.error(request, 'Отправка невозможна: текущее время вне диапазона рассылки.')
            return redirect('mailing_detail', pk=pk)

        recipients = mailing.recipients.all()
        attempts = []

        for client in recipients:
            try:
                send_mail(
                    subject=mailing.message.subject,
                    message=mailing.message.body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[client.email],
                    fail_silently=False,
                )
                attempts.append(Attempt(
                    mailing=mailing,
                    client=client,
                    status=Attempt.STATUS_SUCCESS,
                    server_response='Письмо успешно отправлено'
                ))
            except Exception as e:
                attempts.append(Attempt(
                    mailing=mailing,
                    client=client,
                    status=Attempt.STATUS_FAILED,
                    server_response=str(e)
                ))

        Attempt.objects.bulk_create(attempts)
        messages.success(request, f'Рассылка завершена. Успешно: {sum(1 for a in attempts if a.status == Attempt.STATUS_SUCCESS)}, Ошибок: {sum(1 for a in attempts if a.status == Attempt.STATUS_FAILED)}')
        return redirect('mailing_detail', pk=pk)


class DisableMailingView(LoginRequiredMixin, View):
    """Отключение рассылки менеджером."""
    def post(self, request, pk):
        if not is_manager(request.user):
            messages.error(request, 'Только менеджер может отключать рассылки.')
            return redirect('mailing_list')
        mailing = get_object_or_404(Mailing, pk=pk)
        mailing.is_disabled = True
        mailing.save(update_fields=['is_disabled'])
        messages.success(request, f'Рассылка #{mailing.pk} отключена.')
        return redirect('mailing_list')


# ---------- Менеджер: пользователи ----------
class UserListView(LoginRequiredMixin, View):
    def get(self, request):
        if not is_manager(request.user):
            messages.error(request, 'Только менеджер может просматривать список пользователей.')
            return redirect('home')
        users = User.objects.all()
        return render(request, 'mailing/user_list.html', {'users': users})


class BlockUserView(LoginRequiredMixin, View):
    def post(self, request, pk):
        if not is_manager(request.user):
            messages.error(request, 'Только менеджер может блокировать пользователей.')
            return redirect('home')
        user = get_object_or_404(User, pk=pk)
        user.is_active = False
        user.save()
        messages.success(request, f'Пользователь {user.username} заблокирован.')
        return redirect('user_list')


# ---------- Статистика ----------
class StatsView(LoginRequiredMixin, View):
    """Статистика и отчёты (серверное + клиентское кеширование)."""

    @method_decorator(cache_control(public=True, max_age=60))
    def get(self, request):
        cache_key = f'stats_{request.user.pk}'
        data = cache.get(cache_key)
        if data is None:
            if is_manager(request.user):
                mailings = Mailing.objects.all()
            else:
                mailings = Mailing.objects.filter(owner=request.user)
            attempts = Attempt.objects.filter(mailing__in=mailings)
            data = {
                'total_mailings': mailings.count(),
                'total_attempts': attempts.count(),
                'success_attempts': attempts.filter(status=Attempt.STATUS_SUCCESS).count(),
                'failed_attempts': attempts.filter(status=Attempt.STATUS_FAILED).count(),
            }
            cache.set(cache_key, data, 60)
        return render(request, 'mailing/stats.html', data)
