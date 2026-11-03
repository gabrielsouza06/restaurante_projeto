from django import forms
from .models import Prato, Bebida, Pedido

class PratoForm(forms.ModelForm):
    class Meta:
        model = Prato
        fields = ['nome', 'preco', 'dias_disponiveis', 'categoria', 'tempo_preparo_minutos']

class BebidaForm(forms.ModelForm):
    class Meta:
        model = Bebida
        fields = ['nome', 'preco', 'dias_disponiveis', 'volume_ml', 'eh_alcoolica']

class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ['cliente_nome', 'tipo_atendente', 'modalidade_atendimento', 'eh_agendado', 'data_hora_agendada']
        widgets = {
            'data_hora_agendada': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }