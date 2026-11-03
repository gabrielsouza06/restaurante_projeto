from django.shortcuts import render, redirect, get_object_or_404
from .models import Prato, Bebida, Pedido
from .forms import PratoForm, BebidaForm, PedidoForm

def lista_pratos(request):
    pratos = Prato.objects.all()
    return render(request, 'cardapio/lista_pratos.html', {'pratos': pratos})

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
    return render(request, 'pedidos/detalhe_pedido.html', {'pedido': pedido})