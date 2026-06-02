from django.urls import path
from . import views

urlpatterns = [

    # --- Autenticação ---
    path('login/',  views.login_view,  name='login'),
    path('logout/', views.logout_view, name='logout'),

    # --- Dashboard ---
    path('', views.dashboard, name='dashboard'),

    # --- Categorias ---
    path('categorias/',                    views.categoria_lista,        name='categoria_lista'),
    path('categorias/nova/',               views.categoria_criar,        name='categoria_criar'),
    path('categorias/<int:pk>/editar/',    views.categoria_editar,       name='categoria_editar'),
    path('categorias/<int:pk>/toggle/',    views.categoria_toggle_ativo, name='categoria_toggle'),

    # --- Fornecedores ---
    path('fornecedores/',                  views.fornecedor_lista,        name='fornecedor_lista'),
    path('fornecedores/novo/',             views.fornecedor_criar,        name='fornecedor_criar'),
    path('fornecedores/<int:pk>/editar/',  views.fornecedor_editar,       name='fornecedor_editar'),
    path('fornecedores/<int:pk>/toggle/',  views.fornecedor_toggle_ativo, name='fornecedor_toggle'),

    # --- Produtos ---
    path('produtos/',                      views.produto_lista,        name='produto_lista'),
    path('produtos/novo/',                 views.produto_criar,        name='produto_criar'),
    path('produtos/<int:pk>/editar/',      views.produto_editar,       name='produto_editar'),
    path('produtos/<int:pk>/toggle/',      views.produto_toggle_ativo, name='produto_toggle'),

    # --- Movimentações ---
    path('movimentacoes/',                        views.movimentacao_lista,      name='movimentacao_lista'),
    path('movimentacoes/nova/',                   views.movimentacao_criar,      name='movimentacao_criar'),
    path('movimentacoes/<int:pk>/rectificar/',    views.movimentacao_rectificar, name='movimentacao_rectificar'),

    # --- Inventários ---
    path('inventarios/',                   views.inventario_lista,    name='inventario_lista'),
    path('inventarios/novo/',              views.inventario_criar,    name='inventario_criar'),
    path('inventarios/<int:pk>/',          views.inventario_detalhe,  name='inventario_detalhe'),
    path('inventarios/<int:pk>/concluir/', views.inventario_concluir, name='inventario_concluir'),

    # --- Relatórios ---
    path('relatorios/',                    views.relatorios,          name='relatorios'),
]
