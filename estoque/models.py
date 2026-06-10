from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal


# =============================================================================
# UTILIZADOR
# Estende o AbstractUser do Django — herda automaticamente:
# username, password (hash seguro), email, is_active, is_staff, etc.
# =============================================================================

class Utilizador(AbstractUser):

    class Perfil(models.TextChoices):
        ADMIN       = 'ADMIN',      'Administrador'
        FUNCIONARIO = 'FUNCIONARIO', 'Funcionário'

    utilizador  = models.CharField('Nome completo', max_length=150)
    perfil      = models.CharField('Perfil', max_length=20,
                                   choices=Perfil.choices,
                                   default=Perfil.FUNCIONARIO)
    ativo       = models.BooleanField('Ativo', default=True)
    create_at   = models.DateTimeField('Criado em', auto_now_add=True)
    update_at   = models.DateTimeField('Atualizado em', auto_now=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='utilizador_set',
        blank=True,
        verbose_name='Grupos'
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='utilizador_set',
        blank=True,
        verbose_name='Permissões'
    )

    class Meta:
        verbose_name        = 'Utilizador'
        verbose_name_plural = 'Utilizadores'
        ordering            = ['utilizador']

    def __str__(self):
        return f'{self.utilizador} ({self.get_perfil_display()})'


# =============================================================================
# CATEGORIA
# Classifica os produtos (ex.: Carnes, Bebidas, Laticínios)
# =============================================================================

class Categoria(models.Model):
    categoria = models.CharField('Categoria', max_length=100, unique=True)
    ativo     = models.BooleanField('Ativa', default=True)

    class Meta:
        verbose_name        = 'Categoria'
        verbose_name_plural = 'Categorias'
        ordering            = ['categoria']

    def __str__(self):
        return self.categoria


# =============================================================================
# FORNECEDOR
# =============================================================================

class Fornecedor(models.Model):
    fornecedor              = models.CharField('Nome', max_length=150)
    telefone                = models.CharField('Telefone', max_length=30, blank=True)
    email                   = models.EmailField('E-mail', max_length=100, blank=True)
    endereco                = models.CharField('Endereço', max_length=255, blank=True)
    status                  = models.BooleanField('Ativo', default=True)
    fornecedor_qualificado  = models.BooleanField('Fornecedor qualificado', default=False)
    create_at               = models.DateTimeField('Criado em', auto_now_add=True)
    update_at               = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name        = 'Fornecedor'
        verbose_name_plural = 'Fornecedores'
        ordering            = ['fornecedor']

    def __str__(self):
        return self.fornecedor


# =============================================================================
# PRODUTO
# Entidade central do sistema.
# O campo estoque_atual é atualizado automaticamente via signal (ver abaixo).
# =============================================================================

class Produto(models.Model):

    class Unidade(models.TextChoices):
        UNIDADE  = 'UN',  'Unidade'
        KILO     = 'KG',  'Quilograma'
        LITRO    = 'LT',  'Litro'
        CAIXA    = 'CX',  'Caixa'
        PACOTE   = 'PC',  'Pacote'

    codigo          = models.CharField('Código', max_length=30, unique=True)
    produto         = models.CharField('Nome do produto', max_length=150)
    categoria       = models.ForeignKey(Categoria, on_delete=models.PROTECT,
                                        verbose_name='Categoria',
                                        related_name='produtos')
    fornecedor      = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL,
                                    verbose_name='Fornecedor',
                                    related_name='produtos',
                                    null=True, blank=True)
    unidade         = models.CharField('Unidade de medida', max_length=5,
                                       choices=Unidade.choices,
                                       default=Unidade.UNIDADE)
    estoque_atual   = models.DecimalField('Estoque atual', max_digits=10,
                                          decimal_places=2, default=Decimal('0.00'))
    estoque_minimo  = models.DecimalField('Estoque mínimo', max_digits=10,
                                          decimal_places=2, default=Decimal('0.00'))
    custo_medio     = models.DecimalField('Custo médio', max_digits=10,
                                          decimal_places=2, default=Decimal('0.00'),
                                          null=True, blank=True)
    ativo           = models.BooleanField('Ativo', default=True)
    create_at       = models.DateTimeField('Criado em', auto_now_add=True)
    update_at       = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name        = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering            = ['produto']

    def __str__(self):
        return f'{self.codigo} — {self.produto}'

    @property
    def abaixo_do_minimo(self):
        """Retorna True se o estoque atual estiver abaixo do mínimo."""
        return self.estoque_atual <= self.estoque_minimo

