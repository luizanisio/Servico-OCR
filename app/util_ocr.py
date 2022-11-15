# -*- coding: utf-8 -*-
'''
 Autor Luiz Anísio 12/11/2022
 Constroi uma lista de dicts com as imagens analisadas pelo tesseract
 Alguns dados do dicionário podem ser usados para análise do tipo da caixa (rodapé, cabeçalho etc)
 [ {'pagina'     : 0 ...n número da página 
    'box'        : 0 ...n reinicia a cada página
    'id'         : 0 ...n até o último box (na ordem para leitura)
    'pagina_la' : [500,75], -> largura e altura da página
    'pagina_tipo' : A4, Legal .. -> tipo da página identificado
    'box_xyla'     : [10,14,30,45], -> x,y  largura, altura da caixa
    'alt_linhas'   : 23, -> média da altura das linhas do box
    'alt_linhas_med' : 30  -> média da altura das linhas da página
    'qtd_linhas'   : 3,  -> linhas da caixa
    'qtd_boxes'    : 2,  -> boxes na página
    'qtd_letras'   : 44, -> letras únicas
    'qtd_palavras' : 22, -> palavras únicas
    'margens_edsi' : [5,5,3,7] -> margens esquerda, direita, superior, inferior
    'bordas'     : [D,E,S,I..] -> Direita, Esquerda, Superior, Inferior (está em alguma borda)
    'texto' : 'bla bla bla',
    'tipo_sugerido': ... descrição do motivo do tipo sugerido (bordas, repetição etc)
    'tipo': C, R, T... Cabeçalho, Rodapé, Título, Folha, Citação ...
     },
  ]

armazenar_imagem = True - guarda cada imagem analisada para permitir desenhar sobre elas depois
Tesseract LEVEL: 1 - page, 2 - block, 3 - paragraph, 4 - line, 5 - word
'''

import pytesseract
from pytesseract import Output
import cv2
from copy import deepcopy
import re
from PIL import Image

