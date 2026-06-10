from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from .models import (
    Utilizador, Categoria, Fornecedor, Produto,
    Movimentacao, Inventario, ItemInventario, Log,
    LoteEstoque 
)


# =============================================================================
# UTILIZADOR
# =============================================================================

@admin.register(Utilizador)
class UtilizadorAdmin(UserAdmin):
    list_display  = ('utilizador', 'username', 'email', 'perfil', 'badge_ativo', 'create_at')
    list_filter   = ('perfil', 'ativo', 'is_staff')
    search_fields = ('utilizador', 'username', 'email')
    ordering      = ('utilizador',)

    fieldsets = UserAdmin.fieldsets + (
        ('Dados do Sistema', {
            'fields': ('utilizador', 'perfil', 'ativo')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Dados do Sistema', {
            'fields': ('utilizador', 'perfil', 'ativo')
        }),
    )

    @admin.display(description='Ativo')
    def badge_ativo(self, obj):
        if obj.ativo:
            return format_html(
                '<span style="color:{};font-weight:bold;">✔ Sim</span>',
                '#2e7d32'
            )
        return format_html(
            '<span style="color:{};font-weight:bold;">✘ Não</span>',
            '#c62828'
        )


# =============================================================================
# CATEGORIA
# =============================================================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display  = ('categoria', 'badge_ativo')
    list_filter   = ('ativo',)
    search_fields = ('categoria',)
    ordering      = ('categoria',)

    @admin.display(description='Ativa')
    def badge_ativo(self, obj):
        if obj.ativo:
            return format_html(
                '<span style="color:{};font-weight:bold;">✔ Sim</span>',
                '#2e7d32'
            )
        return format_html(
            '<span style="color:{};font-weight:bold;">✘ Não</span>',
            '#c62828'
        )


# =============================================================================
# FORNECEDOR
# =============================================================================

@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display  = ('fornecedor', 'telefone', 'email', 'badge_qualificado', 'badge_status')
    list_filter   = ('status', 'fornecedor_qualificado')
    search_fields = ('fornecedor', 'email', 'telefone')
    ordering      = ('fornecedor',)

    fieldsets = (
        ('Dados do Fornecedor', {
            'fields': ('fornecedor', 'telefone', 'email', 'endereco')
        }),
        ('Estado', {
            'fields': ('status', 'fornecedor_qualificado')
        }),
    )

    @admin.display(description='Qualificado')
    def badge_qualificado(self, obj):
        if obj.fornecedor_qualificado:
            return format_html(
                '<span style="color:{};font-weight:bold;">★ Sim</span>',
                '#1565c0'
            )
        return format_html(
            '<span style="color:{};">— Não</span>',
            '#888888'
        )

    @admin.display(description='Ativo')
    def badge_status(self, obj):
        if obj.status:
            return format_html(
                '<span style="color:{};font-weight:bold;">✔ Sim</span>',
                '#2e7d32'
            )
        return format_html(
            '<span style="color:{};font-weight:bold;">✘ Não</span>',
            '#c62828'
        )


# =============================================================================
# PRODUTO
# =============================================================================

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display    = ('codigo', 'produto', 'categoria', 'fornecedor',
                       'unidade', 'estoque_atual', 'estoque_minimo',
                       'badge_alerta', 'badge_ativo')
    list_filter     = ('categoria', 'fornecedor', 'unidade', 'ativo')
    search_fields   = ('codigo', 'produto')
    ordering        = ('produto',)
    readonly_fields = ('estoque_atual', 'create_at', 'update_at')

    fieldsets = (
        ('Identificação', {
            'fields': ('codigo', 'produto', 'categoria', 'fornecedor', 'unidade', 'ativo')
        }),
        ('Estoque', {
            'fields': ('estoque_atual', 'estoque_minimo', 'custo_medio')
        }),
        ('Auditoria', {
            'classes': ('collapse',),
            'fields': ('create_at', 'update_at')
        }),
    )

    @admin.display(description='Alerta')
    def badge_alerta(self, obj):
        if obj.abaixo_do_minimo:
            return format_html(
                '<span style="background:{};color:{};padding:2px 8px;'
                'border-radius:4px;font-size:11px;font-weight:bold;">⚠ Abaixo do mínimo</span>',
                '#c62828', '#ffffff'
            )
        return format_html(
            '<span style="color:{};">✔ OK</span>',
            '#2e7d32'
        )

    @admin.display(description='Ativo')
    def badge_ativo(self, obj):
        if obj.ativo:
            return format_html(
                '<span style="color:{};font-weight:bold;">✔ Sim</span>',
                '#2e7d32'
            )
        return format_html(
            '<span style="color:{};font-weight:bold;">✘ Não</span>',
            '#c62828'
        )


# =============================================================================
# MOVIMENTAÇÃO
# =============================================================================