class LoteEstoque(models.Model):
    """
    Regista cada lote de entrada de um produto.
    Usado pelo sistema PEPS para controlar a ordem de consumo.
    O operador nunca interage directamente com esta tabela.
    """
    produto              = models.ForeignKey(
                               Produto,
                               on_delete=models.PROTECT,
                               verbose_name='Produto',
                               related_name='lotes'
                           )
    movimentacao_origem  = models.ForeignKey(
                               'Movimentacao',
                               on_delete=models.PROTECT,
                               verbose_name='Movimentação de origem',
                               related_name='lotes_criados',
                               help_text='Entrada que criou este lote'
                           )
    quantidade_inicial   = models.DecimalField(
                               'Quantidade inicial', max_digits=10, decimal_places=3
                           )
    quantidade_restante  = models.DecimalField(
                               'Quantidade restante', max_digits=10, decimal_places=3
                           )
    valor_unitario       = models.DecimalField(
                               'Valor unitário', max_digits=10, decimal_places=2
                           )
    data_entrada         = models.DateTimeField(
                               'Data de entrada', default=timezone.now
                           )
    esgotado             = models.BooleanField(
                               'Esgotado', default=False
                           )
    create_at            = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name        = 'Lote de Estoque'
        verbose_name_plural = 'Lotes de Estoque'
        ordering            = ['produto', 'data_entrada']  # PEPS — mais antigo primeiro

    def __str__(self):
        return (
            f'{self.produto.produto} | '
            f'Lote {self.pk} | '
            f'{self.quantidade_restante}/{self.quantidade_inicial} '
            f'{self.produto.get_unidade_display()} | '
            f'{self.valor_unitario}€'
        )


# =============================================================================
# MOVIMENTAÇÃO
# Regista entradas, saídas e perdas de produtos.
# Após cada save(), o signal atualiza o estoque_atual do produto.
# =============================================================================

class Movimentacao(models.Model):

    class Tipo(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SAIDA   = 'SAIDA',   'Saída'
        PERDA   = 'PERDA',   'Perda'

    utilizador          = models.ForeignKey(Utilizador, on_delete=models.PROTECT,
                                            verbose_name='Utilizador',
                                            related_name='movimentacoes')
    produto             = models.ForeignKey(Produto, on_delete=models.PROTECT,
                                            verbose_name='Produto',
                                            related_name='movimentacoes')
    # Fornecedor é opcional — aplicável apenas nas entradas
    fornecedor          = models.ForeignKey(Fornecedor, on_delete=models.SET_NULL,
                                            verbose_name='Fornecedor',
                                            related_name='movimentacoes',
                                            null=True, blank=True)
    tipo_movimentacao   = models.CharField('Tipo', max_length=10,
                                           choices=Tipo.choices)
    quantidade          = models.DecimalField('Quantidade', max_digits=10,
                                              decimal_places=2)
    valor_unitario      = models.DecimalField('Valor unitário', max_digits=10,
                                              decimal_places=2, default=Decimal('0.00'))
    valor_total         = models.DecimalField('Valor total', max_digits=10,
                                              decimal_places=2, default=Decimal('0.00'),
                                              editable=False)  # calculado no save()
    rectificada         = models.BooleanField('Rectificada', default=False)
    motivo_rectificacao = models.TextField('Motivo da rectificação', blank=True)
    movimentacao_origem = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='estornos',
        verbose_name='Movimentação de origem',
        help_text='Preenchido automaticamente nos estornos'
    )
    observacao          = models.TextField('Observação', blank=True)
    data_movimentacao   = models.DateTimeField('Data', default=timezone.now)
    create_at           = models.DateTimeField('Criado em', auto_now_add=True)
    update_at           = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name        = 'Movimentação'
        verbose_name_plural = 'Movimentações'
        ordering            = ['-data_movimentacao']

    def save(self, *args, **kwargs):
        # valor_total é sempre calculado — nunca inserido manualmente
        self.valor_total = self.quantidade * self.valor_unitario
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.tipo_movimentacao} | {self.produto} | {self.quantidade} {self.produto.unidade}'


