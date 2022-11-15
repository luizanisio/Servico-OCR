# -*- coding: utf-8 -*-
from tempfile import TemporaryDirectory
from util_pdf_ocr import imagens_pdf
from util_ocr import analise_imagens_ocr
from util_html import aimg_2_html
from util import hash_file, listar_arquivos, limpar_temporarios
import os
import json

class Controller():

    def aplicar_ocr_arquivo(self, arquivo):
        return {}

    def request_file_pdf(self, request_file):
        if type(request_file) is str:
            return None
        # arquivo pdf, testa o conteúdo
        if ('pdf' in request_file.files) and (request_file.files['pdf']) and \
             str(request_file.files['pdf'].filename).lower().endswith('.pdf') and\
             str(request_file.files['pdf'].content_type).lower().find('pdf') > 0:
           return request_file.files['pdf']

        # arquivo imagem - vai tentar abrir qualquer um
        if ('pdf' in request_file.files) and (request_file.files['pdf']) :
           return request_file.files['pdf']
        return None

    # extrai as imagens do PDF
    def extrair_imagens_request_pdf(self, request_file):
        # veio o nome do arquivo de exemplo
        if type(request_file) is str:
           print(f'Extraindo imagens do arquivo {request_file}')
           pasta = './exemplos/'
           arquivo = os.path.join(pasta,request_file) 
           imagens = imagens_pdf(arquivo_entrada = arquivo) 
        elif self.is_request_pdf(request_file):
           print(f'Extraindo imagens do request PDF')
           imagens = imagens_pdf(request_pdf = request_file) 
        else:
           print(f'Nenhuma imagem recebida') 
           imagens = []
        return imagens

    def alerta(self, mensagem):
        return f'<div class="p-3 mb-2 bg-warning text-dark">{mensagem}</div>'

    def ocerizar_imagens_para_html(self, request_file, ignorar_cache = False, cabecalho = True, estampas = True, citacoes = True):
        if not request_file:
            return {}, ''
        with TemporaryDirectory() as tempdir:
             arquivo_entrada = self.__arquivo_analise__(request_file, tempdir)
             if not os.path.isfile(arquivo_entrada):
                return self.alerta('Arquivo não encontrado')
             hash_arquivo = hash_file(arquivo_entrada)
             print(f'Extraindo dados do arquivo: "{arquivo_entrada}"  hash: {hash_arquivo}')

            # nome do arquivo json de análise
             pasta = './temp/'
             #arquivo_json = os.path.splitext( os.path.split(arquivo_entrada)[1])[0]
             #arquivo_json = 
             arquivo_json = os.path.join(pasta, f'{hash_arquivo}.json')
             print('Procurando cache no arquivo: ', arquivo_json, end='')
             # análise em cache
             if (not ignorar_cache) and os.path.isfile(arquivo_json):
                with open(arquivo_json, 'r') as f:
                        dados = f.read()
                if len(dados)>10 and dados.find('{')>=0 and dados[-5:].find('}')>=0:
                    print(' ... cache encontrado _o/')
                    dados = json.loads(dados)
                    aimg = analise_imagens_ocr(dados)
                    dados = aimg.dados()
                    with open(arquivo_json, 'w') as f:
                        f.write(json.dumps(dados, indent = 2))
                    dados = self.filtrar_dados(dados = dados, cabecalho=cabecalho, 
                                               estampas=estampas, citacoes = citacoes)
                    return aimg_2_html(dados), self.tipo_folha(dados)
             # nova análise
             if ignorar_cache:
                print(' ... cache ignorado _o/')
             else:
                print(' ... cache não encontrado :(')
             print('Atualizando cache: arquivo de entrada: ', arquivo_entrada)
             if self.e_arquivo_pdf(arquivo_entrada):
                imagens = imagens_pdf(arquivo_entrada)
             else:
                imagens = arquivo_entrada
             aimg = analise_imagens_ocr(imagens)
             dados = aimg.dados()
             with open(arquivo_json, 'w') as f:
                 f.write(json.dumps(dados, indent = 2))
             dados = self.filtrar_dados(dados = dados, cabecalho=cabecalho, 
                                        estampas=estampas, citacoes = citacoes)
        return aimg_2_html(dados), self.tipo_folha(dados)

    def filtrar_dados(self, dados, cabecalho, estampas, citacoes):
        if cabecalho and estampas and citacoes:
            return dados
        res = []
        for box in dados:
            if box['tipo'] in {'C','R'} and not cabecalho:
               continue
            elif box['tipo'] in ('E','F') and not estampas:
               continue 
            elif box['tipo'] == 'CT' and not citacoes:
               continue
            res.append(box)
        return res

    def e_arquivo_pdf(self, arquivo):
        return arquivo.lower().endswith('.pdf')

    def tipo_folha(self, dados):
        if not any(dados):
            return 'Página não definida'
        return 'Página '+ str(dados[0]['pagina_tipo'])

    # recebe um arquivo ou nome de um arquivo e retorna o nome
    # deve ser chamado dentro de um TemporaryDirectory
    def __arquivo_analise__(self, request_file, tempdir):
        # veio o conteúdo do PDF ou Imagem
        # a análise do tipo de arquivo é feita depois

        # veio o nome de um arquivo de exemplo
        if request_file and type(request_file) is str:
           arquivo_pdf = str(request_file)
           arquivo_pdf = os.path.split(arquivo_pdf)[1]
           return os.path.join('./exemplos/', arquivo_pdf)

        # veio o conteúdo do arquivo - copia ele para a pasta temporária
        file_pdf = self.request_file_pdf(request_file)
        if file_pdf:
            arquivo_pdf = os.path.split(file_pdf.filename)[1]
            arquivo_pdf = os.path.join(tempdir, f'cache_{arquivo_pdf}') 
            file_pdf.save(arquivo_pdf)
            return arquivo_pdf

        return None

    def listar_exemplos(self):
        exemplos_pdf = listar_arquivos(pasta = './exemplos/', extensao = 'pdf')
        exemplos_png = listar_arquivos(pasta = './exemplos/', extensao = 'png')
        exemplos_jpg = listar_arquivos(pasta = './exemplos/', extensao = 'jpg')
        exemplos = exemplos_pdf + exemplos_jpg + exemplos_png
        #print('Exemplos: ', exemplos)
        return [(os.path.split(nm)[1], nm) for nm in exemplos]

    def limpar_temporarios(self):
        limpar_temporarios(5)