@admin.register(Movimentacao)
class MovimentacaoAdmin(admin.ModelAdmin):
    list_display    = ('data_movimentacao', 'badge_tipo', 'produto',
                       'quantidade', 'valor_unitario', 'valor_total',
                       'utilizador', 'fornecedor')
    list_filter     = ('tipo_movimentacao', 'produto', 'utilizador', 'data_movimentacao')
    search_fields   = ('produto__produto', 'produto__codigo', 'observacao')
    ordering        = ('-data_movimentacao',)
    readonly_fields = ('valor_total', 'create_at', 'update_at')
    date_hierarchy  = 'data_movimentacao'

    fieldsets = (
        ('Movimentação', {
            'fields': ('tipo_movimentacao', 'produto', 'fornecedor',
                       'quantidade', 'valor_unitario', 'valor_total')
        }),
        ('Responsável e Data', {
            'fields': ('utilizador', 'data_movimentacao', 'observacao')
        }),
        ('Auditoria', {
            'classes': ('collapse',),
            'fields': ('create_at', 'update_at')
        }),
        ('Rectificação', {
            'classes': ('collapse',),
            'fields': ('rectificada', 'motivo_rectificacao', 'movimentacao_origem')
        }),
    )

    @admin.display(description='Tipo')
    def badge_tipo(self, obj):
        cores = {
            'ENTRADA': ('#1b5e20', '#e8f5e9', '↑ Entrada'),
            'SAIDA':   ('#b71c1c', '#ffebee', '↓ Saída'),
            'PERDA':   ('#e65100', '#fff3e0', '✘ Perda'),
        }
        cor_texto, cor_fundo, label = cores.get(
            obj.tipo_movimentacao, ('#333333', '#eeeeee', obj.tipo_movimentacao)
        )
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
            cor_fundo, cor_texto, label
        )

    @admin.register(LoteEstoque)
    class LoteEstoqueAdmin(admin.ModelAdmin):
        list_display  = ('produto', 'quantidade_inicial', 'quantidade_restante',
                        'valor_unitario', 'data_entrada', 'esgotado')
        list_filter   = ('produto', 'esgotado')
        ordering      = ('produto', 'data_entrada')
        readonly_fields = ('create_at',)

# =============================================================================
# ITEM DE INVENTÁRIO — inline dentro do Inventário
# =============================================================================

class ItemInventarioInline(admin.TabularInline):
    model           = ItemInventario
    extra           = 1
    readonly_fields = ('diferenca', 'create_at')
    fields          = ('produto', 'saldo_sistema', 'saldo_fisico', 'diferenca', 'observacao')

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.concluido:
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields


# =============================================================================
# INVENTÁRIO
# =============================================================================

@admin.register(Inventario)
class InventarioAdmin(admin.ModelAdmin):
    list_display    = ('data_inventario', 'utilizador', 'badge_concluido',
                       'total_itens', 'create_at')
    list_filter     = ('concluido', 'utilizador', 'data_inventario')
    search_fields   = ('observacao', 'utilizador__utilizador')
    ordering        = ('-data_inventario',)
    readonly_fields = ('create_at', 'update_at')
    inlines         = [ItemInventarioInline]
    date_hierarchy  = 'data_inventario'

    fieldsets = (
        ('Inventário', {
            'fields': ('utilizador', 'data_inventario', 'concluido', 'observacao')
        }),
        ('Auditoria', {
            'classes': ('collapse',),
            'fields': ('create_at', 'update_at')
        }),
    )

    @admin.display(description='Estado')
    def badge_concluido(self, obj):
        if obj.concluido:
            return format_html(
                '<span style="background:{};color:{};padding:2px 8px;'
                'border-radius:4px;font-size:11px;font-weight:bold;">✔ Concluído</span>',
                '#1b5e20', '#ffffff'
            )
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:bold;">⏳ Em curso</span>',
            '#e65100', '#ffffff'
        )

    @admin.display(description='Nº de itens')
    def total_itens(self, obj):
        return obj.itens.count()


# =============================================================================
# LOG — apenas leitura, sem adição ou eliminação
# =============================================================================

@admin.register(Log)
class LogAdmin(admin.ModelAdmin):
    list_display    = ('data_log', 'utilizador', 'badge_acao',
                       'tabela_afetada', 'id_registro', 'ip_address')
    list_filter     = ('acao', 'tabela_afetada', 'utilizador')
    search_fields   = ('tabela_afetada', 'utilizador__utilizador', 'ip_address')
    ordering        = ('-data_log',)
    date_hierarchy  = 'data_log'

    readonly_fields = ('utilizador', 'acao', 'tabela_afetada', 'id_registro',
                       'dados_antes', 'dados_depois', 'data_log', 'ip_address')

    fieldsets = (
        ('Ação', {
            'fields': ('utilizador', 'acao', 'tabela_afetada', 'id_registro', 'data_log', 'ip_address')
        }),
        ('Detalhe da Alteração', {
            'fields': ('dados_antes', 'dados_depois')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Ação')
    def badge_acao(self, obj):
        cores = {
            'CRIACAO':  ('#1b5e20', '#e8f5e9', '✚ Criação'),
            'EDICAO':   ('#1565c0', '#e3f2fd', '✎ Edição'),
            'EXCLUSAO': ('#b71c1c', '#ffebee', '✘ Exclusão'),
        }
        cor_texto, cor_fundo, label = cores.get(
            obj.acao, ('#333333', '#eeeeee', obj.acao)
        )
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;'
            'border-radius:4px;font-size:11px;font-weight:bold;">{}</span>',
            cor_fundo, cor_texto, label
        )