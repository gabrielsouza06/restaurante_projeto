from datetime import datetime
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


DIAS_SEMANA_PT = {
    0: "Segunda",
    1: "Terça",
    2: "Quarta",
    3: "Quinta",
    4: "Sexta",
    5: "Sábado",
    6: "Domingo",
}


class RegiaoSalao(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField(blank=True)

    def __str__(self):
        return self.nome


class Mesa(models.Model):
    numero = models.PositiveIntegerField(unique=True)
    regiao = models.ForeignKey(
        RegiaoSalao, on_delete=models.CASCADE, related_name="mesas"
    )
    capacidade = models.PositiveIntegerField(default=4)
    garcom_responsavel_nome = models.CharField(max_length=120, blank=True)
    ocupada = models.BooleanField(default=False)

    def __str__(self):
        return f"Mesa {self.numero} ({self.regiao.nome})"


class OrdemGerente(models.Model):
    gerente_nome = models.CharField(max_length=120)
    manobrista_nome = models.CharField(max_length=120)
    cliente_nome = models.CharField(max_length=120)
    descricao_ordem = models.CharField(
        max_length=255, default="Colocar carro do cliente na portaria"
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    concluida = models.BooleanField(default=False)

    def marcar_concluida(self):
        self.concluida = True
        self.save()

    def __str__(self):
        status = "Concluída" if self.concluida else "Pendente"
        return f"Ordem #{self.id} - {self.cliente_nome} [{status}]"


class ItemCardapio(models.Model):
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    dias_disponiveis = models.JSONField(default=list)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__desconto_percentual = Decimal("0.00")

    @property
    def desconto_percentual(self) -> Decimal:
        return self.__desconto_percentual

    @desconto_percentual.setter
    def desconto_percentual(self, valor):
        desconto = Decimal(str(valor))
        if desconto < Decimal("0.00") or desconto > Decimal("100.00"):
            raise ValueError("O desconto percentual deve estar entre 0 e 100.")
        self.__desconto_percentual = desconto

    def preco_efetivo(self) -> Decimal:
        fator = Decimal("1.00") - (self.__desconto_percentual / Decimal("100.00"))
        return (self.preco * fator).quantize(Decimal("0.01"))

    def esta_disponivel_hoje(self, dia_semana: str | None = None) -> bool:
        if not self.dias_disponiveis:
            return True
        dia_alvo = dia_semana or DIAS_SEMANA_PT[timezone.localdate().weekday()]
        return dia_alvo in self.dias_disponiveis

    def obter_detalhes(self) -> str:
        return f"{self.nome} - R$ {self.preco_efetivo()}"

    def clean(self):
        if self.preco is not None and self.preco < Decimal("0.00"):
            raise ValidationError("O preço do item não pode ser negativo.")

    def __str__(self):
        return self.nome


class Prato(ItemCardapio):
    categoria = models.CharField(max_length=50)
    tempo_preparo_minutos = models.IntegerField()

    def esta_disponivel_hoje(self, dia_semana: str | None = None) -> bool:
        return super().esta_disponivel_hoje(dia_semana)

    def obter_detalhes(self) -> str:
        return (
            f"[Prato] {self.nome} ({self.categoria}) - "
            f"{self.tempo_preparo_minutos} min - R$ {self.preco_efetivo()}"
        )


class Bebida(ItemCardapio):
    volume_ml = models.IntegerField()
    eh_alcoolica = models.BooleanField(default=False)

    def esta_disponivel_hoje(self, dia_semana: str | None = None) -> bool:
        return super().esta_disponivel_hoje(dia_semana)

    def obter_detalhes(self) -> str:
        alcool_str = "Alcoólica" if self.eh_alcoolica else "Não alcoólica"
        return (
            f"[Bebida] {self.nome} ({self.volume_ml}ml, {alcool_str}) - "
            f"R$ {self.preco_efetivo()}"
        )


class Pedido(models.Model):
    cliente_nome = models.CharField(max_length=150)
    atendente_id = models.IntegerField(null=True, blank=True)
    tipo_atendente = models.CharField(max_length=50)
    modalidade_atendimento = models.CharField(max_length=50)
    mesa = models.ForeignKey(
        Mesa, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos"
    )
    eh_agendado = models.BooleanField(default=False)
    data_hora_criacao = models.DateTimeField(auto_now_add=True)
    data_hora_inicio_atendimento = models.DateTimeField(null=True, blank=True)
    data_hora_agendada = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50, default="Pendente")

    def iniciar_atendimento(self):
        if not self.data_hora_inicio_atendimento:
            self.data_hora_inicio_atendimento = timezone.now()
        if self.status == "Pendente":
            self.status = "Em Atendimento"
        self.save()

    def adicionar_item(
        self,
        item_cardapio: ItemCardapio,
        quantidade: int,
        observacao: str = "",
        validar_disponibilidade: bool = True,
    ):
        if quantidade <= 0:
            raise ValueError("A quantidade deve ser maior que zero.")
        if validar_disponibilidade and not item_cardapio.esta_disponivel_hoje():
            raise ValidationError(
                f"O item '{item_cardapio.nome}' não está disponível hoje."
            )

        if not self.data_hora_inicio_atendimento:
            self.data_hora_inicio_atendimento = timezone.now()
            self.save(update_fields=["data_hora_inicio_atendimento"])

        ItemPedido.objects.create(
            pedido=self,
            item_cardapio=item_cardapio,
            quantidade=quantidade,
            observacao=observacao,
        )

    def verificar_bebida_acompanhando_pratos(self) -> str | None:
        """Verifica se há pratos no pedido sem bebida vinculada."""
        itens = self.itens.select_related("item_cardapio").all()
        tem_prato = any(hasattr(item.item_cardapio, "prato") for item in itens)
        tem_bebida = any(hasattr(item.item_cardapio, "bebida") for item in itens)
        if tem_prato and not tem_bebida:
            return "Atenção: este pedido contém prato(s) sem bebida acompanhando."
        return None

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
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="itens")
    item_cardapio = models.ForeignKey(ItemCardapio, on_delete=models.PROTECT)
    quantidade = models.IntegerField(default=1)
    observacao = models.TextField(blank=True, null=True)

    def clean(self):
        if self.quantidade is not None and self.quantidade <= 0:
            raise ValidationError("A quantidade deve ser maior que zero.")

    def calcular_subtotal(self) -> float:
        return float(self.item_cardapio.preco_efetivo() * self.quantidade)

    def __str__(self):
        return f"{self.quantidade}x {self.item_cardapio.nome} (Pedido #{self.pedido.id})"


