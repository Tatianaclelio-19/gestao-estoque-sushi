from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q, Count, F, ExpressionWrapper, DecimalField
from django.db.models import OuterRef, Subquery
from django.db.models import Sum as DjSum
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from decimal import Decimal
from .models import (
    Produto, Movimentacao, Inventario, Fornecedor,
    Categoria, LoteEstoque, ItemInventario, Log
)



# AUTENTICAÇÃO

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.ativo:
                login(request, user)
                return redirect(request.GET.get('next', 'dashboard'))
            else:
                messages.error(request, 'A sua conta está desativada. Contacte o administrador.')
        else:
            messages.error(request, 'Utilizador ou password incorretos.')
    return render(request, 'estoque/login.html')


def logout_view(request):
    logout(request)
    messages.success(request, 'Sessão terminada com sucesso.')
    return redirect('login')



# DASHBOARD

@login_required(login_url='login')
def dashboard(request):
    hoje      = timezone.now()
    mes_atual = hoje.month
    ano_atual = hoje.year

    total_produtos     = Produto.objects.filter(ativo=True).count()
    total_fornecedores = Fornecedor.objects.filter(status=True).count()
    total_categorias   = Categoria.objects.filter(ativo=True).count()

    todos_produtos  = Produto.objects.filter(ativo=True).select_related('categoria')
    produtos_alerta = [p for p in todos_produtos if p.abaixo_do_minimo]
    total_alertas   = len(produtos_alerta)

    entradas_mes = Movimentacao.objects.filter(
        tipo_movimentacao=Movimentacao.Tipo.ENTRADA,
        data_movimentacao__month=mes_atual,
        data_movimentacao__year=ano_atual,
        rectificada=False
    ).exclude(
        observacao__startswith='ESTORNO AUTOMÁTICO'
    ).exclude(
        observacao__startswith='Acerto de inventário'
    ).count()

    saidas_mes = Movimentacao.objects.filter(
        tipo_movimentacao=Movimentacao.Tipo.SAIDA,
        data_movimentacao__month=mes_atual,
        data_movimentacao__year=ano_atual,
        rectificada=False
    ).exclude(
        observacao__startswith='ESTORNO AUTOMÁTICO'
    ).exclude(
        observacao__startswith='Acerto de inventário'
    ).count()

    perdas_mes = Movimentacao.objects.filter(
        tipo_movimentacao=Movimentacao.Tipo.PERDA,
        data_movimentacao__month=mes_atual,
        data_movimentacao__year=ano_atual,
        rectificada=False
    ).exclude(
        observacao__startswith='ESTORNO AUTOMÁTICO'
        ).exclude(
        observacao__startswith='Acerto de inventário'
    ).count()

    ultimas_movimentacoes = Movimentacao.objects.select_related(
        'produto', 'utilizador'
    ).order_by('-data_movimentacao')[:8]

    context = {
        'total_produtos':        total_produtos,
        'total_fornecedores':    total_fornecedores,
        'total_categorias':      total_categorias,
        'total_alertas':         total_alertas,
        'produtos_alerta':       produtos_alerta[:5],
        'entradas_mes':          entradas_mes,
        'saidas_mes':            saidas_mes,
        'perdas_mes':            perdas_mes,
        'ultimas_movimentacoes': ultimas_movimentacoes,
        'mes_atual':             hoje.strftime('%B de %Y'),
    }
    return render(request, 'estoque/dashboard.html', context)



# CATEGORIAS

@login_required(login_url='login')
def categoria_lista(request):
    pesquisa   = request.GET.get('q', '')
    categorias = Categoria.objects.all().order_by('categoria')
    if pesquisa:
        categorias = categorias.filter(categoria__icontains=pesquisa)
    return render(request, 'estoque/categoria_lista.html', {
        'categorias': categorias,
        'pesquisa':   pesquisa,
    })


@login_required(login_url='login')
def categoria_criar(request):
    if request.method == 'POST':
        nome = request.POST.get('categoria', '').strip()
        ativo = request.POST.get('ativo') == 'on'
        if not nome:
            messages.error(request, 'O nome da categoria é obrigatório.')
            return render(request, 'estoque/categoria_form.html', {'acao': 'Nova'})
        if Categoria.objects.filter(categoria__iexact=nome).exists():
            messages.error(request, f'Já existe uma categoria com o nome "{nome}".')
            return render(request, 'estoque/categoria_form.html', {
                'acao': 'Nova', 'valores': {'categoria': nome}
            })
        Categoria.objects.create(categoria=nome, ativo=ativo)
        messages.success(request, f'Categoria "{nome}" criada com sucesso!')
        return redirect('categoria_lista')
    return render(request, 'estoque/categoria_form.html', {'acao': 'Nova'})


