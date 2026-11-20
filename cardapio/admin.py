from django.contrib import admin

from .models import (
    Bebida,
    Devolucao,
    Entregador,
    ItemPedido,
    Mesa,
    NotaFiscal,
    OrdemGerente,
    Pedido,
    Prato,
    RegiaoSalao,
    RotaEntrega,
)


@admin.register(RegiaoSalao)
class RegiaoSalaoAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "descricao")
    search_fields = ("nome",)


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ("numero", "regiao", "capacidade", "garcom_responsavel_nome", "ocupada")
    list_filter = ("regiao", "ocupada")
    search_fields = ("numero", "garcom_responsavel_nome")


@admin.register(OrdemGerente)
class OrdemGerenteAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente_nome", "gerente_nome", "manobrista_nome", "concluida", "criada_em")
    list_filter = ("concluida",)


admin.site.register(Prato)
admin.site.register(Bebida)
admin.site.register(Pedido)
admin.site.register(ItemPedido)
admin.site.register(Devolucao)
admin.site.register(Entregador)
admin.site.register(RotaEntrega)
admin.site.register(NotaFiscal)