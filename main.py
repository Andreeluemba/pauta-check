"""
main.py

Roda o fluxo completo de verificação de uma pauta:
  1. Extrai a pauta FÍSICA escaneada (OCR célula por célula)
  2. Extrai a pauta do SISTEMA (PDF digital)
  3. Compara as duas e gera o relatório de divergências (tela + CSV)

Uso:
    python main.py

Ajuste os caminhos dos arquivos de entrada logo abaixo antes de rodar.
"""

import extrai_fisica
import extrai_sistema
import compara_pautas

# AJUSTAR: caminhos reais dos arquivos, quando tivermos os dois PDFs/imagem
CAMINHO_PAUTA_FISICA = 'pauta.png'          # imagem ou, futuramente, PDF escaneado
CAMINHO_PAUTA_SISTEMA = 'pauta_sistema_teste.pdf'  # trocar pelo PDF real do sistema


def main():
    print('=' * 70)
    print('ETAPA 1/3 — Extraindo pauta FÍSICA (OCR)')
    print('=' * 70)
    extrai_fisica.CAMINHO_IMAGEM = CAMINHO_PAUTA_FISICA
    imagem_cinza, linhas, dimensoes = extrai_fisica.extrair_celulas_da_imagem(CAMINHO_PAUTA_FISICA)
    tabela_fisica = extrai_fisica.ocr_celulas(imagem_cinza, linhas, dimensoes)
    dados_fisica = extrai_fisica.montar_dados_longos(tabela_fisica)

    print('\n' + '=' * 70)
    print('ETAPA 2/3 — Extraindo pauta do SISTEMA (PDF)')
    print('=' * 70)
    linhas_sistema = extrai_sistema.extrair_tabelas_do_pdf(CAMINHO_PAUTA_SISTEMA)
    dados_sistema = extrai_sistema.montar_dados_longos(linhas_sistema)

    print('\n' + '=' * 70)
    print('ETAPA 3/3 — Comparando as duas pautas')
    print('=' * 70)
    resultado = compara_pautas.comparar_pautas(dados_sistema, dados_fisica)
    compara_pautas.imprimir_relatorio(resultado)
    compara_pautas.exportar_csv(resultado)


if __name__ == '__main__':
    main()