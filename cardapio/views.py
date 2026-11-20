import io
from contextlib import redirect_stdout

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .forms import BebidaForm, PedidoForm, PratoForm
from .funcionarios import (
    ChefeCozinha,
    Garcom,
    GarcomBebida,
    GarcomChefe,
    GerenteGeneral,
    Manobrista,
    Seguranca,
    Telefonista,
)
from .models import (
    Bebida,
    Devolucao,
    ItemCardapio,
    Mesa,
    OrdemGerente,
    Pedido,
    Prato,
    RegiaoSalao,
)
from .servicos import GerenciadorRelatorios, fechar_conta_pedido


def lista_pratos(request):
    pratos = Prato.objects.all()
    bebidas = Bebida.objects.all()
    return render(request, "cardapio/lista_pratos.html", {"pratos": pratos, "bebidas": bebidas})


def criar_prato(request):
    if request.method == "POST":
        form = PratoForm(request.POST)
        if form.is_valid():
            prato = form.save()
            messages.success(request, f"Prato '{prato.nome}' cadastrado com sucesso.")
            return redirect("lista_pratos")
    else:
        form = PratoForm()
    return render(request, "cardapio/form_prato.html", {"form": form, "titulo": "Cadastrar Prato"})


def criar_bebida(request):
    if request.method == "POST":
        form = BebidaForm(request.POST)
        if form.is_valid():
            bebida = form.save()
            messages.success(request, f"Bebida '{bebida.nome}' cadastrada com sucesso.")
            return redirect("lista_pratos")
    else:
        form = BebidaForm()
    return render(request, "cardapio/form_prato.html", {"form": form, "titulo": "Cadastrar Bebida"})


def lista_pedidos(request):
    pedidos = Pedido.objects.select_related("mesa", "mesa__regiao").order_by("-data_hora_criacao")
    return render(request, "pedidos/lista_pedidos.html", {"pedidos": pedidos})


def criar_pedido(request):
    if request.method == "POST":
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            pedido.iniciar_atendimento()
            if pedido.mesa:
                pedido.mesa.ocupada = True
                pedido.mesa.save(update_fields=["ocupada"])
            messages.success(request, f"Pedido #{pedido.id} criado com sucesso.")
            return redirect("detalhe_pedido", pk=pedido.pk)
    else:
        form = PedidoForm()
    return render(request, "pedidos/form_pedido.html", {"form": form})


def detalhe_pedido(request, pk):
    pedido = get_object_or_404(Pedido.objects.select_related("mesa", "mesa__regiao"), pk=pk)
    itens_cardapio = ItemCardapio.objects.order_by("nome")
    itens_pedido = pedido.itens.select_related("item_cardapio").all()
    devolucoes = pedido.devolucoes.select_related("item_cardapio").order_by("-data_hora")
    nota = getattr(pedido, "nota_fiscal", None)
    alerta_bebida = pedido.verificar_bebida_acompanhando_pratos()
    ordens_recentes = OrdemGerente.objects.filter(cliente_nome=pedido.cliente_nome).order_by("-criada_em")[:3]

    return render(
        request,
        "pedidos/detalhe_pedido.html",
        {
            "pedido": pedido,
            "itens_cardapio": itens_cardapio,
            "itens_pedido": itens_pedido,
            "devolucoes": devolucoes,
            "nota": nota,
            "total_pedido": pedido.calcular_total(),
            "alerta_bebida": alerta_bebida,
            "ordens_recentes": ordens_recentes,
        },
    )


def adicionar_item_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        item_id = request.POST.get("item_cardapio_id")
        quantidade_raw = request.POST.get("quantidade", "1")
        observacao = request.POST.get("observacao", "").strip()
        validar_dia = request.POST.get("forcar_indisponivel") != "on"

        item = get_object_or_404(ItemCardapio, pk=item_id)
        try:
            quantidade = max(1, int(quantidade_raw))
            pedido.adicionar_item(
                item_cardapio=item,
                quantidade=quantidade,
                observacao=observacao,
                validar_disponibilidade=validar_dia,
            )
            messages.success(request, f"{quantidade}x {item.nome} adicionado ao pedido.")
        except (ValueError, ValidationError) as exc:
            messages.error(request, str(exc))
    return redirect("detalhe_pedido", pk=pedido.pk)


