import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestao.settings')
django.setup()

from estoque.models import Produto, Movimentacao
from django.db.models import Sum
from decimal import Decimal

print('A recalcular saldos...')

for produto in Produto.objects.all():
    movs_validas = Movimentacao.objects.filter(
        produto=produto,
        rectificada=False
    ).exclude(observacao__startswith='ESTORNO AUTOMÁTICO')

    entradas = movs_validas.filter(
        tipo_movimentacao='ENTRADA'
    ).aggregate(total=Sum('quantidade'))['total'] or Decimal('0.00')

    saidas = movs_validas.filter(
        tipo_movimentacao='SAIDA'
    ).aggregate(total=Sum('quantidade'))['total'] or Decimal('0.00')

    perdas = movs_validas.filter(
        tipo_movimentacao='PERDA'
    ).aggregate(total=Sum('quantidade'))['total'] or Decimal('0.00')

    produto.estoque_atual = entradas - saidas - perdas
    produto.save(update_fields=['estoque_atual'])
    print(f'  {produto.produto}: {produto.estoque_atual}')

print('Concluído!')