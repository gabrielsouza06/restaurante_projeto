from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Redireciona a página inicial (raiz) direto para a lista de pratos
    path('', RedirectView.as_view(url='/pratos/', permanent=False)),

    # Cardápio
    path('pratos/', views.lista_pratos, name='lista_pratos'),
    path('pratos/novo/', views.criar_prato, name='criar_prato'),
    path('bebidas/nova/', views.criar_bebida, name='criar_bebida'),

    # Pedidos
    path('pedidos/', views.lista_pedidos, name='lista_pedidos'),
    path('pedidos/novo/', views.criar_pedido, name='criar_pedido'),
    path('pedidos/<int:pk>/', views.detalhe_pedido, name='detalhe_pedido'),

    # Itens do Pedido
    path('pedidos/<int:pk>/adicionar-item/', views.adicionar_item_pedido, name='adicionar_item_pedido'),
    path('pedidos/<int:pk>/remover-item/<int:item_pedido_id>/', views.remover_item_pedido, name='remover_item_pedido'),

    # Devoluções
    path('pedidos/<int:pk>/devolucao/', views.registrar_devolucao, name='registrar_devolucao'),

    # Fechamento de Conta / Nota Fiscal & Relatórios
    path('pedidos/<int:pk>/fechar-conta/', views.fechar_conta_view, name='fechar_conta'),
    path('relatorios/', views.relatorios_view, name='relatorios'),

    # portal_funcionarios
    path("funcionarios/", views.portal_funcionarios, name="portal_funcionarios"),
    path("funcionarios/ordem/<int:ordem_id>/concluir/", views.concluir_ordem_manobrista, name="concluir_ordem_manobrista"),
    path("cliente/", views.portal_clientes, name="portal_clientes"),
]