# =============================================================================
# FICHEIRO: estoque/templatetags/estoque_extras.py
#
# Cria esta estrutura de pastas no teu projecto:
#
#   estoque/
#   └── templatetags/
#       ├── __init__.py      (ficheiro vazio)
#       └── estoque_extras.py  (este ficheiro)
#
# =============================================================================

from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Permite aceder a um dicionário por chave variável no template Django.

    Uso no template:
        {{ meu_dicionario|get_item:chave_variavel }}

    Exemplo:
        {{ valor_peps_por_produto|get_item:p.produto__pk }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)
