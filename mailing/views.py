from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import Client, Message, Mailing, Attempt
from .forms import ClientForm, MessageForm, MailingForm


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


# CRUD для клиентов
class ClientListView(View):
    def get(self, request):
        clients = Client.objects.all()
        return render(request, 'mailing/client_list.html', {'clients': clients})


class ClientCreateView(View):
    def get(self, request):
        form = ClientForm()
        return render(request, 'mailing/client_form.html', {'form': form})
    
    def post(self, request):
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Клиент успешно создан.')
            return redirect('client_list')
        return render(request, 'mailing/client_form.html', {'form': form})


class ClientUpdateView(View):
    def get(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = ClientForm(instance=client)
        return render(request, 'mailing/client_form.html', {'form': form, 'client': client})
    
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Клиент успешно обновлён.')
            return redirect('client_list')
        return render(request, 'mailing/client_form.html', {'form': form, 'client': client})


class ClientDeleteView(View):
    def post(self, request, pk):
        client = get_object_or_404(Client, pk=pk)
        client.delete()
        messages.success(request, 'Клиент успешно удалён.')
        return redirect('client_list')


# CRUD для сообщений
class MessageListView(View):
    def get(self, request):
        messages_list = Message.objects.all()
        return render(request, 'mailing/message_list.html', {'messages': messages_list})


class MessageCreateView(View):
    def get(self, request):
        form = MessageForm()
        return render(request, 'mailing/message_form.html', {'form': form})
    
    def post(self, request):
        form = MessageForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сообщение успешно создано.')
            return redirect('message_list')
        return render(request, 'mailing/message_form.html', {'form': form})


class MessageUpdateView(View):
    def get(self, request, pk):
        message = get_object_or_404(Message, pk=pk)
        form = MessageForm(instance=message)
        return render(request, 'mailing/message_form.html', {'form': form, 'message': message})
    
    def post(self, request, pk):
        message = get_object_or_404(Message, pk=pk)
        form = MessageForm(request.POST, instance=message)
        if form.is_valid():
            form.save()
            messages.success(request, 'Сообщение успешно обновлено.')
            return redirect('message_list')
        return render(request, 'mailing/message_form.html', {'form': form, 'message': message})


class MessageDeleteView(View):
    def post(self, request, pk):
        message = get_object_or_404(Message, pk=pk)
        message.delete()
        messages.success(request, 'Сообщение успешно удалено.')
        return redirect('message_list')


# CRUD для рассылок
class MailingListView(View):
    def get(self, request):
        mailings = Mailing.objects.all()
        for mailing in mailings:
            mailing.update_status()
        return render(request, 'mailing/mailing_list.html', {'mailings': mailings})


class MailingCreateView(View):
    def get(self, request):
        form = MailingForm()
        return render(request, 'mailing/mailing_form.html', {'form': form})
    
    def post(self, request):
        form = MailingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Рассылка успешно создана.')
            return redirect('mailing_list')
        return render(request, 'mailing/mailing_form.html', {'form': form})


class MailingUpdateView(View):
    def get(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        mailing.update_status()
        form = MailingForm(instance=mailing)
        return render(request, 'mailing/mailing_form.html', {'form': form, 'mailing': mailing})
    
    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        form = MailingForm(request.POST, instance=mailing)
        if form.is_valid():
            form.save()
            messages.success(request, 'Рассылка успешно обновлена.')
            return redirect('mailing_list')
        return render(request, 'mailing/mailing_form.html', {'form': form, 'mailing': mailing})


class MailingDeleteView(View):
    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        mailing.delete()
        messages.success(request, 'Рассылка успешно удалена.')
        return redirect('mailing_list')


class MailingDetailView(View):
    def get(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        mailing.update_status()
        attempts = Attempt.objects.filter(mailing=mailing)
        return render(request, 'mailing/mailing_detail.html', {
            'mailing': mailing,
            'attempts': attempts
        })


class SendMailingView(View):
    """Отправка рассылки по требованию."""
    def post(self, request, pk):
        mailing = get_object_or_404(Mailing, pk=pk)
        mailing.update_status()
        
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
        
        # Batch создание записей
        Attempt.objects.bulk_create(attempts)
        messages.success(request, f'Рассылка завершена. Успешно: {sum(1 for a in attempts if a.status == Attempt.STATUS_SUCCESS)}, Ошибок: {sum(1 for a in attempts if a.status == Attempt.STATUS_FAILED)}')
        return redirect('mailing_detail', pk=pk)
