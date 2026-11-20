from abc import ABC, abstractmethod
from collections import defaultdict
from decimal import Decimal
from typing import Protocol

from django.db import transaction
from django.utils import timezone

from .funcionarios import GerenteGeneral, Manobrista
from .models import Devolucao, NotaFiscal, OrdemGerente, Pedido


class GeradorRelatorioInterface(Protocol):
    """Interface explícita para contratos de relatórios gerenciais."""

    def relatorio_tempo_medio_por_garcom(self) -> list[dict]:
        ...

    def relatorio_itens_mais_devolvidos(self) -> list[dict]:
        ...


class FormaPagamento(ABC):
    """Classe abstrata para métodos de pagamento (polimorfismo)."""

    def __init__(self, valor: Decimal):
        self.valor = Decimal(str(valor))
        if self.valor < Decimal("0.00"):
            raise ValueError("O valor do pagamento não pode ser negativo.")

    @abstractmethod
    def processar(self) -> dict:
        """Executa o processamento específico da forma de pagamento."""


class PagamentoCartao(FormaPagamento):
    def __init__(self, valor: Decimal, bandeira: str = "Visa", numero_cartao: str = ""):
        super().__init__(valor)
        self.bandeira = bandeira.strip() or "Cartão"
        digitos = "".join(ch for ch in numero_cartao if ch.isdigit())
        self.__ultimos_digitos = digitos[-4:] if len(digitos) >= 4 else "0000"

    def processar(self) -> dict:
        return {
            "metodo": "CARTAO",
            "aprovado": True,
            "valor": float(self.valor),
            "mensagem": f"Aprovado no cartão {self.bandeira} (final {self.__ultimos_digitos}).",
        }


class PagamentoDinheiro(FormaPagamento):
    def __init__(self, valor: Decimal, valor_entregue: Decimal | None = None):
        super().__init__(valor)
        self.valor_entregue = Decimal(str(valor_entregue)) if valor_entregue is not None else self.valor

    def processar(self) -> dict:
        if self.valor_entregue < self.valor:
            return {
                "metodo": "DINHEIRO",
                "aprovado": False,
                "valor": float(self.valor),
                "troco": 0.0,
                "mensagem": "Valor entregue insuficiente para quitar o pedido.",
            }
        troco = (self.valor_entregue - self.valor).quantize(Decimal("0.01"))
        return {
            "metodo": "DINHEIRO",
            "aprovado": True,
            "valor": float(self.valor),
            "troco": float(troco),
            "mensagem": f"Recebido em dinheiro. Troco: R$ {troco:.2f}.",
        }


class PagamentoCheque(FormaPagamento):
    def __init__(self, valor: Decimal, banco: str = "", numero_cheque: str = ""):
        super().__init__(valor)
        self.banco = banco.strip() or "Banco não informado"
        self.numero_cheque = numero_cheque.strip() or "S/N"

    def processar(self) -> dict:
        return {
            "metodo": "CHEQUE",
            "aprovado": True,
            "valor": float(self.valor),
            "mensagem": f"Cheque nº {self.numero_cheque} ({self.banco}) registrado para compensação.",
        }


def criar_processador_pagamento(forma_pagamento: str, valor: Decimal, dados: dict) -> FormaPagamento:
    forma = (forma_pagamento or "CARTAO").upper()
    if forma == "DINHEIRO":
        raw_entregue = dados.get("valor_entregue")
        valor_entregue = Decimal(str(raw_entregue)) if raw_entregue not in (None, "") else valor
        return PagamentoDinheiro(valor, valor_entregue=valor_entregue)
    if forma == "CHEQUE":
        return PagamentoCheque(
            valor,
            banco=dados.get("banco", ""),
            numero_cheque=dados.get("numero_cheque", ""),
        )
    return PagamentoCartao(
        valor,
        bandeira=dados.get("bandeira", "Visa"),
        numero_cartao=dados.get("numero_cartao", ""),
    )


