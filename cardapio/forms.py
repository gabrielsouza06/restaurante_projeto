from django import forms

from .models import Bebida, Mesa, Pedido, Prato, RotaEntrega

DIAS_SEMANA_CHOICES = [
    ("Segunda", "Segunda-feira"),
    ("Terça", "Terça-feira"),
    ("Quarta", "Quarta-feira"),
    ("Quinta", "Quinta-feira"),
    ("Sexta", "Sexta-feira"),
    ("Sábado", "Sábado"),
    ("Domingo", "Domingo"),
]


class PratoForm(forms.ModelForm):
    dias_selecionados = forms.MultipleChoiceField(
        label="Dias disponíveis",
        choices=DIAS_SEMANA_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Prato
        fields = ["nome", "preco", "categoria", "tempo_preparo_minutos"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and isinstance(self.instance.dias_disponiveis, list):
            self.fields["dias_selecionados"].initial = self.instance.dias_disponiveis
        elif not self.is_bound:
            self.fields["dias_selecionados"].initial = [dia for dia, _ in DIAS_SEMANA_CHOICES]

    def save(self, commit=True):
        prato = super().save(commit=False)
        escolhidos = self.cleaned_data.get("dias_selecionados")
        if escolhidos:
            prato.dias_disponiveis = list(escolhidos)
        elif not prato.dias_disponiveis:
            prato.dias_disponiveis = [dia for dia, _ in DIAS_SEMANA_CHOICES]
        if commit:
            prato.save()
        return prato


class BebidaForm(forms.ModelForm):
    dias_selecionados = forms.MultipleChoiceField(
        label="Dias disponíveis",
        choices=DIAS_SEMANA_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Bebida
        fields = ["nome", "preco", "volume_ml", "eh_alcoolica"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and isinstance(self.instance.dias_disponiveis, list):
            self.fields["dias_selecionados"].initial = self.instance.dias_disponiveis
        elif not self.is_bound:
            self.fields["dias_selecionados"].initial = [dia for dia, _ in DIAS_SEMANA_CHOICES]

    def save(self, commit=True):
        bebida = super().save(commit=False)
        escolhidos = self.cleaned_data.get("dias_selecionados")
        if escolhidos:
            bebida.dias_disponiveis = list(escolhidos)
        elif not bebida.dias_disponiveis:
            bebida.dias_disponiveis = [dia for dia, _ in DIAS_SEMANA_CHOICES]
        if commit:
            bebida.save()
        return bebida


class PedidoForm(forms.ModelForm):
    mesa = forms.ModelChoiceField(
        queryset=Mesa.objects.select_related("regiao").order_by("numero"),
        required=False,
        label="Mesa (se atendimento no salão)",
    )

    class Meta:
        model = Pedido
        fields = [
            "cliente_nome",
            "atendente_id",
            "tipo_atendente",
            "modalidade_atendimento",
            "mesa",
            "eh_agendado",
            "data_hora_agendada",
        ]
        widgets = {
            "data_hora_agendada": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }


class RotaEntregaForm(forms.ModelForm):
    enderecos_texto = forms.CharField(
        label="Endereços de entrega",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 4,
                "placeholder": "Um endereço por linha\nEx.: Rua A, 120\nAv. Central, 45",
            }
        ),
    )

    class Meta:
        model = RotaEntrega
        fields = ["entregador"]

    def save(self, commit=True):
        rota = super().save(commit=False)
        texto = self.cleaned_data.get("enderecos_texto", "")
        rota.enderecos = [linha.strip() for linha in texto.splitlines() if linha.strip()]
        if commit:
            rota.save()
        return rota