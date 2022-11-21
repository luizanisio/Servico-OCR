# -*- coding: utf-8 -*-
from tempfile import TemporaryDirectory
from util_pdf_ocr import imagens_pdf
from util_ocr import analise_imagens_ocr
from util_html import aimg_2_html
from util import Util
from util_processar_pasta import ProcessarOcrThread
import os
import json
import shutil

class Controller():

    def aplicar_ocr_arquivo(self, arquivo):
        return {}

    def request_file_send(self, request_file):
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

    def ocerizar_arquivo_recebido(self, request_file, ignorar_cache = False, cabecalho = True, estampas = True, citacoes = True, saida_pdf = False):
        if not saida_pdf:
            return self.ocerizar_arquivo_para_html(request_file = request_file,
                                                   ignorar_cache = ignorar_cache, 
                                                   cabecalho = cabecalho, 
                                                   estampas = estampas, 
                                                   citacoes = citacoes)
        else:
            return self.ocerizar_arquivo_para_pdf(request_file = request_file,
                                                   ignorar_cache = ignorar_cache)


    def ocerizar_arquivo_para_pdf(self, request_file, ignorar_cache = False):
        ''' retorna o hash para criar um link de download e o status da ocerização 
            {"erro":, "hash": ..., "inicio": ...., "fim": ...., "tempo": }
            '''
        if not request_file:
            return {}
        with TemporaryDirectory() as tempdir:
             arquivo_entrada = self.__arquivo_analise__(request_file, tempdir)
             if not os.path.isfile(arquivo_entrada):
                a = os.path.split(arquivo_entrada)[1]
                return {'erro': f'Arquivo não encontrado "{a}"' }
             hash_arquivo = Util.hash_file(arquivo_entrada)
             destino_entrada = os.path.join(ProcessarOcrThread.servico().entrada, f'{hash_arquivo}.pdf')
             destino_json = os.path.join(ProcessarOcrThread.servico().entrada, f'{hash_arquivo}.json')
             json_status_inicial = {'status': 'incluído na pasta de entrada', 
                                    'nome_real': os.path.split(arquivo_entrada)[1],
                                    'inicio': Util.data_hora_str(),
                                    'tamanho_inicial' : round(os.path.getsize(arquivo_entrada)/1024,2)}
             if ignorar_cache:
                status_arquivo = {}
             else:   
                status_arquivo = ProcessarOcrThread.servico().status_arquivo(hash_arquivo)
             print(f'Processar PDF "{arquivo_entrada}" >> "{destino_entrada}"')
             if not any(status_arquivo):
                if arquivo_entrada.find('_cache.') > 0:
                    shutil.move(arquivo_entrada, destino_entrada)
                else:
                    shutil.copy(arquivo_entrada, destino_entrada)
                status_arquivo.update(json_status_inicial)
                Util.gravar_json(destino_json, json_status_inicial)
                status_arquivo = ProcessarOcrThread.servico().status_arquivo(hash_arquivo)
                
             if 'status' in status_arquivo:
                status_arquivo['tipo_folha'] = 'PDF'
                return status_arquivo
        return {'erro' : 'Não foi possívle identificar o status do arquivo enviado'}

    def status_por_id(self, id_arquivo):
        return ProcessarOcrThread.servico().status_arquivo(id_arquivo)

    def ocerizar_arquivo_para_html(self, request_file, ignorar_cache = False, cabecalho = True, estampas = True, citacoes = True):
        ''' retorna o conteúdo da extração em html e o tipo da folha reconhecido
            pode retornar uma mensagem de erro ou o hash para acompanhamento posterior
            {"html": ..., "tipo_folha": ..., "erro":, "hash": ..., }
            '''
        if not request_file:
            return {}
        with TemporaryDirectory() as tempdir:
             arquivo_entrada = self.__arquivo_analise__(request_file, tempdir)
             if not os.path.isfile(arquivo_entrada):
                a = os.path.split(arquivo_entrada)[1]
                return {'erro': f'Arquivo não encontrado "{a}"' }
             hash_arquivo = Util.hash_file(arquivo_entrada)
             print(f'Extraindo dados do arquivo: "{arquivo_entrada}"  hash: {hash_arquivo}')

             # nome do arquivo json de análise
             pasta = './temp/'
             #arquivo_json = os.path.splitext( os.path.split(arquivo_entrada)[1])[0]
             #arquivo_json = 
             arquivo_json = os.path.join(pasta, f'{hash_arquivo}.json')
             print('Procurando cache no arquivo: ', arquivo_json, end='')
             # análise em cache
             if (not ignorar_cache) and os.path.isfile(arquivo_json):
                dados = Util.ler_json(arquivo_json)
                if any(dados):
                    print(' ... cache encontrado _o/')
                    aimg = analise_imagens_ocr(dados)
                    dados = aimg.dados()
                    Util.gravar_json(arquivo_json, dados)
                    dados = self.filtrar_dados(dados = dados, cabecalho=cabecalho, 
                                               estampas=estampas, citacoes = citacoes)
                    return {'html': aimg_2_html(dados), 'tipo_folha' : self.tipo_folha(dados) }
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
             Util.gravar_json(arquivo_json, dados)
             dados = self.filtrar_dados(dados = dados, cabecalho=cabecalho, 
                                        estampas=estampas, citacoes = citacoes)
        return {'html': aimg_2_html(dados), 'tipo_folha' : self.tipo_folha(dados) }

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
           nome_arquivo = str(request_file)
           nome_arquivo = os.path.split(nome_arquivo)[1]
           return os.path.join('./exemplos/', nome_arquivo)

        # veio o conteúdo do arquivo - copia ele para a pasta temporária
        file_pdf = self.request_file_send(request_file)
        if file_pdf:
            nome_arquivo = os.path.split(file_pdf.filename)[1]
            nome_arquivo = os.path.join(tempdir, f'cache_{nome_arquivo}') 
            file_pdf.save(nome_arquivo)
            return nome_arquivo

        return None

    def listar_exemplos(self):
        exemplos_pdf = Util.listar_arquivos(pasta = './exemplos/', extensao = 'pdf')
        exemplos_png = Util.listar_arquivos(pasta = './exemplos/', extensao = 'png')
        exemplos_jpg = Util.listar_arquivos(pasta = './exemplos/', extensao = 'jpg')
        exemplos = exemplos_pdf + exemplos_jpg + exemplos_png
        #print('Exemplos: ', exemplos)
        return [(os.path.split(nm)[1], nm) for nm in exemplos]

    def limpar_temporarios(self):
        Util.limpar_temporarios(5)

    def arquivo_saida(self, hash):
        arquivo = os.path.join(ProcessarOcrThread.servico().saida, f'{hash}.pdf')
        return arquivo if os.path.isfile(arquivo) else None

    def status_arquivo_saida(self, hash):
        return ProcessarOcrThread.servico().status_arquivo(hash)
