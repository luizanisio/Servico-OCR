# -*- coding: utf-8 -*-

from util import Util
import os

'''
 Autor Luiz Anísio 19/02/2023
 Constroi um arquivo md com os dicionários dos box extraídos pelo tesseract e 
 analisados pela classe util_ocr.AnaliseImagensOCR
 '''

def get_rotulado(rotulo, substituicao):
    return f'> <sub><b>{rotulo}</b>: @@{substituicao}@@ </sub>\n' 

def get_modelo_texto(superior_esquerda, cabecalho, superior_direita, estampa_direita, estampa_esquerda):
    texto = ''
    quebra = ''
    if any(cabecalho):
       texto += '>@@cabecalho@@\n' 
       quebra = '\n'
    if any(superior_esquerda):
       texto += get_rotulado('Folha esquerda', 'folhase')
       quebra = '\n'
    if any(superior_direita):
       texto += get_rotulado('Folha direita', 'folhasd')
       quebra = '\n'
    if any(estampa_esquerda):
       texto += get_rotulado('Rstampa esquerda', 'estampas_e')
       quebra = '\n'
    if any(estampa_direita):
       texto += get_rotulado('Estampa direita', 'estampas_d')
       quebra = '\n'
    texto = f'{quebra}{texto}{quebra}\n@@textos@@\n' 
    return f'{texto}\n'

def get_rodape(inferior_esquerda, rodape, inferior_direita):
    if not (any(inferior_esquerda) or any(inferior_direita) or any(rodape)):
        return ''
    texto = ''
    if any(rodape):
       texto = '>@@rodape@@\n'
    if any(inferior_esquerda):
       texto += get_rotulado('Estampa esquerda', 'folhaie')
    if any(inferior_direita):
       texto += get_rotulado('Estampa direita', 'folhaid')
    return texto


