import io
from contextlib import redirect_stdout
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from .models import Bebida, Devolucao, ItemCardapio, Pedido, Prato
from .forms import PratoForm, BebidaForm, PedidoForm
from .servicos import (
    CartaoCredito,
    Cheque,
    Dinheiro,
    GerenciadorRelatorios,
    fechar_conta_pedido,
)


def lista_pratos(request):
    pratos = Prato.objects.all()
    bebidas = Bebida.objects.all()
    return render(request, 'cardapio/lista_pratos.html', {'pratos': pratos, 'bebidas': bebidas})


def criar_prato(request):
    if request.method == 'POST':
        form = PratoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_pratos')
    else:
        form = PratoForm()
    return render(request, 'cardapio/form_prato.html', {'form': form})


def lista_pedidos(request):
    pedidos = Pedido.objects.all().order_by('-data_hora_criacao')
    return render(request, 'pedidos/lista_pedidos.html', {'pedidos': pedidos})


def criar_pedido(request):
    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save()
            return redirect('detalhe_pedido', pk=pedido.pk)
    else:
        form = PedidoForm()
    return render(request, 'pedidos/form_pedido.html', {'form': form})


def detalhe_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    itens_cardapio = ItemCardapio.objects.all()
    itens_pedido = pedido.itens.select_related('item_cardapio').all()
    devolucoes = pedido.devolucoes.select_related('item_cardapio').all()
    nota = getattr(pedido, 'nota_fiscal', None)

    return render(
        request,
        'pedidos/detalhe_pedido.html',
        {
            'pedido': pedido,
            'itens_cardapio': itens_cardapio,
            'itens_pedido': itens_pedido,
            'devolucoes': devolucoes,
            'nota': nota,
            'total_pedido': pedido.calcular_total(),
        },
    )


def adicionar_item_pedido(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        item_id = request.POST.get('item_cardapio_id')
        quantidade = int(request.POST.get('quantidade', 1))
        observacao = request.POST.get('observacao', '').strip()
        item = get_object_or_404(ItemCardapio, pk=item_id)
        pedido.adicionar_item(item, max(1, quantidade), observacao)
    return redirect('detalhe_pedido', pk=pedido.pk)


def remover_item_pedido(request, pk, item_pedido_id):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        pedido.remover_item(item_pedido_id)
    return redirect('detalhe_pedido', pk=pedido.pk)


def registrar_devolucao(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        item_id = request.POST.get('item_cardapio_id')
        justificativa = request.POST.get('justificativa', '').strip()
        aprovada = request.POST.get('aprovada') == 'on'
        item = get_object_or_404(ItemCardapio, pk=item_id)
        if justificativa:
            dev = Devolucao(
                pedido=pedido,
                item_cardapio=item,
                justificativa=justificativa,
                aprovada=aprovada,
            )
            dev.registrar_devolucao()
    return redirect('detalhe_pedido', pk=pedido.pk)


def fechar_conta_view(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if request.method == 'POST':
        tipo = request.POST.get('forma_pagamento', 'CARTAO')
        total = float(pedido.calcular_total())

        if tipo == 'DINHEIRO':
            valor_entregue = float(request.POST.get('valor_entregue') or total)
            metodo = Dinheiro(valor_entregue)
        elif tipo == 'CHEQUE':
            numero_cheque = request.POST.get('numero_cheque', '0001')
            banco = request.POST.get('banco', 'Banco do Brasil')
            metodo = Cheque(numero_cheque, banco)
        else:
            numero_cartao = request.POST.get('numero_cartao', '4111111111111234')
            bandeira = request.POST.get('bandeira', 'Visa')
            metodo = CartaoCredito(numero_cartao, bandeira)

        fechar_conta_pedido(
            pedido=pedido,
            metodo_pagamento=metodo,
            codigo_tipo=tipo,
            hora_atendimento=timezone.now(),
        )
    return redirect('detalhe_pedido', pk=pedido.pk)


def relatorios_view(request):
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        GerenciadorRelatorios.relatorio_tempo_medio_por_garcom()
        GerenciadorRelatorios.relatorio_itens_mais_devolvidos()
    saida_relatorios = buffer.getvalue()
    return render(request, 'pedidos/relatorios.html', {'saida_relatorios': saida_relatorios})