# =============================================================================
# SIGNAL — Atualiza o estoque_atual do produto após cada movimentação
# Executado automaticamente pelo Django após qualquer save() em Movimentacao.
# =============================================================================

@receiver(post_save, sender=Movimentacao)
def atualizar_estoque(sender, instance, **kwargs):
    """
    Signal que:
    1. Se for ENTRADA — cria um novo LoteEstoque
    2. Se for SAIDA ou PERDA — consome lotes pela ordem PEPS
    3. Actualiza o estoque_atual do produto
    """
    from .models import LoteEstoque

    produto = instance.produto

    # --- ENTRADA: cria novo lote ---
    if instance.tipo_movimentacao == Movimentacao.Tipo.ENTRADA:
        # Só cria lote se não for estorno nem rectificada
        if (not instance.rectificada and
                not instance.observacao.startswith('ESTORNO AUTOMÁTICO')):
            # Verifica se o lote já foi criado (evita duplicação no signal)
            if not LoteEstoque.objects.filter(movimentacao_origem=instance).exists():
                LoteEstoque.objects.create(
                    produto             = produto,
                    movimentacao_origem = instance,
                    quantidade_inicial  = instance.quantidade,
                    quantidade_restante = instance.quantidade,
                    valor_unitario      = instance.valor_unitario,
                    data_entrada        = instance.data_movimentacao,
                )

    # --- SAIDA ou PERDA: consome lotes PEPS ---
    elif instance.tipo_movimentacao in (
        Movimentacao.Tipo.SAIDA, Movimentacao.Tipo.PERDA
    ):
        if (not instance.rectificada and
                not instance.observacao.startswith('ESTORNO AUTOMÁTICO')):
            quantidade_a_consumir = instance.quantidade

            # Busca lotes disponíveis do mais antigo para o mais novo (PEPS)
            lotes = LoteEstoque.objects.filter(
                produto  = produto,
                esgotado = False,
            ).order_by('data_entrada')

            for lote in lotes:
                if quantidade_a_consumir <= Decimal('0.00'):
                    break

                if lote.quantidade_restante <= quantidade_a_consumir:
                    # Consome o lote inteiro
                    quantidade_a_consumir -= lote.quantidade_restante
                    lote.quantidade_restante = Decimal('0.00')
                    lote.esgotado            = True
                    lote.save()
                else:
                    # Consome parcialmente
                    lote.quantidade_restante -= quantidade_a_consumir
                    quantidade_a_consumir     = Decimal('0.00')
                    lote.save()

    # --- Recalcula estoque_atual a partir dos lotes activos ---
    from django.db.models import Sum as DjSum
    saldo = LoteEstoque.objects.filter(
        produto  = produto,
        esgotado = False,
    ).aggregate(
        total=DjSum('quantidade_restante')
    )['total'] or Decimal('0.00')

    Produto.objects.filter(pk=produto.pk).update(estoque_atual=saldo)


# =============================================================================
# INVENTÁRIO
# Cabeçalho de cada contagem física periódica.
# =============================================================================