def fechar_conta_pedido(
    pedido: Pedido,
    forma_pagamento: str,
    dados_pagamento: dict | None = None,
    gerente_nome: str = "Gerente Geral",
    manobrista_nome: str = "Manobrista Portaria",
    placa_veiculo: str = "",
) -> dict:
    if hasattr(pedido, "nota_fiscal") and pedido.nota_fiscal.quitada:
        return {
            "sucesso": False,
            "mensagem": "Esta conta já foi quitada anteriormente.",
            "nota": pedido.nota_fiscal,
            "ordem_gerente": None,
        }

    dados = dados_pagamento or {}
    total_decimal = Decimal(str(pedido.calcular_total())).quantize(Decimal("0.01"))
    processador = criar_processador_pagamento(forma_pagamento, total_decimal, dados)
    resultado_pgto = processador.processar()

    if not resultado_pgto.get("aprovado", False):
        return {
            "sucesso": False,
            "mensagem": resultado_pgto.get("mensagem", "Pagamento não aprovado."),
            "nota": None,
            "ordem_gerente": None,
        }

    agora = timezone.now()
    hora_chegada = pedido.data_hora_criacao or agora
    hora_atendimento = pedido.data_hora_inicio_atendimento or agora

    with transaction.atomic():
        nota, _ = NotaFiscal.objects.update_or_create(
            pedido=pedido,
            defaults={
                "forma_pagamento": (forma_pagamento or "CARTAO").upper(),
                "valor_total": total_decimal,
                "hora_chegada": hora_chegada,
                "hora_atendimento": hora_atendimento,
                "hora_saida": agora,
                "quitada": True,
            },
        )

        pedido.status = "Fechado / Pago"
        if pedido.mesa:
            pedido.mesa.ocupada = False
            pedido.mesa.save(update_fields=["ocupada"])
        pedido.save(update_fields=["status"])

        gerente = GerenteGeneral(matricula=1, nome=gerente_nome)
        manobrista = Manobrista(matricula=2, nome=manobrista_nome)
        descricao = gerente.emitir_ordem_manobrista(
            manobrista=manobrista,
            cliente_nome=pedido.cliente_nome,
            nota_id=nota.id,
            placa_veiculo=placa_veiculo,
        )

        ordem = OrdemGerente.objects.create(
            gerente_nome=gerente.nome,
            manobrista_nome=manobrista.nome,
            cliente_nome=pedido.cliente_nome,
            descricao_ordem=descricao,
        )

    return {
        "sucesso": True,
        "mensagem": resultado_pgto.get("mensagem", "Conta fechada com sucesso."),
        "nota": nota,
        "ordem_gerente": ordem,
    }


class GerenciadorRelatorios:
    """Implementa GeradorRelatorioInterface para métricas gerenciais."""

    def relatorio_tempo_medio_por_garcom(self) -> list[dict]:
        notas = NotaFiscal.objects.select_related("pedido", "pedido__mesa").all()
        grupos: dict[tuple, list[float]] = defaultdict(list)

        for nota in notas:
            pedido = nota.pedido
            chave = (
                pedido.atendente_id or "sem_id",
                pedido.tipo_atendente or "Atendente",
                pedido.mesa.garcom_responsavel_nome if pedido.mesa and pedido.mesa.garcom_responsavel_nome else "",
            )
            grupos[chave].append(nota.calcular_tempo_atendimento_minutos())

        resultado = []
        for (atendente_id, tipo_atendente, garcom_mesa), tempos in grupos.items():
            media = sum(tempos) / len(tempos) if tempos else 0.0
            nome_exibicao = garcom_mesa or f"{tipo_atendente} (ID: {atendente_id})"
            resultado.append(
                {
                    "atendente": nome_exibicao,
                    "tipo_atendente": tipo_atendente,
                    "quantidade_pedidos": len(tempos),
                    "tempo_medio_minutos": round(media, 2),
                }
            )
        return resultado

    def relatorio_itens_mais_devolvidos(self) -> list[dict]:
        devolucoes = Devolucao.objects.select_related("item_cardapio", "pedido").all()
        contagem: dict[int, dict] = {}

        for dev in devolucoes:
            item_id = dev.item_cardapio.id
            if item_id not in contagem:
                contagem[item_id] = {
                    "item_nome": dev.item_cardapio.nome,
                    "total_devolucoes": 0,
                    "aprovadas": 0,
                }
            contagem[item_id]["total_devolucoes"] += 1
            if dev.aprovada:
                contagem[item_id]["aprovadas"] += 1

        return sorted(
            contagem.values(),
            key=lambda x: x["total_devolucoes"],
            reverse=True,
        )

    def emitir_relatorios_console(self) -> str:
        linhas = [
            "=== RELATÓRIOS GERENCIAIS DO RESTAURANTE ===",
            "",
            "--- 1. Tempo Médio de Atendimento por Garçom ---",
        ]
        for row in self.relatorio_tempo_medio_por_garcom():
            linhas.append(
                f"* {row['atendente']} [{row['tipo_atendente']}]: "
                f"{row['tempo_medio_minutos']} min ({row['quantidade_pedidos']} pedido(s))"
            )

        linhas.extend(["", "--- 2. Itens Mais Devolvidos ---"])
        for row in self.relatorio_itens_mais_devolvidos():
            linhas.append(
                f"* {row['item_nome']}: {row['total_devolucoes']} devolução(ões) "
                f"({row['aprovadas']} aprovada(s))"
            )

        texto = "\n".join(linhas)
        print(texto)
        return texto