class analise_imagens_ocr():
    CONF_LIMITE = 30
    MAX_PALAVRAS_CABECALHO = 15
    MAX_PALAVRAS_RODAPE = 40
    MAX_PALAVRAS_ESTAMPA = 30
    MAX_PALAVRAS_FOLHAS = 5

    RE_FOLHA = re.compile('[0-9]')

    def __init__(self, img, file_2_grayscale = True, linguagem='por', armazenar_imagem = True):
      self.file_2_grayscale = file_2_grayscale
      self.linguagem = linguagem
      self.__dados__ = []
      self.__enriquecidos__ = False # volta para false quando os dados são atualizados
      self.__pagina__ = -1   # guarda a página atual
      self.__box__ = -1      # guarda o box atual
      self.__caracter__ = -1 # guarda o caractere atual da página
      self.__imagens__ = [] # guarda as imagens de cada página analisada
      self.__paginas__ = 0  # número de páginas
      self.analisar_imagems(img, armazenar_imagem)
      
    def paginas(self):
        return sorted(set([box['pagina'] for box in self.__dados__]))

    def analisar_imagems(self, img, armazenar_imagem = True):
        ''' recebe uma imagem, um nome de arquivo ou uma lista de imagem ou lista de nomes de arquivos
            processa as imagens e guarda elas na lista de imagens do objeto
            e guarda os dados das caixas de texto
        '''
        if img is None:
           print(f'analise_imagens_ocr: nenhuma imagem recebida')
           return
        imgs = []
        if type(img) is str:
           # recebeu um nome de arquivo 
           imgs = [cv2.imread(img, 0 if self.file_2_grayscale  else None)]
           print(f'analise_imagens_ocr: arquivo {img} carregado')
        elif type(img) is list and len(img)>0 and type(img[0]) is dict:
           # recebeu um dicionário de análise
           self.__dados__ = img
           self.__enriquecidos__ = False
           imgs = []  
        elif type(img) is list:
           # recebeu uma lista de imagens
           imgs = [cv2.cvtColor(_, cv2.COLOR_BGR2GRAY if self.file_2_grayscale else None) for _ in img]
           print(f'analise_imagens_ocr: imagens carregadas')
        else:
           # recebeu uma imagem
           imgs = [cv2.cvtColor(img, cv2.COLOR_BGR2GRAY if self.file_2_grayscale else None)]
           print(f'analise_imagens_ocr: imagem carregada')
        # processa o OCR das imagens
        if len(imgs) > 0:
           self.processar_img_ocr(imgs)
           if armazenar_imagem:
              self.__imagens__.extend(imgs)
           else:
              self.__imagens__ = []  

    def processar_img_ocr(self, img):
        if type(img) is list:
           [self.processar_img_ocr(_) for _ in img]
           return
        ## insere em self.dados os dados da imagem
        d = pytesseract.image_to_data(img, lang=self.linguagem, output_type=Output.DICT)

        n_boxes = len(d['level'])
        if n_boxes < 1:
           return
        
        _pagina_o = -1
        _bloco_o  = -1
        _parag_linha_o = ''
        def dados_novos():
            return {'texto':'', 'pagina' : self.__pagina__, 
                    'pagina_la': [d['width'][0], d['height'][0]],
                    'box_xyla': [],
                    'qtd_linhas': 0}
        def incluir_dados(dados_incluir):
            txt = dados_incluir['texto'].strip().replace('  ',' ')
            if txt:
               dados_incluir['texto'] = txt
               self.__box__ += 1
               dados_incluir['box'] = self.__box__
               self.__dados__.append(dados_incluir)
        
        dados = dados_novos()
        self.__pagina__ += 1
        for i in range(n_boxes):
            _level = d['level'][i]
            _pagina = d['page_num'][i]
            _bloco  = d['block_num'][i]
            _paragrafo = d['par_num'][i]
            _linha = d['line_num'][i]
            _texto = d['text'][i]
            if _bloco != _bloco_o:
               #if _pagina != _pagina_o:
               #   self.__pagina__ += 1
               _pagina_o = _pagina
               _bloco_o = _bloco
               _parag_linha_o = ''
               incluir_dados(dados)
               dados = dados_novos()

            # guarda o box do texto
            if _level == 2:
               dados['box_xyla'] = [d['left'][i], d['top'][i],d['width'][i], d['height'][i]]

            # verifica se é um mínimo confiável o texto (pode ser lixo/ruído)
            if ( not _texto ) or ( d['conf'][i] < self.CONF_LIMITE ):
               continue

            # conta a linha se a caixa da palavra mudou de linha
            if _parag_linha_o != f'{_paragrafo}-{_linha}':
               #print(f'Mudou de linha e parágrafo: {_parag_linha_o} != {_paragrafo}-{_linha}')
               dados['qtd_linhas'] += 1
               _parag_linha_o = f'{_paragrafo}-{_linha}'

            ql = '\n' if _paragrafo != _paragrafo else ''
            dados['texto'] += f' {_texto}{ql}'
        
        incluir_dados(dados)
        self.__pagina__ += 1
        ### indica que precisa enriquecer os dados de análise novamente, 
        ### pois leva em conta todos os objetos
        self.__enriquecidos__ = False

    def dados(self):
        if not self.__enriquecidos__:
           self.__enriquecer_dados__()
        return self.__dados__

    def __load_dados__(self, dados):
        self.__dados__ = dados
        self.__enriquecidos__ = False

    def __enriquecer_dados__(self):
        #print('Enriquecendo os dados...')
        # guarda informações por página
        alturas_linhas = dict() # para média das alturas linhas por página
        linhas_v = dict()  # para identificação das margens por página
        linhas_h = dict()  # para identificação das margens por página

        palavras = []
        letras = []
        paginas = []
        paginas_box = {}
        # corrigir por páginas edsi no dict de cada página
        for box in self.__dados__:
            x, y, w, h = box['box_xyla']  
            qtd_linhas = box['qtd_linhas']
            pagina = box['pagina']
            if not pagina in linhas_h:
               linhas_h[pagina] = []
               linhas_v[pagina] = []
               alturas_linhas[pagina] = []
               paginas.append(pagina)
               paginas_box[pagina] = 0
            paginas_box[pagina] += 1
            linhas_h[pagina].append(y)
            linhas_h[pagina].append(y+h)
            linhas_v[pagina].append(x)
            linhas_v[pagina].append(x+w)
            alturas_linhas[pagina].append(h/qtd_linhas)
            # estatísticas do texto
            _texto = self.remove_acentos_simbolos(box['texto'])
            box['palavras'] = set([_ for _ in _texto.split(' ') if len(_) > 1])
            box['qtd_palavras'] = len(box['palavras'])
            box['qtd_letras'] = len(set([_ for _ in _texto if _]))
            box['alt_linhas'] = round(h / qtd_linhas)
            box['tipo_sugerido'] = ''
        # margens laterais, superior e inferior 
        # margens_edsi - margem até o box mais próximo ou a página
        for p in paginas:
            linhas_h[pagina].sort()
            linhas_v[pagina].sort()
        #print('linhas: ', linhas_h)
        #print('colunas: ', linhas_v)
        margens = None
        pagina = -1
        for box in self.__dados__:
            x, y, w, h = box['box_xyla']
            pw, ph = box['pagina_la']
            if box['pagina'] != pagina:
               pagina = box['pagina']
               margens = Pagina(pw,ph)
            box['qtd_boxes'] = paginas_box[box['pagina']]
            box['pagina_tipo'] = margens.tipo   
            # busca as margems com outras caixas ou a página 
            e = [_ for _ in linhas_v[pagina] if _ < x]
            d = [_ for _ in linhas_v[pagina] if _ > x+w]
            s = [_ for _ in linhas_h[pagina] if _ < y]
            i = [_ for _ in linhas_h[pagina] if _ > y+h]
            e = x-e[-1] if any(e) else x
            d = d[0] -x -w if any(d) else pw - x - w
            s = y-s[-1] if any(s) else y
            i = i[0] -y -h if any(i) else ph - y - h
            box['margens_edsi'] = [e,d-1,s,i-1]
            box['alt_linhas_med'] = round( sum(alturas_linhas[pagina]) / \
                                           len(alturas_linhas[pagina]) )

            # verifica se a caixa dentro de uma ou mais bordas
            # auxilia identificação de cabeçalho, rodapé, estampas e folhas
            box['bordas'] = []
            box['ordem_extra'] = 0
            if x + w <= pw * margens.MARGEM_LATERAL:
               box['bordas'].append('E')
               box['ordem_extra'] = 1
            elif x >= pw - pw * margens.MARGEM_LATERAL:
               box['bordas'].append('D')
               box['ordem_extra'] = 2
            if y + h <= ph * margens.MARGEM_CABECALHO:
               box['bordas'].append('S')
            elif y >= ph - ph * margens.MARGEM_RODAPE:
               box['bordas'].append('I')
               box['ordem_extra'] = 3

        # ordena pela página, depois pela posição y e depois pela posição x
        # box nas margens direita ou esquerda ficam no final
        self.__dados__.sort(key = lambda box:(box['pagina'], box['ordem_extra'], box['box_xyla'][1], box['box_xyla'][0]))
        # análise do tipo e ajustes do número do box dentro da página pela ordenação
        nbox = 0
        for i, box in enumerate(self.__dados__):
            if pagina != box['pagina']:
                nbox = 0
                pagina = box['pagina']
            box['box'] = nbox
            box['id'] = i
            nbox += 1
            # análise dos tipos - leva em consideração a posição do box 
            # - precisa ocorrer depois da ordenação
            self.__analisar_tipos__(box, margens)
        # análise de petição de textos para identificação de cabeçalhos e rodapés
        # leva em consideração os tipos já encontrados
        self.__analisar_repeticoes__()
        # ajuste final - limpeza do que não é necessário
        # precisa ocorrer no final pois alguns dados são usados durante as análises
        for i, box in enumerate(self.__dados__):
            # remove dados usados só na alálise
            box.pop('ordem_extra')
            box.pop('palavras')
            #box['palavras'] = list(box['palavras']) # para teste das palavras - precisa ser set para análise

        self.__paginas__ = pagina + 1
        self.__pagina__ = pagina 
        self.__enriquecidos__ = True
        #print('Enriquecimento concluído...')

    #-------------------------------            
    RE_ACENTOS = {(re.compile('[áâàãä]'), 'a'),
                  (re.compile('[éèêë]'), 'e'),
                  (re.compile('[íìîï]'), 'i'),
                  (re.compile('[óòôöõ]'), 'o'),
                  (re.compile('[úùüû]'), 'u'),
                  (re.compile('ç'), 'c'),
                  (re.compile('ñ'), 'n')}        
    def remove_acentos_simbolos(self, texto):
        for rg, pat in self.RE_ACENTOS:
            texto = rg.sub(pat, texto)                     
        texto = re.sub('[^0-9a-zA-Z ]', ' ', texto)
        return str(texto).lower()
    #-------------------------------            

    def print(self, filtro_box = None):
        for d in self.dados():
            print('-------------------------------')
            [print(f'{c} = {v}') for c,v in d.items() if filtro_box == None or filtro_box(d)]

    def imagem_pagina(self, n_pagina, desenhar = True, margens = True):
        img = deepcopy(self.__imagens__[n_pagina])
        if not (desenhar or margens):
           return img
        dados = [d for d in self.dados() if d['pagina'] == n_pagina]
        cor = (140, 140, 140)
        cor_margem = (200, 200, 200)
        for box in dados:
            x, y, w, h = box['box_xyla'] 
            if margens:
               e, d, s, i = box['margens_edsi'] 
               cv2.rectangle(img, (x-e, y-s), (x+w+d, y+h+i), cor_margem)
            if desenhar:
               cv2.rectangle(img, (x-1, y-1), (x + w + 1, y + h +1), cor, 1)
        
        #(d['left'][i], d['top'][i], d['width'][i], d['height'][i])
        #    if d['level'][i] in (2,5):
        #      cv2.rectangle(img, (x-1, y-1), (x + w + 1, y + h +1), cor, 1)
        return img

    def __analisar_tipos__(self, box, margens):
        ''' analisa o tipo do box
            C = cabeçalho   R = rodapé
            E = estampa     F = folha
            T = título      P = parágrafos
            CT = citação
        '''
        # reseta o tipo 
        box['tipo'] = ''
        if self.__cabecalho_rodape_estampa__(box) \
            or self.__titulo_citacao__(box, margens):
            # aqui já alterou o dicionário
            pass
        else:
            # padrão é parágrafo 
            box['tipo'] = 'P'
    
    def __cabecalho_rodape_estampa__(self, box):
        # análise de trechos em bordas
        bordas = box['bordas']
        if not any(bordas):
           return False
        palavras = box['qtd_palavras']
        qtd_linhas = box['qtd_linhas']
        n_box = box['box']
        qtd_boxes = box['qtd_boxes']
        # rodapé - está além da margem final com poucas palavras
        if ('I' in bordas) and palavras <= self.MAX_PALAVRAS_RODAPE:
           box['tipo'] = 'R'
           box['tipo_sugerido'] = 'Bordas'
        # estampa - se for C ou R também, é espaço de folhas
        if ('E' in bordas or 'D' in bordas) and ('S' in bordas or 'I' in bordas) and \
           palavras <= self.MAX_PALAVRAS_FOLHAS and self.RE_FOLHA.search(box['texto']):
           box['tipo'] = 'F' 
           box['tipo_sugerido'] = 'Bordas'
        # estampas
        elif ('E' in bordas) or ('D' in bordas) and \
           palavras <= self.MAX_PALAVRAS_ESTAMPA:
           box['tipo'] = 'E'
           box['tipo_sugerido'] = 'Bordas'
        return bool(box['tipo'])

    def __titulo_citacao__(self, box, margens):
        bordas = box['bordas']
        # só roda nos casos de não estar nas bordas ou ser um possível cabeçalho
        if box['tipo']:
            return False
        x, y, w, h = box['box_xyla']
        pw, ph = box['pagina_la']
        palavras = box['qtd_palavras']
        qtd_linhas = box['qtd_linhas']        
        n_box = box['box']
        # cabeçalho grande no centro horizontal 1/4 <- 2/4 -> 1/4 
        # e no topo até 1/4 da página - só para o primeiro box
        if n_box ==0 and palavras <= self.MAX_PALAVRAS_CABECALHO \
           and qtd_linhas <= 3 and \
           x >= pw/4 and x+w <= 3*pw/4 and y+h <= ph/4 :
           box['tipo'] = 'C'
           box['tipo_sugerido'] = 'Proporção e margem'
        # o box tem margem de citação e a margem direita é menor que a esquerda
        # pois pode ser um título centralizado
        elif (x / pw  >= margens.MARGEM_CITACAO) \
             and (pw - x - w < x * 0.8) \
             and box['qtd_linhas'] >= 1:
           box['tipo'] = 'CT'
           box['tipo_sugerido'] = 'Margem'
        # o box tem uma linha e a fonte é maior que a média da linhas * 1.15
        elif box['qtd_linhas'] == 1 and \
           box['qtd_palavras'] <= 15 and \
           h > box['alt_linhas'] * 1.15:
           box['tipo'] = 'T'
           box['tipo_sugerido'] = 'Altura da linha'
        return bool(box['tipo'])

    def __analisar_repeticoes__(self):
        ''' analisa repetições em boxes que não foram identificados 
            os primeiros 3 da página e os últimos 2 da página
            se tiverem até 3 linhas e 30 palavras
            pela posição nas margens, em busca de cabeçalhos e rodapés
            É cabeçalho se repetir o tamanho aproximado do box, linhas e o set de palavras
            Analisa a primeira e segunda página com as próximas, pois o cabeçalho pode começar na segunda
            '''
        paginas = self.__paginas__
        if paginas == 1:
            return
        achados = 0
        def __box_fora__(b):
            # se está na borda, já foi analisado
            if any(b['bordas']):
               #print(f'Box fora bordas: {b["pagina"]} - {b["box_xyla"]}')
               return True
            if b['qtd_palavras'] > 30 or b['qtd_linhas'] > 3:
               #print(f'Box fora palavras: {b["pagina"]} - {b["box_xyla"]}')
               return True
            if not (__box_topo__(b) or __box_rodape__(b)):
               #print(f'Box fora topo/rodapé: {b["pagina"]} - {b["box_xyla"]}')
               return True
            return False

        def __box_rodape__(b):
            # box abaixo de 5/6 da página
            return b['box_xyla'][1] >= 5*b['pagina_la'][1]/6
        def __box_topo__(b):
            # acima de 1/4 da página
            return b['box_xyla'][1] <= b['pagina_la'][1]/4

        # varre os boxes da primeira página e compara com as outras
        for box1 in self.__dados__:
            if box1['pagina'] > 1:
               break
            if __box_fora__(box1):
                continue
            distancia_termos = 0 if box1['qtd_palavras'] <= 5 else 2
            tipo_sugerido = 'C' if __box_topo__(box1) else 'R'
            # varre os próximos
            for box2 in self.__dados__:
                if box2['pagina'] <= box1['pagina']:
                   continue
                if __box_fora__(box2):
                    continue
                if self.__box_proximo__(box1, box2, 2) and self.__box_diferenca_termos__(box1,box2,distancia_termos):
                   box1['tipo'] = tipo_sugerido
                   box2['tipo'] = tipo_sugerido
                   box2['tipo_sugerido'] = 'Repetição'
                   box1['tipo_sugerido'] = 'Repetição'
                   #print(f'Boxex semelhantes:  tipo sugerido {tipo_sugerido}') 
                   #print('-', box1)
                   #print('-', box2)

    def __box_proximo__(self, box1, box2, distancia):
        ''' retorna se está no máximo da distância percentual da página informada '''
        l, a = box1['pagina_la']
        x1, y1, w1, h1 = box1['box_xyla']
        x2, y2, w2, h2 = box2['box_xyla']
        if 100*abs(x1 - x2)/l > distancia:
            return False
        if 100*abs(w1 - w2)/l > distancia:
            return False
        if 100*abs(y1 - y2)/a > distancia:
            return False
        if 100*abs(h1 - h2)/a > distancia:
            return False
        return True

    def __box_diferenca_termos__(self, box1, box2, diferenca):
        ''' diferença de até n termos '''
        if len(box1['palavras'] ^ box2['palavras']) > diferenca:
            return False
        return True
        '''
        d1 = box1['palavras'] - box2['palavras']
        d2 = box2['palavras'] - box1['palavras']
        d = d1 + d2
        print(f'{box1["box"]} e {box2["box"]} Distância: ', d1, d2, d, len(d) / len(d1+d2+d) )
        return (len(d) / len(d1+d2+d)) <= distancia
        '''

