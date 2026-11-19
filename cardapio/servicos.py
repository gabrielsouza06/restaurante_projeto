from abc import ABC, abstractmethod
from typing import Dict, List
from django.utils import timezone
from .models import NotaFiscal, Devolucao


class FormaPagamento(ABC):
    """Interface / Classe Abstrata para formas de pagamento do restaurante."""

    @abstractmethod
    def processar_pagamento(self, valor: float) -> bool:
        pass

    @abstractmethod
    def obter_descricao(self) -> str:
        pass


class CartaoCredito(FormaPagamento):
    def __init__(self, numero_cartao: str, bandeira: str):
        self.__numero_cartao = numero_cartao
        self.__bandeira = bandeira

    def processar_pagamento(self, valor: float) -> bool:
        final = self.__numero_cartao[-4:] if len(self.__numero_cartao) >= 4 else self.__numero_cartao
        print(f"Transação de R$ {valor:.2f} aprovada no Cartão {self.__bandeira} (Final {final}).")
        return True

    def obter_descricao(self) -> str:
        return f"Cartão de Crédito ({self.__bandeira})"


class Cheque(FormaPagamento):
    def __init__(self, numero_cheque: str, banco: str):
        self.__numero_cheque = numero_cheque
        self.__banco = banco

    def processar_pagamento(self, valor: float) -> bool:
        print(f"Cheque nº {self.__numero_cheque} ({self.__banco}) compensado: R$ {valor:.2f}.")
        return True

    def obter_descricao(self) -> str:
        return f"Cheque ({self.__banco})"


class Dinheiro(FormaPagamento):
    def __init__(self, valor_entregue: float):
        self.__valor_entregue = valor_entregue

    def processar_pagamento(self, valor: float) -> bool:
        if self.__valor_entregue >= valor:
            troco = self.__valor_entregue - valor
            print(f"Pagamento em Dinheiro: R$ {self.__valor_entregue:.2f}. Troco: R$ {troco:.2f}.")
            return True
        print(f"Valor insuficiente! Faltam R$ {valor - self.__valor_entregue:.2f}.")
        return False

    def obter_descricao(self) -> str:
        return "Dinheiro em Espécie"


def fechar_conta_pedido(pedido, metodo_pagamento: FormaPagamento, codigo_tipo: str, hora_atendimento=None) -> NotaFiscal:
    total = float(pedido.calcular_total())
    aprovado = metodo_pagamento.processar_pagamento(total)

    nota = NotaFiscal.objects.create(
        pedido=pedido,
        forma_pagamento=codigo_tipo,
        valor_total=total,
        hora_chegada=pedido.data_hora_criacao,
        hora_atendimento=hora_atendimento or timezone.now(),
        hora_saida=timezone.now(),
        quitada=aprovado,
    )

    if aprovado:
        pedido.status = "CONCLUIDO"
        pedido.save()
        print("NOTA QUITADA - GERENTE NOTIFICADO PARA LIBERAR VEÍCULO NA PORTARIA.")

    return nota


class GerenciadorRelatorios:
    @staticmethod
    def relatorio_tempo_medio_por_garcom():
        print("\n--- [RELATÓRIO A] TEMPO MÉDIO DE ATENDIMENTO POR ATENDENTE ---")
        dados: Dict[str, List[float]] = {}

        for nota in NotaFiscal.objects.select_related("pedido").all():
            atendente = getattr(nota.pedido, "tipo_atendente", "Não informado")
            tempo = nota.calcular_tempo_atendimento_minutos()
            dados.setdefault(atendente, []).append(tempo)

        for atendente, tempos in dados.items():
            media = sum(tempos) / len(tempos)
            print(f"Atendente: {atendente:<15} | Pedidos: {len(tempos):<2} | Tempo Médio: {media:.1f} min")
        print("--------------------------------------------------------------\n")

    @staticmethod
    def relatorio_itens_mais_devolvidos():
        print("\n--- [RELATÓRIO B] ITENS MAIS DEVOLVIDOS E MOTIVOS ---")
        contagem: Dict[str, int] = {}
        motivos: Dict[str, List[str]] = {}

        for dev in Devolucao.objects.select_related("item_cardapio").all():
            nome_item = dev.item_cardapio.nome
            contagem[nome_item] = contagem.get(nome_item, 0) + 1
            motivos.setdefault(nome_item, []).append(dev.justificativa)

        for item, qtd in sorted(contagem.items(), key=lambda x: x[1], reverse=True):
            print(f"Item: {item:<20} | Qtd Devoluções: {qtd}")
            print(f"   Justificativas: {', '.join(motivos[item])}")
        print("-----------------------------------------------------\n")