def remover_item_pedido(request, pk, item_pedido_id):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        pedido.remover_item(item_pedido_id)
        messages.success(request, "Item removido do pedido.")
    return redirect("detalhe_pedido", pk=pedido.pk)


def registrar_devolucao(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        item_id = request.POST.get("item_cardapio_id")
        justificativa = request.POST.get("justificativa", "").strip()
        aprovada = request.POST.get("aprovada") == "on"
        item = get_object_or_404(ItemCardapio, pk=item_id)

        dev = Devolucao(
            pedido=pedido,
            item_cardapio=item,
            justificativa=justificativa,
            aprovada=aprovada,
        )
        try:
            dev.registrar_devolucao()
            messages.success(request, "Devolução registrada com sucesso.")
        except ValueError as exc:
            messages.error(request, str(exc))
    return redirect("detalhe_pedido", pk=pedido.pk)


def fechar_conta_view(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == "POST":
        forma_pagamento = request.POST.get("forma_pagamento", "CARTAO")
        dados_pagamento = {
            "bandeira": request.POST.get("bandeira", "Visa"),
            "numero_cartao": request.POST.get("numero_cartao", ""),
            "valor_entregue": request.POST.get("valor_entregue", ""),
            "banco": request.POST.get("banco", ""),
            "numero_cheque": request.POST.get("numero_cheque", ""),
        }
        resultado = fechar_conta_pedido(
            pedido=pedido,
            forma_pagamento=forma_pagamento,
            dados_pagamento=dados_pagamento,
            placa_veiculo=request.POST.get("placa_veiculo", ""),
        )
        if resultado["sucesso"]:
            messages.success(
                request,
                f"{resultado['mensagem']} Ordem emitida ao manobrista para {pedido.cliente_nome}.",
            )
        else:
            messages.error(request, resultado["mensagem"])
    return redirect("detalhe_pedido", pk=pedido.pk)


def relatorios_view(request):
    gerenciador = GerenciadorRelatorios()
    relatorio_garcons = gerenciador.relatorio_tempo_medio_por_garcom()
    relatorio_devolucoes = gerenciador.relatorio_itens_mais_devolvidos()

    buffer = io.StringIO()
    with redirect_stdout(buffer):
        gerenciador.emitir_relatorios_console()
    saida_relatorios = buffer.getvalue()

    if request.GET.get("console") == "1":
        print(saida_relatorios)
        messages.info(request, "Relatórios emitidos também no console do servidor.")

    return render(
        request,
        "pedidos/relatorios.html",
        {
            "saida_relatorios": saida_relatorios,
            "relatorio_garcons": relatorio_garcons,
            "relatorio_devolucoes": relatorio_devolucoes,
        },
    )


def portal_funcionarios(request):
    """Área interna da equipe organizada pela hierarquia Funcionario (ABC)."""
    equipe_hierarquia = [
        ("1. Direção e Liderança", GerenteGeneral(1, "Ana Paula", turno="Integral")),
        ("1. Direção e Liderança", ChefeCozinha(2, "Bruno Henrique", turno="Integral")),
        ("1. Direção e Liderança", GarcomChefe(3, "Carla Mendes", regiao_supervisionada="Salão Principal")),
        ("2. Atendimento e Salão", Garcom(4, "Carlos Silva", mesas_atendidas=[1, 2, 3])),
        ("2. Atendimento e Salão", GarcomBebida(5, "Diego Santos", turno="Noite")),
        ("2. Atendimento e Salão", Telefonista(6, "Elena Costa", turno="Integral")),
        ("3. Portaria e Apoio", Manobrista(7, "Fábio Rocha", turno="Noite")),
        ("3. Portaria e Apoio", Seguranca(8, "Gustavo Lima", turno="Noite")),
    ]

    cargo_filtro = request.GET.get("cargo", "").strip()
    equipe_filtrada = [
        {"nivel": nivel, "obj": func}
        for nivel, func in equipe_hierarquia
        if not cargo_filtro or func.cargo == cargo_filtro
    ]

    cargos_disponiveis = list(dict.fromkeys(func.cargo for _, func in equipe_hierarquia))

    contexto = {
        "equipe": equipe_filtrada,
        "cargos_disponiveis": cargos_disponiveis,
        "cargo_selecionado": cargo_filtro,
        "regioes": RegiaoSalao.objects.prefetch_related("mesas").all(),
        "pedidos_abertos": Pedido.objects.exclude(status="Fechado / Pago").order_by("-data_hora_criacao"),
        "ordens_manobrista": OrdemGerente.objects.filter(concluida=False).order_by("-criada_em"),
        "devolucoes_recentes": Devolucao.objects.select_related("pedido", "item_cardapio").order_by("-data_hora")[:5],
    }
    return render(request, "portal/portal_funcionarios.html", contexto)


def concluir_ordem_manobrista(request, ordem_id):
    """Permite ao manobrista marcar uma ordem do gerente como concluída."""
    if request.method == "POST":
        ordem = get_object_or_404(OrdemGerente, id=ordem_id)
        ordem.marcar_concluida()
        messages.success(request, f"Ordem #{ordem.id} ({ordem.cliente_nome}) concluída pelo manobrista.")
    return redirect("portal_funcionarios")


def portal_clientes(request):
    """Área pública para clientes: cardápio do dia, mesas livres e pedido rápido."""
    pratos_hoje = [p for p in Prato.objects.all() if p.esta_disponivel_hoje()]
    bebidas_hoje = [b for b in Bebida.objects.all() if b.esta_disponivel_hoje()]
    mesas_livres = Mesa.objects.select_related("regiao").filter(ocupada=False).order_by("numero")

    pedido_criado = None
    alerta_bebida = None

    if request.method == "POST":
        cliente_nome = request.POST.get("cliente_nome", "").strip()
        modalidade = request.POST.get("modalidade_atendimento", "Salão")
        mesa_id = request.POST.get("mesa_id")
        prato_id = request.POST.get("prato_id")
        bebida_id = request.POST.get("bebida_id")
        observacao = request.POST.get("observacao", "").strip()

        try:
            qtd_prato = max(1, int(request.POST.get("qtd_prato") or 1))
            qtd_bebida = max(1, int(request.POST.get("qtd_bebida") or 1))
        except ValueError:
            qtd_prato, qtd_bebida = 1, 1

        if not cliente_nome:
            messages.error(request, "Por favor, informe seu nome para fazer o pedido.")
        elif not prato_id and not bebida_id:
            messages.error(request, "Escolha pelo menos um prato ou uma bebida.")
        else:
            try:
                with transaction.atomic():
                    mesa_obj = None
                    if mesa_id:
                        mesa_obj = get_object_or_404(Mesa, id=mesa_id, ocupada=False)
                        mesa_obj.ocupada = True
                        mesa_obj.save(update_fields=["ocupada"])

                    pedido = Pedido.objects.create(
                        cliente_nome=cliente_nome,
                        tipo_atendente="Autoatendimento Cliente",
                        modalidade_atendimento=modalidade,
                        mesa=mesa_obj,
                        status="Em Atendimento",
                    )

                    if prato_id:
                        prato = get_object_or_404(Prato, id=prato_id)
                        pedido.adicionar_item(prato, qtd_prato, observacao=observacao)

                    if bebida_id:
                        bebida = get_object_or_404(Bebida, id=bebida_id)
                        pedido.adicionar_item(bebida, qtd_bebida)

                    pedido_criado = pedido
                    alerta_bebida = pedido.verificar_bebida_acompanhando_pratos()
                    messages.success(request, f"Pedido #{pedido.id} enviado com sucesso!")
            except (ValidationError, ValueError) as exc:
                messages.error(request, str(exc))

    contexto = {
        "pratos_hoje": pratos_hoje,
        "bebidas_hoje": bebidas_hoje,
        "mesas_livres": mesas_livres,
        "pedido_criado": pedido_criado,
        "alerta_bebida": alerta_bebida,
    }
    return render(request, "portal/portal_clientes.html", contexto)