@login_required(login_url='login')
def categoria_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    if request.method == 'POST':
        nome = request.POST.get('categoria', '').strip()
        ativo = request.POST.get('ativo') == 'on'
        if not nome:
            messages.error(request, 'O nome da categoria é obrigatório.')
            return render(request, 'estoque/categoria_form.html', {
                'acao': 'Editar', 'categoria': categoria
            })
        if Categoria.objects.filter(categoria__iexact=nome).exclude(pk=pk).exists():
            messages.error(request, f'Já existe uma categoria com o nome "{nome}".')
            return render(request, 'estoque/categoria_form.html', {
                'acao': 'Editar', 'categoria': categoria
            })
        categoria.categoria = nome
        categoria.ativo      = ativo
        categoria.save()
        messages.success(request, f'Categoria "{nome}" atualizada com sucesso!')
        return redirect('categoria_lista')
    return render(request, 'estoque/categoria_form.html', {
        'acao': 'Editar', 'categoria': categoria
    })


@login_required(login_url='login')
def categoria_toggle_ativo(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    categoria.ativo = not categoria.ativo
    categoria.save()
    estado = 'ativada' if categoria.ativo else 'desativada'
    messages.success(request, f'Categoria "{categoria.categoria}" {estado} com sucesso!')
    return redirect('categoria_lista')



# FORNECEDORES

@login_required(login_url='login')
def fornecedor_lista(request):
    pesquisa     = request.GET.get('q', '')
    filtro_ativo = request.GET.get('ativo', '')
    fornecedores = Fornecedor.objects.all().order_by('fornecedor')
    if pesquisa:
        fornecedores = fornecedores.filter(fornecedor__icontains=pesquisa)
    if filtro_ativo == '1':
        fornecedores = fornecedores.filter(status=True)
    elif filtro_ativo == '0':
        fornecedores = fornecedores.filter(status=False)
    return render(request, 'estoque/fornecedor_lista.html', {
        'fornecedores': fornecedores,
        'pesquisa':     pesquisa,
        'filtro_ativo': filtro_ativo,
    })


@login_required(login_url='login')
def fornecedor_criar(request):
    if request.method == 'POST':
        dados = {
            'fornecedor':             request.POST.get('fornecedor', '').strip(),
            'telefone':               request.POST.get('telefone', '').strip(),
            'email':                  request.POST.get('email', '').strip(),
            'endereco':               request.POST.get('endereco', '').strip(),
            'status':                 request.POST.get('status') == 'on',
            'fornecedor_qualificado': request.POST.get('fornecedor_qualificado') == 'on',
        }
        if not dados['fornecedor']:
            messages.error(request, 'O nome do fornecedor é obrigatório.')
            return render(request, 'estoque/fornecedor_form.html', {
                'acao': 'Novo', 'valores': dados
            })
        Fornecedor.objects.create(**dados)
        messages.success(request, f'Fornecedor "{dados["fornecedor"]}" criado com sucesso!')
        return redirect('fornecedor_lista')
    return render(request, 'estoque/fornecedor_form.html', {'acao': 'Novo'})


@login_required(login_url='login')
def fornecedor_editar(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    if request.method == 'POST':
        nome = request.POST.get('fornecedor', '').strip()
        if not nome:
            messages.error(request, 'O nome do fornecedor é obrigatório.')
            return render(request, 'estoque/fornecedor_form.html', {
                'acao': 'Editar', 'fornecedor': fornecedor
            })
        fornecedor.fornecedor             = nome
        fornecedor.telefone               = request.POST.get('telefone', '').strip()
        fornecedor.email                  = request.POST.get('email', '').strip()
        fornecedor.endereco               = request.POST.get('endereco', '').strip()
        fornecedor.status                 = request.POST.get('status') == 'on'
        fornecedor.fornecedor_qualificado = request.POST.get('fornecedor_qualificado') == 'on'
        fornecedor.save()
        messages.success(request, f'Fornecedor "{nome}" atualizado com sucesso!')
        return redirect('fornecedor_lista')
    return render(request, 'estoque/fornecedor_form.html', {
        'acao': 'Editar', 'fornecedor': fornecedor
    })


@login_required(login_url='login')
def fornecedor_toggle_ativo(request, pk):
    fornecedor = get_object_or_404(Fornecedor, pk=pk)
    fornecedor.status = not fornecedor.status
    fornecedor.save()
    estado = 'ativado' if fornecedor.status else 'desativado'
    messages.success(request, f'Fornecedor "{fornecedor.fornecedor}" {estado} com sucesso!')
    return redirect('fornecedor_lista')



# PRODUTOS

@login_required(login_url='login')
def produto_lista(request):
    """Lista produtos com pesquisa e filtros por categoria, fornecedor e estado."""
    pesquisa         = request.GET.get('q', '')
    filtro_categoria = request.GET.get('categoria', '')
    filtro_fornecedor = request.GET.get('fornecedor', '')
    filtro_ativo     = request.GET.get('ativo', '1')  # por defeito mostra só ativos
    filtro_alerta    = request.GET.get('alerta', '')

    produtos = Produto.objects.select_related('categoria', 'fornecedor').order_by('produto')

    if pesquisa:
        produtos = produtos.filter(produto__icontains=pesquisa) | \
                   produtos.filter(codigo__icontains=pesquisa)
        produtos = produtos.distinct()

    if filtro_categoria:
        produtos = produtos.filter(categoria__pk=filtro_categoria)

    if filtro_fornecedor:
        produtos = produtos.filter(fornecedor__pk=filtro_fornecedor)

    if filtro_ativo == '1':
        produtos = produtos.filter(ativo=True)
    elif filtro_ativo == '0':
        produtos = produtos.filter(ativo=False)

    # Filtro de alertas — aplica a property depois do queryset
    if filtro_alerta == '1':
        produtos = [p for p in produtos if p.abaixo_do_minimo]
    else:
        produtos = list(produtos)

    categorias   = Categoria.objects.filter(ativo=True).order_by('categoria')
    fornecedores = Fornecedor.objects.filter(status=True).order_by('fornecedor')

    return render(request, 'estoque/produto_lista.html', {
        'produtos':          produtos,
        'categorias':        categorias,
        'fornecedores':      fornecedores,
        'pesquisa':          pesquisa,
        'filtro_categoria':  filtro_categoria,
        'filtro_fornecedor': filtro_fornecedor,
        'filtro_ativo':      filtro_ativo,
        'filtro_alerta':     filtro_alerta,
        'total':             len(produtos),
    })


@login_required(login_url='login')
def produto_criar(request):
    """Formulário para criar novo produto."""
    categorias   = Categoria.objects.filter(ativo=True).order_by('categoria')
    fornecedores = Fornecedor.objects.filter(status=True).order_by('fornecedor')

    if request.method == 'POST':
        codigo    = request.POST.get('codigo', '').strip()
        nome      = request.POST.get('produto', '').strip()
        categoria = request.POST.get('categoria', '')
        fornecedor = request.POST.get('fornecedor', '')
        unidade   = request.POST.get('unidade', '')
        estoque_minimo = request.POST.get('estoque_minimo', '0')
        custo_medio    = request.POST.get('custo_medio', '0')
        ativo          = request.POST.get('ativo') == 'on'

        erros = []
        if not codigo:    erros.append('O código do produto é obrigatório.')
        if not nome:      erros.append('O nome do produto é obrigatório.')
        if not categoria: erros.append('A categoria é obrigatória.')
        if not unidade:   erros.append('A unidade de medida é obrigatória.')
        if Produto.objects.filter(codigo__iexact=codigo).exists():
            erros.append(f'Já existe um produto com o código "{codigo}".')

        if erros:
            for erro in erros:
                messages.error(request, erro)
            return render(request, 'estoque/produto_form.html', {
                'acao':        'Novo',
                'categorias':  categorias,
                'fornecedores': fornecedores,
                'valores':     request.POST,
            })

        Produto.objects.create(
            codigo         = codigo, 
            produto        = nome, 
            categoria_id   = categoria,
            unidade        = unidade, 
            estoque_minimo = estoque_minimo, 
            ativo          = ativo,
        )
        messages.success(request, f'Produto "{nome}" criado com sucesso!')
        return redirect('produto_lista')

    return render(request, 'estoque/produto_form.html', {
        'acao':        'Novo',
        'categorias':  categorias,
        'fornecedores': fornecedores,
    })


@login_required(login_url='login')
def produto_editar(request, pk):
    """Formulário para editar produto existente."""
    produto      = get_object_or_404(Produto, pk=pk)
    categorias   = Categoria.objects.filter(ativo=True).order_by('categoria')
    fornecedores = Fornecedor.objects.filter(status=True).order_by('fornecedor')

    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        nome   = request.POST.get('produto', '').strip()

        erros = []
        if not codigo:
            erros.append('O código do produto é obrigatório.')
        if not nome:
            erros.append('O nome do produto é obrigatório.')
        if not request.POST.get('categoria'):
            erros.append('A categoria é obrigatória.')
        if Produto.objects.filter(codigo__iexact=codigo).exclude(pk=pk).exists():
            erros.append(f'Já existe outro produto com o código "{codigo}".')

        if erros:
            for erro in erros:
                messages.error(request, erro)
            return render(request, 'estoque/produto_form.html', {
                'acao':        'Editar',
                'produto':     produto,
                'categorias':  categorias,
                'fornecedores': fornecedores,
                'valores':     request.POST,
            })

        produto.codigo        = codigo
        produto.produto       = nome
        produto.categoria_id  = request.POST.get('categoria')
        produto.unidade       = request.POST.get('unidade')
        produto.estoque_minimo = request.POST.get('estoque_minimo', '0')
        produto.ativo         = request.POST.get('ativo') == 'on'
        produto.save()

        messages.success(request, f'Produto "{nome}" atualizado com sucesso!')
        return redirect('produto_lista')

    return render(request, 'estoque/produto_form.html', {
        'acao':        'Editar',
        'produto':     produto,
        'categorias':  categorias,
        'fornecedores': fornecedores,
    })


@login_required(login_url='login')
def produto_toggle_ativo(request, pk):
    """Ativa ou desativa um produto sem o eliminar."""
    produto = get_object_or_404(Produto, pk=pk)
    produto.ativo = not produto.ativo
    produto.save()
    estado = 'ativado' if produto.ativo else 'desativado'
    messages.success(request, f'Produto "{produto.produto}" {estado} com sucesso!')
    return redirect('produto_lista')


@login_required(login_url='login')
def movimentacao_lista(request):
    """Lista movimentações com filtros por tipo, produto e período."""
    pesquisa    = request.GET.get('q', '')
    filtro_tipo = request.GET.get('tipo', '')
    filtro_mes  = request.GET.get('mes', '')
    filtro_ano  = request.GET.get('ano', str(timezone.now().year))

    movimentacoes = Movimentacao.objects.select_related(
        'produto', 'utilizador', 'fornecedor'
    ).order_by('-data_movimentacao')

    # Queryset limpo só para os totais — sem rectificadas nem estornos
    movimentacoes_reais = movimentacoes.filter(
        rectificada=False
    ).exclude(
        observacao__startswith='ESTORNO AUTOMÁTICO'
    ).exclude(
        observacao__startswith='Acerto de inventário'
    )

    if pesquisa:
        movimentacoes = movimentacoes.filter(
            Q(produto__produto__icontains=pesquisa) |
            Q(produto__codigo__icontains=pesquisa)
        )
    if filtro_tipo:
        movimentacoes = movimentacoes.filter(tipo_movimentacao=filtro_tipo)
    if filtro_ano:
        movimentacoes = movimentacoes.filter(data_movimentacao__year=filtro_ano)
    if filtro_mes:
        movimentacoes = movimentacoes.filter(data_movimentacao__month=filtro_mes)

    # Totais do período filtrado
    totais = movimentacoes_reais.aggregate(
        total_entradas=Count('pk', filter=Q(tipo_movimentacao='ENTRADA')),
        total_saidas=Count('pk',   filter=Q(tipo_movimentacao='SAIDA')),
        total_perdas=Count('pk',   filter=Q(tipo_movimentacao='PERDA')),
        valor_total=Sum('valor_total'),
    )

    # Anos disponíveis para o filtro
    anos_qs = Movimentacao.objects.dates('data_movimentacao', 'year', order='DESC')
    anos    = [d.year for d in anos_qs] or [timezone.now().year]

    meses = [
        (1,'Janeiro'),(2,'Fevereiro'),(3,'Março'),(4,'Abril'),
        (5,'Maio'),(6,'Junho'),(7,'Julho'),(8,'Agosto'),
        (9,'Setembro'),(10,'Outubro'),(11,'Novembro'),(12,'Dezembro'),
    ]

    return render(request, 'estoque/movimentacao_lista.html', {
        'movimentacoes': movimentacoes[:100],
        'pesquisa':      pesquisa,
        'filtro_tipo':   filtro_tipo,
        'filtro_mes':    filtro_mes,
        'filtro_ano':    filtro_ano,
        'totais':        totais,
        'anos':          anos,
        'meses':         meses,
        'total':         movimentacoes.count(),
    })


@login_required(login_url='login')
def movimentacao_criar(request):
    """
    Regista uma nova movimentação.
    Validações:
      - Quantidade deve ser positiva
      - SAIDA e PERDA: verifica saldo disponível
      - ENTRADA: fornecedor obrigatório
    """
    produtos     = Produto.objects.filter(ativo=True).order_by('produto')
    fornecedores = Fornecedor.objects.filter(status=True).order_by('fornecedor')

    if request.method == 'POST':
        tipo           = request.POST.get('tipo_movimentacao', '')
        produto_id     = request.POST.get('produto', '')
        fornecedor_id  = request.POST.get('fornecedor', '') or None
        quantidade_str = request.POST.get('quantidade', '')
        valor_unitario = request.POST.get('valor_unitario', '0') or '0'
        observacao     = request.POST.get('observacao', '').strip()

        erros = []

        if not tipo:
            erros.append('O tipo de movimentação é obrigatório.')
        if not produto_id:
            erros.append('O produto é obrigatório.')

        quantidade_decimal = Decimal('0')
        if not quantidade_str:
            erros.append('A quantidade é obrigatória.')
        else:
            try:
                quantidade_decimal = Decimal(quantidade_str)
                if quantidade_decimal <= 0:
                    erros.append('A quantidade deve ser maior que zero.')
            except Exception:
                erros.append('Quantidade inválida — use apenas números.')

        if erros:
            for erro in erros:
                messages.error(request, erro)
            return render(request, 'estoque/movimentacao_form.html', {
                'produtos': produtos, 'fornecedores': fornecedores,
                'valores': request.POST,
            })

        produto = get_object_or_404(Produto, pk=produto_id)

        # Fornecedor obrigatório para entradas
        if tipo == 'ENTRADA' and not fornecedor_id:
            messages.error(request, 'O fornecedor é obrigatório para movimentações de entrada.')
            return render(request, 'estoque/movimentacao_form.html', {
                'produtos': produtos, 'fornecedores': fornecedores,
                'valores': request.POST,
            })

        # Saldo suficiente para saídas e perdas
        

            if tipo in ('SAIDA', 'PERDA'):
                saldo_disponivel = LoteEstoque.objects.filter(
                    produto=produto,
                    esgotado=False,
                ).aggregate(total=DjSum('quantidade_restante'))['total'] or Decimal('0.00')

                if quantidade_decimal > saldo_disponivel:
                    messages.error(
                        request,
                        f'Saldo insuficiente! Estoque disponível de '
                        f'"{produto.produto}" é '
                        f'{saldo_disponivel} {produto.get_unidade_display()}.'
                    )
                    return render(request, 'estoque/movimentacao_form.html', {
                        'produtos': produtos, 'fornecedores': fornecedores,
                        'valores': request.POST,
                    })

            return render(request, 'estoque/movimentacao_form.html', {
                'produtos': produtos, 'fornecedores': fornecedores,
                'valores': request.POST,
            })

        if tipo == 'ENTRADA':
            valor_unit = Decimal(valor_unitario) if valor_unitario else Decimal('0')
        else:
            # Para saída e perda usa sempre o custo médio do produto
            valor_unit = produto.custo_medio or Decimal('0')

        Movimentacao.objects.create(
            utilizador        = request.user,
            produto           = produto,
            fornecedor_id     = fornecedor_id,
            tipo_movimentacao = tipo,
            quantidade        = quantidade_decimal,
            valor_unitario    = valor_unit,
            observacao        = observacao,
            data_movimentacao = timezone.now(),
        )

        tipo_label = {'ENTRADA': 'Entrada', 'SAIDA': 'Saída', 'PERDA': 'Perda'}.get(tipo, tipo)
        messages.success(
            request,
            f'{tipo_label} de {quantidade_decimal} {produto.get_unidade_display()} '
            f'de "{produto.produto}" registada com sucesso!'
        )
        return redirect('movimentacao_lista')

    return render(request, 'estoque/movimentacao_form.html', {
        'produtos': produtos, 'fornecedores': fornecedores,
    })

@login_required(login_url='login')
def inventario_lista(request):
    """Lista todos os inventários com filtro de estado."""
    filtro_estado = request.GET.get('estado', '')
    inventarios   = Inventario.objects.select_related('utilizador').order_by('-data_inventario')

    if filtro_estado == '1':
        inventarios = inventarios.filter(concluido=True)
    elif filtro_estado == '0':
        inventarios = inventarios.filter(concluido=False)

    return render(request, 'estoque/inventario_lista.html', {
        'inventarios':   inventarios,
        'filtro_estado': filtro_estado,
    })


@login_required(login_url='login')
def inventario_criar(request):
    """
    Cria um novo inventário em aberto e pré-preenche
    os itens com todos os produtos ativos e os seus saldos atuais.
    """
    # Impede criar um novo inventário se já existe um em curso
    em_curso = Inventario.objects.filter(concluido=False).first()
    if em_curso:
        messages.warning(
            request,
            f'Já existe um inventário em curso desde {em_curso.data_inventario}. '
            f'Conclui-o antes de criar um novo.'
        )
        return redirect('inventario_detalhe', pk=em_curso.pk)

    if request.method == 'POST':
        observacao = request.POST.get('observacao', '').strip()

        inventario = Inventario.objects.create(
            utilizador      = request.user,
            data_inventario = timezone.now().date(),
            concluido       = False,
            observacao      = observacao,
        )

        # Pré-preenche os itens com todos os produtos ativos
        produtos = Produto.objects.filter(ativo=True).order_by('produto')
        itens = []
        for produto in produtos:
            itens.append(ItemInventario(
                inventario    = inventario,
                produto       = produto,
                saldo_sistema = produto.estoque_atual,
                saldo_fisico  = produto.estoque_atual,  # operador vai corrigir
                diferenca     = Decimal('0.00'),
            ))
        ItemInventario.objects.bulk_create(itens)

        messages.success(request, 'Inventário criado! Preenche os saldos físicos contados.')
        return redirect('inventario_detalhe', pk=inventario.pk)

    return render(request, 'estoque/inventario_criar.html')


@login_required(login_url='login')
def inventario_detalhe(request, pk):
    """
    Página de preenchimento do inventário.
    O operador insere o saldo físico contado para cada produto.
    Após submeter, a diferença é calculada automaticamente.
    """
    inventario = get_object_or_404(Inventario, pk=pk)
    itens      = inventario.itens.select_related('produto').order_by('produto__produto')

    if request.method == 'POST':
        # Inventário já concluído — não permite edição
        if inventario.concluido:
            messages.error(request, 'Este inventário já foi concluído e não pode ser alterado.')
            return redirect('inventario_detalhe', pk=pk)

        acao = request.POST.get('acao', '')

        # Guarda os saldos físicos inseridos
        for item in itens:
            campo = f'saldo_fisico_{item.pk}'
            valor = request.POST.get(campo, '').strip()
            try:
                item.saldo_fisico = Decimal(valor) if valor else item.saldo_sistema
                item.save()   # save() calcula a diferenca automaticamente
            except Exception:
                messages.error(request, f'Valor inválido para "{item.produto.produto}".')
                return redirect('inventario_detalhe', pk=pk)

        if acao == 'concluir':
            inventario.concluido = True
            inventario.save()
            messages.success(request, 'Inventário concluído com sucesso!')
            return redirect('inventario_lista')
        else:
            messages.success(request, 'Saldos guardados. Podes continuar a preencher.')
            return redirect('inventario_detalhe', pk=pk)

    # Estatísticas do inventário
    total_itens      = itens.count()
    itens_divergente = [i for i in itens if i.diferenca != 0]
    total_divergente = len(itens_divergente)

    return render(request, 'estoque/inventario_detalhe.html', {
        'inventario':       inventario,
        'itens':            itens,
        'total_itens':      total_itens,
        'total_divergente': total_divergente,
    })

    #Inventário

@login_required(login_url='login')
def inventario_concluir(request, pk):
    """Conclui um inventário em curso."""
    inventario = get_object_or_404(Inventario, pk=pk)

    if inventario.concluido:
        messages.warning(request, 'Este inventário já estava concluído.')
        return redirect('inventario_lista')

    inventario.concluido = True
    inventario.save()
    messages.success(request, f'Inventário de {inventario.data_inventario} concluído!')
    return redirect('inventario_lista')

@login_required(login_url='login')
def relatorios(request):
    """
    Página de relatórios gerenciais.
    Filtros: período (mês/ano) e categoria.
    Gera 4 blocos de informação:
      1. Resumo geral do período
      2. Movimentações por produto
      3. Produtos abaixo do mínimo
      4. Perdas do período
    """
    hoje      = timezone.now()
    mes       = int(request.GET.get('mes', hoje.month))
    ano       = int(request.GET.get('ano', hoje.year))
    categoria_id = request.GET.get('categoria', '')

    # --- Filtro base de movimentações do período ---
    movs = Movimentacao.objects.filter(
    data_movimentacao__month=mes,
    data_movimentacao__year=ano,
    rectificada=False,
).exclude(
    observacao__startswith='ESTORNO AUTOMÁTICO'
).exclude(
    observacao__startswith='Acerto de inventário'
).select_related('produto', 'produto__categoria', 'fornecedor', 'utilizador')

    if categoria_id:
        movs = movs.filter(produto__categoria__pk=categoria_id)

    # --- 1. Resumo geral ---
    resumo = movs.aggregate(
    total_entradas = Count('pk', filter=Q(tipo_movimentacao='ENTRADA')),
    total_saidas   = Count('pk', filter=Q(tipo_movimentacao='SAIDA')),
    total_perdas   = Count('pk', filter=Q(tipo_movimentacao='PERDA')),
    valor_entradas = Sum('valor_total', filter=Q(tipo_movimentacao='ENTRADA')),
    valor_saidas   = Sum('valor_total', filter=Q(tipo_movimentacao='SAIDA')),
    valor_perdas   = Sum('valor_total', filter=Q(tipo_movimentacao='PERDA')),
    )

    #---2.  Calcula valor PEPS por produto (lotes activos)
 
    lote_valor = LoteEstoque.objects.filter(
        produto=OuterRef('produto__pk'),
        esgotado=False,
    ).values('produto').annotate(
        total=DjSum(
            ExpressionWrapper(
                F('quantidade_restante') * F('valor_unitario'),
                output_field=DecimalField()
            )
        )
    ).values('total')

    # E passa no contexto:
    #     'valor_peps_por_produto': valor_peps_por_produto,
   
   
    # --- 3. Movimentações agrupadas por produto ---
 
    produtos_mov = (
    movs.values(
        'produto__pk',
        'produto__produto',
        'produto__codigo',
        'produto__categoria__categoria',
        'produto__unidade',
        'produto__estoque_atual',
        'produto__estoque_minimo',
        'produto__custo_medio',
    )
    .annotate(
        qtd_entradas = DjSum('quantidade', filter=Q(tipo_movimentacao='ENTRADA')),
        qtd_saidas   = DjSum('quantidade', filter=Q(tipo_movimentacao='SAIDA')),
        qtd_perdas   = DjSum('quantidade', filter=Q(tipo_movimentacao='PERDA')),
        val_total    = DjSum('valor_total'),
        n_movs       = Count('pk'),
    )
    .order_by('produto__produto')
    )

    # --- 4. Produtos abaixo do mínimo ---
    produtos_qs = Produto.objects.filter(ativo=True).select_related('categoria', 'fornecedor')
    if categoria_id:
        produtos_qs = produtos_qs.filter(categoria__pk=categoria_id)
    produtos_alerta = [p for p in produtos_qs if p.abaixo_do_minimo]

    # --- 4. Perdas do período ---
    perdas = movs.filter(tipo_movimentacao='PERDA').order_by('-data_movimentacao')

    # --- Valor financeiro total do estoque ---

    valor_estoque = LoteEstoque.objects.filter(
        esgotado=False,
    ).aggregate(
        total=DjSum(
            ExpressionWrapper(
                F('quantidade_restante') * F('valor_unitario'),
                output_field=DecimalField()
            )
        )
    )['total'] or Decimal('0.00')

    # --- Dados para os filtros ---
    categorias = Categoria.objects.filter(ativo=True).order_by('categoria')
    anos_qs    = Movimentacao.objects.dates('data_movimentacao', 'year', order='DESC')
    anos       = [d.year for d in anos_qs] or [hoje.year]

    meses = [
        (1,'Janeiro'),(2,'Fevereiro'),(3,'Março'),(4,'Abril'),
        (5,'Maio'),(6,'Junho'),(7,'Julho'),(8,'Agosto'),
        (9,'Setembro'),(10,'Outubro'),(11,'Novembro'),(12,'Dezembro'),
    ]

    nome_mes = dict(meses).get(mes, '')

    return render(request, 'estoque/relatorios.html', {
        'mes':                    mes,
        'ano':                    ano,
        'nome_mes':               nome_mes,
        'categoria_id':           categoria_id,
        'resumo':                 resumo,
        'produtos_mov':           produtos_mov,
        'produtos_alerta':        produtos_alerta,
        'perdas':                 perdas,
        'valor_estoque':          valor_estoque,
        'valor_peps_por_produto': valor_peps_por_produto,
        'categorias':             categorias,
        'anos':                   anos,
        'meses':                  meses,
    })

    
@login_required(login_url='login')
def movimentacao_rectificar(request, pk):
    """
    Rectifica uma movimentação com erro.
    Apenas utilizadores com perfil ADMIN podem aceder.

    O processo:
      1. Marca a movimentação original como rectificada
      2. Cria automaticamente um estorno (movimentação inversa)
      3. Regista no Log quem fez, quando e porquê
      4. Redireciona para a lista com mensagem de sucesso
    """

    # --- Apenas ADMIN pode rectificar ---
    if request.user.perfil != 'ADMIN':
        raise PermissionDenied

    movimentacao = get_object_or_404(Movimentacao, pk=pk)

    # --- Já foi rectificada anteriormente ---
    if movimentacao.rectificada:
        messages.warning(
            request,
            f'Esta movimentação já foi rectificada anteriormente.'
        )
        return redirect('movimentacao_lista')

    if request.method == 'POST':
        motivo = request.POST.get('motivo', '').strip()

        if not motivo:
            messages.error(request, 'O motivo da rectificação é obrigatório.')
            return render(request, 'estoque/movimentacao_rectificar.html', {
                'movimentacao': movimentacao,
            })

        # --- Determina o tipo do estorno (inverso da original) ---
        tipo_estorno = {
            'ENTRADA': 'SAIDA',
            'SAIDA':   'ENTRADA',
            'PERDA':   'ENTRADA',
        }.get(movimentacao.tipo_movimentacao, 'ENTRADA')

        # --- Cria o estorno automaticamente ---
        estorno = Movimentacao.objects.create(
            utilizador        = request.user,
            produto           = movimentacao.produto,
            fornecedor        = movimentacao.fornecedor,
            tipo_movimentacao = tipo_estorno,
            quantidade        = movimentacao.quantidade,
            valor_unitario    = movimentacao.valor_unitario,
            observacao        = f'ESTORNO AUTOMÁTICO — Ref. movimentação #{movimentacao.pk}. Motivo: {motivo}',
            data_movimentacao = timezone.now(),
            movimentacao_origem = movimentacao,
        )

        # --- Marca a original como rectificada ---
        movimentacao.rectificada         = True
        movimentacao.motivo_rectificacao = motivo
        movimentacao.save()

        # --- Regista no Log ---

        Log.objects.create(
            utilizador     = request.user,
            acao           = Log.Acao.EDICAO,
            tabela_afetada = 'movimentacao',
            id_registro    = movimentacao.pk,
            dados_antes    = (
                f'tipo={movimentacao.tipo_movimentacao}, '
                f'produto={movimentacao.produto.produto}, '
                f'quantidade={movimentacao.quantidade}, '
                f'valor_unitario={movimentacao.valor_unitario}'
            ),
            dados_depois   = (
                f'rectificada=True, '
                f'estorno_id={estorno.pk}, '
                f'motivo={motivo}'
            ),
        )

        tipo_label = {
            'ENTRADA': 'Entrada',
            'SAIDA':   'Saída',
            'PERDA':   'Perda'
        }.get(movimentacao.tipo_movimentacao, '')

        messages.success(
            request,
            f'{tipo_label} #{movimentacao.pk} rectificada com sucesso! '
            f'Estorno #{estorno.pk} criado automaticamente. '
            f'Regista agora a movimentação correcta.'
        )
        return redirect('movimentacao_lista')

    return render(request, 'estoque/movimentacao_rectificar.html', {
        'movimentacao': movimentacao,
    })

@login_required(login_url='login')
def inventario_acerto(request, pk):
    """
    Aplica o acerto de estoque com base nas divergências do inventário.
    Apenas ADMIN pode executar.
    Só pode ser aplicado uma vez por inventário.
    Só funciona em inventários concluídos.
    """
    if request.user.perfil != 'ADMIN':
        raise PermissionDenied

    inventario = get_object_or_404(Inventario, pk=pk)

    # Validações
    if not inventario.concluido:
        messages.error(request, 'O inventário tem de estar concluído antes de aplicar o acerto.')
        return redirect('inventario_detalhe', pk=pk)

    if inventario.acerto_aplicado:
        messages.warning(request, 'O acerto já foi aplicado para este inventário.')
        return redirect('inventario_detalhe', pk=pk)

    if request.method == 'POST':
        itens_com_divergencia = list(   # ← converte para lista logo aqui
            inventario.itens.filter(
                diferenca__isnull=False
            ).exclude(diferenca=0).select_related('produto')
        )

        if not itens_com_divergencia:
            messages.info(request, 'Não existem divergências para acertar neste inventário.')
            return redirect('inventario_detalhe', pk=pk)

        produtos_afectados = set()
        movimentacoes_criadas = 0

        for item in itens_com_divergencia:
            produto = item.produto
            produtos_afectados.add(produto)  # ← recolhe aqui, dentro do mesmo loop

            if item.diferenca > 0:
                tipo = 'ENTRADA'
                quantidade = item.diferenca
            else:
                tipo = 'SAIDA'
                quantidade = abs(item.diferenca)

            Movimentacao.objects.create(
                utilizador        = request.user,
                produto           = produto,
                fornecedor        = None,
                tipo_movimentacao = tipo,
                quantidade        = quantidade,
                valor_unitario    = produto.custo_medio or Decimal('0.00'),
                observacao        = f'Acerto de inventário #{inventario.pk} — {inventario.data_inventario}',
                data_movimentacao = timezone.now(),
            )
            movimentacoes_criadas += 1

        # Recalcula o saldo de cada produto afectado

        for produto in produtos_afectados:
            saldo = LoteEstoque.objects.filter(
                produto=produto,
                esgotado=False,
            ).aggregate(total=DjSum('quantidade_restante'))['total'] or Decimal('0.00')
            Produto.objects.filter(pk=produto.pk).update(estoque_atual=saldo)


        # Marca como acertado — remove o bloco duplicado que existia
        inventario.acerto_aplicado = True
        inventario.save()

        # Regista no Log
        Log.objects.create(
            utilizador     = request.user,
            acao           = Log.Acao.EDICAO,
            tabela_afetada = 'inventario',
            id_registro    = inventario.pk,
            dados_antes    = 'acerto_aplicado=False',
            dados_depois   = f'acerto_aplicado=True, movimentacoes_criadas={movimentacoes_criadas}',
        )

        messages.success(
            request,
            f'Acerto aplicado com sucesso! '
            f'{movimentacoes_criadas} movimentação(ões) criada(s) automaticamente.'
        )
        return redirect('inventario_detalhe', pk=pk)

    # GET — página de confirmação
    itens_divergentes = inventario.itens.exclude(diferenca=0).select_related('produto')

    return render(request, 'estoque/inventario_acerto.html', {
        'inventario':       inventario,
        'itens_divergentes': itens_divergentes,
    })

