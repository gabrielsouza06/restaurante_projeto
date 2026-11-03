from django.db import models
from datetime import datetime

class ItemCardapio(models.Model):
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    dias_disponiveis = models.JSONField(default=list)

    def esta_disponivel_hoje(self, dia_semana: str) -> bool:
        return dia_semana in self.dias_disponiveis

    def obter_detalhes(self) -> str:
        return f"{self.nome} - R$ {self.preco}"

    def __str__(self):
        return self.nome


class Prato(ItemCardapio):
    categoria = models.CharField(max_length=50)
    tempo_preparo_minutos = models.IntegerField()

    def esta_disponivel_hoje(self, dia_semana: str) -> bool:
        return super().esta_disponivel_hoje(dia_semana)

    def obter_detalhes(self) -> str:
        return f"[Prato] {self.nome} ({self.categoria}) - {self.tempo_preparo_minutos} min - R$ {self.preco}"


class Bebida(ItemCardapio):
    volume_ml = models.IntegerField()
    eh_alcoolica = models.BooleanField(default=False)

    def esta_disponivel_hoje(self, dia_semana: str) -> bool:
        return super().esta_disponivel_hoje(dia_semana)

    def obter_detalhes(self) -> str:
        alcool_str = "Alcoólica" if self.eh_alcoolica else "Não alcoólica"
        return f"[Bebida] {self.nome} ({self.volume_ml}ml, {alcool_str}) - R$ {self.preco}"


class Pedido(models.Model):
    cliente_nome = models.CharField(max_length=150)
    atendente_id = models.IntegerField(null=True, blank=True)
    tipo_atendente = models.CharField(max_length=50)
    modalidade_atendimento = models.CharField(max_length=50)
    eh_agendado = models.BooleanField(default=False)
    data_hora_criacao = models.DateTimeField(auto_now_add=True)
    data_hora_agendada = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, default="Pendente")

    def adicionar_item(self, item_cardapio: ItemCardapio, quantidade: int, observacao: str = ""):
        ItemPedido.objects.create(
            pedido=self,
            item_cardapio=item_cardapio,
            quantidade=quantidade,
            observacao=observacao
        )

    def remover_item(self, item_id: int):
        ItemPedido.objects.filter(id=item_id, pedido=self).delete()

    def calcular_total(self) -> float:
        total = sum(item.calcular_subtotal() for item in self.itens.all())
        return float(total)

    def agendar_atendimento(self, data_hora: datetime):
        self.eh_agendado = True
        self.data_hora_agendada = data_hora
        self.save()

    def __str__(self):
        return f"Pedido #{self.id} - {self.cliente_nome} ({self.status})"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    item_cardapio = models.ForeignKey(ItemCardapio, on_delete=models.PROTECT)
    quantidade = models.IntegerField(default=1)
    observacao = models.TextField(blank=True, null=True)

    def calcular_subtotal(self) -> float:
        return float(self.item_cardapio.preco * self.quantidade)

    def __str__(self):
        return f"{self.quantidade}x {self.item_cardapio.nome} (Pedido #{self.pedido.id})"


class Devolucao(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='devolucoes')
    item_cardapio = models.ForeignKey(ItemCardapio, on_delete=models.PROTECT)
    justificativa = models.TextField()
    data_hora = models.DateTimeField(auto_now_add=True)
    aprovada = models.BooleanField(default=False)

    def registrar_devolucao(self) -> bool:
        self.save()
        return self.aprovada

    def obter_resumo_devolucao(self) -> str:
        status_str = "Aprovada" if self.aprovada else "Pendente/Rejeitada"
        return f"Devolução #{self.id} - Pedido #{self.pedido.id} - Item: {self.item_cardapio.nome} [{status_str}]"

    def __str__(self):
        return f"Devolução #{self.id} - Pedido #{self.pedido.id}"