class Devolucao(models.Model):
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="devolucoes"
    )
    item_cardapio = models.ForeignKey(ItemCardapio, on_delete=models.PROTECT)
    justificativa = models.TextField()
    data_hora = models.DateTimeField(auto_now_add=True)
    aprovada = models.BooleanField(default=False)

    def registrar_devolucao(self) -> bool:
        if not self.justificativa or not self.justificativa.strip():
            raise ValueError("A justificativa da devolução é obrigatória.")
        self.justificativa = self.justificativa.strip()
        self.save()
        return self.aprovada

    def obter_resumo_devolucao(self) -> str:
        status_str = "Aprovada" if self.aprovada else "Pendente/Rejeitada"
        return (
            f"Devolução #{self.id} - Pedido #{self.pedido.id} - "
            f"Item: {self.item_cardapio.nome} [{status_str}]"
        )

    def __str__(self):
        return f"Devolução #{self.id} - Pedido #{self.pedido.id}"


class Entregador(models.Model):
    nome = models.CharField(max_length=100)
    disponivel = models.BooleanField(default=True)

    def __str__(self):
        status = "Disponível" if self.disponivel else "Em rota"
        return f"{self.nome} ({status})"


class RotaEntrega(models.Model):
    entregador = models.ForeignKey(
        Entregador,
        on_delete=models.PROTECT,
        related_name="rotas",
    )
    enderecos = models.JSONField(
        default=list, help_text="Lista de endereços para entrega"
    )
    criada_em = models.DateTimeField(auto_now_add=True)

    def obter_enderecos_otimizados(self):
        if not isinstance(self.enderecos, list):
            return []
        # Ordena por proximidade textual / bairro-rua mantendo endereços limpos
        limpos = [str(addr).strip() for addr in self.enderecos if str(addr).strip()]
        return sorted(limpos, key=lambda endereco: (len(endereco), endereco.lower()))

    def gerar_manifesto(self):
        linhas = [f"Manifesto - Entregador: {self.entregador.nome}"]
        for i, addr in enumerate(self.obter_enderecos_otimizados(), 1):
            linhas.append(f"  {i}ª Parada: {addr}")
        return "\n".join(linhas)

    def __str__(self):
        return f"Rota #{self.id} - {self.entregador.nome}"


class NotaFiscal(models.Model):
    FORMA_PAGAMENTO_CHOICES = [
        ("CARTAO", "Cartão de Crédito"),
        ("CHEQUE", "Cheque"),
        ("DINHEIRO", "Dinheiro em Espécie"),
    ]

    pedido = models.OneToOneField(
        Pedido,
        on_delete=models.CASCADE,
        related_name="nota_fiscal",
    )
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    hora_chegada = models.DateTimeField()
    hora_atendimento = models.DateTimeField()
    hora_saida = models.DateTimeField(default=timezone.now)
    quitada = models.BooleanField(default=False)

    def clean(self):
        if self.valor_total is not None and self.valor_total < Decimal("0.00"):
            raise ValidationError("O valor total da nota fiscal não pode ser negativo.")
        if (
            self.hora_chegada
            and self.hora_atendimento
            and self.hora_atendimento < self.hora_chegada
        ):
            raise ValidationError(
                "A hora de atendimento não pode ser anterior à hora de chegada."
            )
        if self.hora_chegada and self.hora_saida and self.hora_saida < self.hora_chegada:
            raise ValidationError(
                "A hora de saída não pode ser anterior à hora de chegada."
            )

    def calcular_permanencia_minutos(self) -> float:
        delta = self.hora_saida - self.hora_chegada
        return max(0.0, delta.total_seconds() / 60.0)

    def calcular_tempo_atendimento_minutos(self) -> float:
        delta = self.hora_atendimento - self.hora_chegada
        return max(0.0, delta.total_seconds() / 60.0)

    def __str__(self):
        return f"Nota Fiscal #{self.id} - Pedido #{self.pedido.id}"