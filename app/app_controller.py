# -*- coding: utf-8 -*-
from tempfile import TemporaryDirectory
from util_pdf_ocr import imagens_pdf
from util_ocr import AnaliseImagensOCR
from util_html import aimg_2_html
from util_markdown import aimg_2_md
from util import Util
from util_tokens import TokensUsuario
from util_processar_pasta import ProcessarOcrThread
import os
import json
import shutil

class Controller():

    def __init__(self) -> None:
        self.pastas_saida = [ProcessarOcrThread.servico().saida, ProcessarOcrThread.servico().saida_img]
        self.tokens = TokensUsuario(pastas_saida = self.pastas_saida)
        self.pasta_temp = './temp'
        # pasta para geração dos arquivos temporários de download
        os.makedirs(self.pasta_temp, exist_ok=True)

    def get_status_id(self, id):
        return ProcessarOcrThread.servico().status_arquivo(id,pastas_saida = self.pastas_saida)

    def get_html_id(self, id, cabecalho, estampas, citacoes):
        nm_analise = os.path.join(ProcessarOcrThread.servico().saida_img, f'{id}.json')
        if os.path.isfile(nm_analise):
           dados = Util.ler_json(nm_analise, {}) 
        if not any(dados):
           return {'erro' : self.alerta(f'Arquivo não encontrado para visualização')}
        dados = self.filtrar_dados(dados = dados, cabecalho=cabecalho, 
                                   estampas=estampas, citacoes = citacoes)
        return {'html': aimg_2_html(dados), 'tipo_folha' : self.tipo_folha(dados) }

    def get_md_id(self, id, cabecalho, estampas, citacoes):
        nm_analise = os.path.join(ProcessarOcrThread.servico().saida_img, f'{id}.json')
        print('Nome arquivo análise: ', nm_analise)
        dados = {}
        if os.path.isfile(nm_analise):
           dados = Util.ler_json(nm_analise, {}) 
        if not any(dados):
           return {'erro' : self.alerta(f'Arquivo não encontrado para visualização')}
        dados = self.filtrar_dados(dados = dados, cabecalho=cabecalho, 
                                   estampas=estampas, citacoes = citacoes)
        return {'md': aimg_2_md(dados)}

    def processar_envio_arquivo(self, token, exemplo_ou_request, 
                                      ignorar_cache = False, 
                                      gerar_pdf = True,
                                      gerar_img = True):
        ''' cria o link token-hash 
            {"erro": ... se ocorrer erro }
            '''
        if not exemplo_ou_request:
            return {}
        with TemporaryDirectory() as tempdir:
             arquivo_entrada = self.__arquivo_analise__(exemplo_ou_request, tempdir)
             if not os.path.isfile(arquivo_entrada):
                a = os.path.split(arquivo_entrada)[1]
                return {'erro': f'Arquivo não encontrado "{a}"' }
             #nome real usado para download
             nome_real = os.path.split(arquivo_entrada)[1]
             tipo_real = os.path.splitext(nome_real)[1]
             tipo_real = tipo_real[1:] if tipo_real[:1] == '.' else tipo_real
             nome_real = nome_real[6:] if nome_real[:6].lower() == 'cache_' else nome_real
             print(f'Preparando análise do arquivo {arquivo_entrada} para processamento')
             # todo processamento é feito pelo hash do arquivo
             hash_arquivo = Util.hash_file(arquivo_entrada, complemento = tipo_real)
             print(f'Associando token {token} ao id {hash_arquivo} do arquivo {nome_real}')
             self.tokens.incluir_id(token, hash_arquivo)
             if gerar_pdf and tipo_real.lower() == 'pdf':
                destino = os.path.join(ProcessarOcrThread.servico().entrada, f'{hash_arquivo}.pdf') 
                status_existente = ProcessarOcrThread.servico().status_arquivo(destino, ProcessarOcrThread.servico().saida)
                if (not ignorar_cache) and status_existente.get('status_pdf'):
                    return {}
                status_inicial = {'status_pdf': 'enviado para processamento', 
                                  'id' : f'{hash_arquivo}',
                                  'nome_real_pdf': nome_real,
                                  'tipo_real_pdf': tipo_real,
                                  'inicio_pdf': Util.data_hora_str(),
                                  'tamanho_inicial_pdf' : round(os.path.getsize(arquivo_entrada)/1024,2)}
                print(f'Processar PDF "{arquivo_entrada}" >> "{destino}"')
                ProcessarOcrThread.servico().atualizar_status(destino, status_inicial, ProcessarOcrThread.servico().saida)
                if arquivo_entrada.find(tempdir) >= 0:
                    shutil.move(arquivo_entrada, destino)
                else:
                    shutil.copy(arquivo_entrada, destino)
             if gerar_img or tipo_real.lower() != 'pdf' or (not gerar_pdf):
                destino = os.path.join(ProcessarOcrThread.servico().entrada_img, f'{hash_arquivo}.{tipo_real}')
                status_existente = ProcessarOcrThread.servico().status_arquivo(destino, ProcessarOcrThread.servico().saida_img)
                if (not ignorar_cache) and status_existente.get('status_img'):
                    print(f'Arquivo enviado já existe: {nome_real} com id {hash_arquivo}')
                    return {}
                status_inicial = {'status_img': 'enviado para processamento', 
                                  'id' : f'{hash_arquivo}',
                                  'nome_real_img': nome_real,
                                  'tipo_real_img': tipo_real,
                                  'inicio_img': Util.data_hora_str(),
                                  'tamanho_inicial_img' : round(os.path.getsize(arquivo_entrada)/1024,2)}
                print(f'Processar IMG "{arquivo_entrada}" >> "{destino}"')
                ProcessarOcrThread.servico().atualizar_status(destino, status_inicial, ProcessarOcrThread.servico().saida_img)
                if arquivo_entrada.find(tempdir) >= 0:
                    shutil.move(arquivo_entrada, destino)
                else:
                    shutil.copy(arquivo_entrada, destino)
             
                return {}
        return {'erro' : 'Não foi possívle identificar o status do arquivo enviado'}



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

    def alerta(self, mensagem):
        return f'<div class="p-3 mb-2 bg-warning text-dark">{mensagem}</div>'

    def get_nome_arquivo_pdf(self, id):
        nm_pdf = os.path.join(ProcessarOcrThread.servico().saida, f'{id}.pdf')
        if os.path.isfile(nm_pdf):
           return nm_pdf
        return None

    def get_tarefas_usuario(self, token):
        Util.limpar_temporarios(self.tokens.pasta_tokens, dias = 10)
        return self.tokens.listar_tarefas(token)

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
        exemplos = []
        for tipo in ['pdf','png','jpg','tif','tiff']:
            exemplos += Util.listar_arquivos(pasta = './exemplos/', extensao = tipo)
        # print('Exemplos: ', exemplos)
        return [(os.path.split(nm)[1], nm) for nm in exemplos]

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