''' Recebe as dimensões da página e 
    busca o melhor padrão de página para as margens
'''
class Pagina():
        A4_w = 21
        A4_h = 29.7
        Carta_w = 21.59
        Carta_h = 27.94
        Legal_w = 21.59
        Legal_h = 35.56
        Quadrado_w = 20
        Quadrado_h = 20
        Faixa_w = 20
        Faixa_h = 10

        def __init__(self, pagina_w, pagina_h):
            proporcao = pagina_w / pagina_h
            # proporção A4 - prioridade
            if  20.5 <= proporcao * self.A4_h <= 21.5:
                w = self.A4_w if proporcao < 1 else self.A4_h
                h = self.A4_h if proporcao < 1 else self.A4_w
                #print(f'Folha A4 {w} / {h} = {w/h}')
                self.tipo = 'A4'
            # proporção Carta
            elif  20.09 <= proporcao * self.Carta_h <= 22.09:
                w = self.Carta_w if proporcao < 1 else self.Carta_h
                h = self.Carta_h if proporcao < 1 else self.Carta_w
                #print(f'Folha Carta {w} / {h} = {w/h}')
                self.tipo = 'Carta'
            # proporção Legal
            elif  20.50 <= proporcao * self.Legal_h <= 22.09:
                w = self.Legal_w if proporcao < 1 else self.Legal_h
                h = self.Legal_h if proporcao < 1 else self.Legal_w
                #print(f'Folha Legal {w} / {h} = {w/h}')
                self.tipo = 'Legal'
            # proporção Quadrado
            elif  19.5 <= proporcao * self.Quadrado_h <= 20.5:
                w = self.Quadrado_w if proporcao < 1 else self.Quadrado_h
                h = self.Quadrado_h if proporcao < 1 else self.Quadrado_w
                #print(f'Folha Quadrado {w} / {h} = {w/h}')
                self.tipo = 'Quadrado'
            # proporção Faixa
            elif  19.5 <= proporcao * self.Faixa_h <= 20.5:
                w = self.Faixa_w if self.proporcao < 1 else self.Faixa_h
                h = self.Faixa_h if self.proporcao < 1 else self.Faixa_w
                #print(f'Folha Faixa {w} / {h} = {w/h}')
                self.tipo = 'Faixa'
            # proporção Padrão A4
            else:
                w = self.A4_w if proporcao < 1 else self.A4_h
                h = self.A4_h if proporcao < 1 else self.A4_w
                #print(f'Folha padrão A4 {w} / {h} = {w/h}')
                self.tipo = 'A4'

            self.MARGEM_CABECALHO = 3/h   # 3cm 
            self.MARGEM_LATERAL   = 3/w   # 3cm 
            self.MARGEM_RODAPE    = 2.5/h # 2.5cm
            self.MARGEM_ESTAMPA   = 2.5/w # 2.5cm da largura do A4   
            self.MARGEM_CITACAO   = 5/w   # 5cm la largura do A4

