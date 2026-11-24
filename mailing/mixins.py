from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.models import User


class OwnerRequiredMixin(LoginRequiredMixin):
    """Миксин: только владелец объекта может редактировать/удалять."""
    def dispatch(self, request, *args, **kwargs):
        obj = self.get_object()
        if hasattr(obj, 'user') and obj.user != request.user:
            if not request.user.groups.filter(name='Менеджер').exists():
                messages.error(request, 'У вас нет доступа к этому объекту.')
                return redirect('home')
        return super().dispatch(request, *args, **kwargs)


class ManagerRequiredMixin(LoginRequiredMixin):
    """Миксин: только менеджер может выполнять действие."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.groups.filter(name='Менеджер').exists():
            messages.error(request, 'Только менеджер может выполнять это действие.')
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)