class Inventario(models.Model):
    utilizador      = models.ForeignKey(Utilizador, on_delete=models.PROTECT,
                                        verbose_name='Responsável',
                                        related_name='inventarios')
    data_inventario = models.DateField('Data do inventário', default=timezone.now)
    concluido       = models.BooleanField('Concluído', default=False)
    acerto_aplicado = models.BooleanField('Acerto aplicado', default=False,
                                          help_text='Indica se o acerto de estoque já foi aplicado para este inventário.')
    observacao      = models.TextField('Observação', blank=True)
    create_at       = models.DateTimeField('Criado em', auto_now_add=True)
    update_at       = models.DateTimeField('Atualizado em', auto_now=True)

    class Meta:
        verbose_name        = 'Inventário'
        verbose_name_plural = 'Inventários'
        ordering            = ['-data_inventario']

    def __str__(self):
        status = 'Concluído' if self.concluido else 'Em curso'
        return f'Inventário {self.data_inventario} — {status}'


# =============================================================================
# ITEM DE INVENTÁRIO
# Detalha a contagem de cada produto num inventário.
# O campo diferenca é sempre calculado no save().
# =============================================================================

class ItemInventario(models.Model):
    inventario      = models.ForeignKey(Inventario, on_delete=models.CASCADE,
                                        verbose_name='Inventário',
                                        related_name='itens')
    produto         = models.ForeignKey(Produto, on_delete=models.PROTECT,
                                        verbose_name='Produto',
                                        related_name='itens_inventario')
    saldo_fisico    = models.DecimalField('Saldo físico (contagem)', max_digits=10,
                                          decimal_places=2)
    saldo_sistema   = models.DecimalField('Saldo sistema', max_digits=10,
                                          decimal_places=2)
    diferenca       = models.DecimalField('Diferença', max_digits=10,
                                          decimal_places=2, default=Decimal('0.00'),
                                          editable=False)  # calculado no save()
    
    observacao      = models.TextField('Observação', blank=True)
    create_at       = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name        = 'Item de Inventário'
        verbose_name_plural = 'Itens de Inventário'
        # Garante que o mesmo produto não aparece duas vezes no mesmo inventário
        unique_together     = [['inventario', 'produto']]

    def save(self, *args, **kwargs):
        # diferenca é sempre calculada — nunca inserida manualmente
        self.diferenca = self.saldo_fisico - self.saldo_sistema
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.produto} | Físico: {self.saldo_fisico} | Sistema: {self.saldo_sistema}'


# =============================================================================
# LOG
# Alimentado automaticamente pelo sistema — nunca pelo utilizador.
# Regista todas as ações de criação, edição e exclusão.
# =============================================================================

class Log(models.Model):

    class Acao(models.TextChoices):
        CRIACAO  = 'CRIACAO',  'Criação'
        EDICAO   = 'EDICAO',   'Edição'
        EXCLUSAO = 'EXCLUSAO', 'Exclusão'

    utilizador      = models.ForeignKey(Utilizador, on_delete=models.SET_NULL,
                                        verbose_name='Utilizador',
                                        related_name='logs',
                                        null=True, blank=True)
    acao            = models.CharField('Ação', max_length=10, choices=Acao.choices)
    tabela_afetada  = models.CharField('Tabela afetada', max_length=50)
    id_registro     = models.PositiveIntegerField('ID do registo')
    dados_antes     = models.TextField('Dados antes', blank=True)
    dados_depois    = models.TextField('Dados depois', blank=True)
    data_log        = models.DateTimeField('Data/hora', auto_now_add=True)
    ip_address      = models.GenericIPAddressField('Endereço IP', null=True, blank=True)

    class Meta:
        verbose_name        = 'Log'
        verbose_name_plural = 'Logs'
        ordering            = ['-data_log']

    def __str__(self):
        return f'{self.acao} | {self.tabela_afetada} #{self.id_registro} | {self.data_log:%d/%m/%Y %H:%M}'