###################################################################

if __name__ == '__main__':
    import sys
    import os
    import json

    arquivo = ''
    arquivo_padrao = './exemplos/testes-extração.png'
    for i, arg in enumerate(sys.argv[1:]):
        print(f"- {arg}")
        if os.path.isfile(arg):
            arquivo = arg
            print(f'Arquivo encontrado: {arquivo}')
            break
    if not arquivo:
        arquivo = arquivo_padrao
        print(f'Arquivo padrão utilizado: {arquivo}')

    if not os.path.isfile(arquivo):
        print(f'Arquivo não encontrado: {arquivo}')
        exit()
    
    if str(arquivo).lower().endswith('.pdf'):
       print('Não implementado') 
       exit()
    #imagem = cv2.imread(arq)
    aimg = analise_imagens_ocr(arquivo, file_2_grayscale = True)
    pasta, arquivo_nm = os.path.split(arquivo)
    arquivo_nm, _ = os.path.splitext(arquivo_nm)
    pasta = './temp/'

    arquivo_json = os.path.join(pasta, f'{arquivo_nm}.json')
    arquivo_imagem = os.path.join(pasta, f'{arquivo_nm}_ocr_?.png')

    with open(arquivo_json, 'w', encoding='utf8') as f:
        f.write(json.dumps(aimg.dados(), indent=2, ensure_ascii = True))
    
    print('Lista de páginas: ', aimg.paginas())
    for p in aimg.paginas():
        print(f'Analisando página {p}', end='')
        img = aimg.imagem_pagina(p, True, True)
        arq = arquivo_imagem.replace('?', str(p))
        #cv2.imwrite(arq,img)
        #arq = arquivo_imagem.replace('?', str(p)+'pil')
        img = Image.fromarray(img)
        img.save(arq, 'PNG', optimize=True)
        print(' _o/')
    
    print('OCR concluído')
    print('- arquivo json:  ', arquivo_json)
    print('- arquivos img: ', arquivo_imagem)