def aimg_2_md(dados):
    ''' página tem 9 regiões
    
        folha   cabeçalho folha
        estampa textos    estampa
        folha   rodapé    folha
    '''
    pagina = 0
    def _textos_dict():
        return {'cabecalho': [],  'folhase': [],    'folhasd':[],
                'estampas_e': [], 'estampas_d': [], 'textos':[],
                'rodape': [],     'folhaie': [],    'folhaid':[]}
    textos = _textos_dict()
    tooltips = _textos_dict()
    textos_paginas = []

    # constrói a estrutura da página e depois une os tipos iguais e substitui na página
    def _inserir_pagina_(_textos, _tooltips):
        texto = ''
        # verifica se inclui cabeçalho da página 
        texto += get_modelo_texto(superior_esquerda =_textos['folhase'], 
                                  cabecalho =_textos['cabecalho'],
                                  superior_direita = _textos['folhasd'],
                                  estampa_esquerda= _textos['estampas_e'],
                                  estampa_direita= _textos['estampas_d'])
        # verifica se inclui rodapé da página 
        texto += get_rodape(inferior_esquerda = _textos['folhaie'],
                            rodape= _textos['rodape'],
                            inferior_direita = _textos['folhaid'])
        if not texto:
            return

        for c, v in _textos.items():
            if c in ['cabecalho','rodape']:
               unir = '\n>' 
            else:
               unir = '\n'  
            v = unir.join(v) if any(v) else ''
            v = str(v).replace(r'\[',r'[').replace(r'\]',r']').replace(r'[',r'\[').replace(r']',r'\]')
            texto = texto.replace(f'@@{c}@@', f'{v}')

        #for c, v in _tooltips.items():
        #    v = '\n'.join(set(v)) if any(v) else ''
        #    v = f'Motivo da região: {v}' if v else ''
        #    texto = texto.replace(f'@@{c}_tt@@', f'{v}')
                        
        # guarda o md da página
        while texto.find('\n\n\n') >=0:
            texto = texto.replace('\n\n\n', '\n\n')
        texto = f'<sub><mark>Página: {len(textos_paginas)+1}</mark></sub>{texto}'
        textos_paginas.append(texto) 

    for box in dados:
        #print('md do box: ', box['box'], box['texto'][:10])
        # quebra de página
        if pagina != box['pagina']:
           _inserir_pagina_(textos, tooltips) 
           pagina = box['pagina']
           # reinicia os conteúdos
           textos = _textos_dict()
           tooltips = _textos_dict()

        # regiões dos textos
        if box['tipo'] == 'F': # folha
            if   'E' in box['bordas'] and 'S' in box['bordas']:
                textos['folhase'].append(box_2_md(box))
                tooltips['folhase'].append(box['tipo_sugerido'])
            elif 'D' in box['bordas'] and 'S' in box['bordas']:
                textos['folhasd'].append(box_2_md(box))
                tooltips['folhasd'].append(box['tipo_sugerido'])
            elif 'E' in box['bordas'] and 'I' in box['bordas']:
                textos['folhaie'].append(box_2_md(box))
                tooltips['folhaie'].append(box['tipo_sugerido'])
            elif 'D' in box['bordas'] and 'I' in box['bordas']:
                textos['folhaid'].append(box_2_md(box))
                tooltips['folhaid'].append(box['tipo_sugerido'])
        elif box['tipo'] == 'E': # estampa
            if 'D' in box['bordas']:
                textos['estampas_d'].append(box_2_md(box))
                tooltips['estampas_d'].append(box['tipo_sugerido'])
            elif 'E' in box['bordas']:
                textos['estampas_e'].append(box_2_md(box))
                tooltips['estampas_e'].append(box['tipo_sugerido'])
        elif box['tipo'] == 'C': # cabeçalho 
             textos['cabecalho'].append(box_2_md(box))
             tooltips['cabecalho'].append(box['tipo_sugerido'])
        elif box['tipo'] == 'R': # rodapé
             textos['rodape'].append(box_2_md(box))
             tooltips['rodape'].append(box['tipo_sugerido'])
        elif box['texto']:
             textos['textos'].append(box_2_md(box))
    # caso tenha ficado algum dado para inserir
    _inserir_pagina_(textos, tooltips) 
    return '\n<hr>\n'.join(textos_paginas)


MODELO_CITACAO = '\n> @@texto@@\n'
def box_2_md(box):
    if box['tipo'] == 'T':
       md = '<b>'+ box['texto'] + '</b>'
    elif box['tipo'] == 'CT':
       _texto = '\n'.join( Util.unir_paragrafos_quebrados(str(box['texto']).split('\n')) )
       md = MODELO_CITACAO.replace('@@texto@@', _texto.replace('\n','>\n'))
    else :
       md = '\n'.join( Util.unir_paragrafos_quebrados(str(box['texto']).split('\n')) )
    return md

def arquivo_aimg_2_md(arquivo_aimg):
    if not arquivo_aimg:
       return 
    arquivo_md = os.path.splitext(arquivo_aimg)[0] + '.md'
    if os.path.isfile(arquivo_md):
       try:
          os.remove(arquivo_md)
       except:
          print(f'* ATENÇÃO: Não foi possível remover o arquivo {arquivo_md}')  
    if not os.path.isfile(arquivo_aimg):
       return
    analise = Util.ler_json(arquivo_aimg)
    if any(analise):
        md = aimg_2_md(analise)
        try:
            with open(arquivo_md, 'w') as f:
                f.write(md)
        except:
            print(f'* ATENÇÃO: Não foi possível criar o arquivo {arquivo_md}')  

if __name__ == '__main__':
    import sys
    import os
    import json

    arquivo = 'testes-extração.json'
    arquivo ='Artigo Seleção por consequências B F Skinner.json'
    arquivo = './temp/Exemplo texto colunas.json'

    arquivo_aimg_2_md(f'{arquivo}')

    print('Finalizado')
