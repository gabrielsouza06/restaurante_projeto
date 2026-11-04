from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Redireciona a página inicial (raiz) direto para a lista de pratos
    path('', RedirectView.as_view(url='/pratos/', permanent=False)),
    
    path('pratos/', views.lista_pratos, name='lista_pratos'),
    path('pratos/novo/', views.criar_prato, name='criar_prato'),
    path('pedidos/', views.lista_pedidos, name='lista_pedidos'),
    path('pedidos/novo/', views.criar_pedido, name='criar_pedido'),
    path('pedidos/<int:pk>/', views.detalhe_pedido, name='detalhe_pedido'),
]