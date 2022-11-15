# -*- coding: utf-8 -*-

'''
 Autor Luiz Anísio 12/11/2022
 Constroi uma página HTML com os dicionários dos box extraídos pelo tesseract e 
 analisados pela classe util_ocr.analise_imagens_ocr
 '''

PAGINA_HTML_C = '''
            <div class="container-fluid">
                <div class="row">
                   <div class="col-md-1 font-weight-light bg-light text-sm-left border-secondary"> 
                        <span class="d-inline-block" tabindex="0" data-toggle="tooltip" title="@@folhase_tt@@">
                        @@folhase@@
                        </span>
                   </div>
                   <div class="col-md-10 font-weight-light bg-light text-sm-left">
                        <span class="d-inline-block" data-toggle="tooltip" title="@@cabecalho_tt@@">
                        @@cabecalho@@
                        </span>
                   </div>
                   <div class="col-md-1 font-weight-light bg-light text-sm-left border-secondary"> 
                        <span class="d-inline-block" tabindex="0" data-toggle="tooltip" title="@@folhasd_tt@@">
                        @@folhasd@@
                        </span>
                   </div>
                </div>
                '''
PAGINA_HTML_M = '''
                <div class="row">
                   <div class="col-md-1 border-right font-weight-light bg-light text-sm-left text-justify" >
                        <span class="d-inline-block" tabindex="0" data-toggle="tooltip" title="@@estampas_e_tt@@">
                        @@estampas_e@@
                        </span>
                   </div>
                   <div class="col-md-10 text-justify">
                        @@textos@@
                   </div>
                   <div class="col-md-1 border-left font-weight-light bg-light text-sm-left text-justify">
                        <span class="d-inline-block" tabindex="0" data-toggle="tooltip" title="@@estampas_d_tt@@">
                        @@estampas_d@@
                        </span>
                   </div>
                </div>
                '''
PAGINA_HTML_T = '''<div class="col-md-10 text-justify">
                        @@textos@@
                   </div>
                '''
PAGINA_HTML_R = '''
                <div class="row">
                   <div class="col-md-1 font-weight-light bg-light text-sm-left border-secondary"> 
                        <span class="d-inline-block" tabindex="0" data-toggle="tooltip" title="@@folhaie_tt@@">
                        @@folhaie@@
                        </span>
                   </div>
                   <div class="col-md-10 font-weight-light bg-light text-sm-left">
                        <span class="d-inline-block" tabindex="0" data-toggle="tooltip" title="@@rodape_tt@@">
                        @@rodape@@
                        </span>
                   </div>
                   <div class="col-md-1 font-weight-light bg-light text-sm-left border-secondary"> 
                        <span class="d-inline-block" tabindex="0" data-toggle="tooltip" title="@@folhaid_tt@@">
                        @@folhaid@@
                        </span>
                   </div>
                </div>
            </div>
            '''

def aimg_2_html(dados):
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

    def _inserir_pagina_(_textos, _tooltips):
        texto = ''
        # verifica se inclui cabeçalho da página 
        if any(_textos['cabecalho'])  or any(_textos['folhase'])    or any(_textos['folhasd']):
            texto += PAGINA_HTML_C
        # verifica se inclui estampas ou só o texto na página 
        if any(_textos['estampas_e']) or any(_textos['estampas_d']) :
            texto += PAGINA_HTML_M
        else:
            texto += PAGINA_HTML_T
        # verifica se inclui rodapé da página 
        if any(_textos['rodape'])     or any(_textos['folhaie'])    or any(_textos['folhaid']):
            texto += PAGINA_HTML_R
        if not texto:
            return

        for c, v in _textos.items():
            v = '\n<p>'.join(v) if any(v) else ''
            texto = texto.replace(f'@@{c}@@', f'{v}')

        for c, v in _tooltips.items():
            v = '\n'.join(set(v)) if any(v) else ''
            v = f'Motivo da região: {v}' if v else ''
            texto = texto.replace(f'@@{c}_tt@@', f'{v}')
                        
        # guarda o html da página
        textos_paginas.append(texto) 

    for box in dados:
        #print('html do box: ', box['box'], box['texto'][:10])
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
                textos['folhase'].append(box_2_html(box))
                tooltips['folhase'].append(box['tipo_sugerido'])
            elif 'D' in box['bordas'] and 'S' in box['bordas']:
                textos['folhasd'].append(box_2_html(box))
                tooltips['folhasd'].append(box['tipo_sugerido'])
            elif 'E' in box['bordas'] and 'I' in box['bordas']:
                textos['folhaie'].append(box_2_html(box))
                tooltips['folhaie'].append(box['tipo_sugerido'])
            elif 'D' in box['bordas'] and 'I' in box['bordas']:
                textos['folhaid'].append(box_2_html(box))
                tooltips['folhaid'].append(box['tipo_sugerido'])
        elif box['tipo'] == 'E': # estampa
            if 'D' in box['bordas']:
                textos['estampas_d'].append(box_2_html(box))
                tooltips['estampas_d'].append(box['tipo_sugerido'])
            elif 'E' in box['bordas']:
                textos['estampas_e'].append(box_2_html(box))
                tooltips['estampas_e'].append(box['tipo_sugerido'])
        elif box['tipo'] == 'C': # cabeçalho 
             textos['cabecalho'].append(box_2_html(box))
             tooltips['cabecalho'].append(box['tipo_sugerido'])
        elif box['tipo'] == 'R': # rodapé
             textos['rodape'].append(box_2_html(box))
             tooltips['rodape'].append(box['tipo_sugerido'])
        elif box['texto']:
             textos['textos'].append(box_2_html(box))
    # caso tenha ficado algum dado para inserir
    _inserir_pagina_(textos, tooltips) 
    return '<hr>'.join(textos_paginas)

MODELO_CITACAO = '''\n<div class="container-fluid text-justify">
                          <div class="row">
                              <div class="col-md-3 "></div>
                              <div class="col-md-9 border-left font-weight-light font-italic text-sm-left"> @@texto@@ </div>
                          </div>
                    </div>'''
def box_2_html(box):
    if box['tipo'] == 'T':
       html = '<b>'+ box['texto'] +'</b>'
    elif box['tipo'] == 'CT':
       html = MODELO_CITACAO.replace('@@texto@@', box['texto'])
    else :
       html = box['texto']
    return html

if __name__ == '__main__':
    import sys
    import os
    import json
    with open('./temp/testes-extração.json', 'r') as f:
        dados = f.read()
        dados = json.loads(dados)

    html = aimg_2_html(dados)

    with open('./temp/testes-extração.html', 'w') as f:
        f.write(html)
    print('Finalizado')
