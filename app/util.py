# -*- coding: utf-8 -*-

'''
 Autor Luiz Anísio 20/11/2022
 Utilitários simples para simplificação de alguns códigos comuns
 '''

import os, time
import hashlib
from datetime import datetime
import json
import random
import string
from multiprocessing import cpu_count
import re

ABREVIACOES = ['sra?s?', 'exm[ao]s?', 'ns?', 'nos?', 'doc', 'ac', 'publ', 'ex', 'lv', 'vlr?', 'vls?',
               'exmo\(a\)', 'ilmo\(a\)', 'av', 'of', 'min', 'livr?', 'co?ls?', 'univ', 'resp', 'cli', 'lb',
               'dra?s?', '[a-z]+r\(as?\)', 'ed', 'pa?g', 'cod', 'prof', 'op', 'plan', 'edf?', 'func', 'ch',
               'arts?', 'artigs?', 'artg', 'pars?', 'rel', 'tel', 'res', '[a-z]', 'vls?', 'gab', 'bel',
               'ilm[oa]', 'parc', 'proc', 'adv', 'vols?', 'cels?', 'pp', 'ex[ao]', 'eg', 'pl', 'ref',
               'reg', 'f[ilí]s?', 'inc', 'par', 'alin', 'fts', 'publ?', 'ex', 'v. em', 'v.rev',
               'des', 'des\(a\)', 'desemb']
#print('REGEX: ',r'(?:\b{})\.\s*$'.format(r'|\b'.join(ABREVIACOES)) )
ABREVIACOES_RGX = re.compile(r'(?:\b{})\.\s*$'.format(r'|\b'.join(ABREVIACOES)), re.IGNORECASE)
PONTUACAO_FINAL = re.compile(r'([\.\?\!]\s+)')
PONTUACAO_FINAL_LISTA = {'.','?','!'}
RE_NUMEROPONTO = re.compile(r'(\d+)\.(?=\d)')
TEMP_GERADOS = []

HASH_BUF_SIZE = 65536  # lets read stuff in 64kb chunks!
class Util():
    @classmethod
    def hash_file(clss, arquivo, complemento=''):
        # BUF_SIZE is totally arbitrary, change for your app!
        # https://stackoverflow.com/questions/22058048/hashing-a-file-in-python

        md5 = hashlib.md5()
        with open(arquivo, 'rb') as f:
            while True:
                data = f.read(HASH_BUF_SIZE)
                if not data:
                    break
                md5.update(data)

        return f'{md5.hexdigest()}{complemento}'

    @classmethod
    def listar_arquivos(cls, pasta, extensao='txt', inicio=''):
        if not os.path.isdir(pasta):
            msg = f'Não foi encontrada a pasta "{pasta}" para listar os arquivos "{extensao}"'
            raise Exception(msg)
        res = []
        _inicio = str(inicio).lower()
        _extensao = f".{extensao}".lower() if extensao else ''
        for path, dir_list, file_list in os.walk(pasta):
            for file_name in file_list:
                if (not inicio) and file_name.lower().endswith(f"{_extensao}"):
                    res.append(os.path.join(path,file_name))
                elif file_name.lower().endswith(f"{_extensao}") and file_name.lower().startswith(f"{_inicio}"):
                    res.append(os.path.join(path,file_name))
        return res

    @classmethod
    def limpar_temporarios(cls, pasta = './temp/', dias = 1):
        if not os.path.isdir(pasta):
           return  
        dias = 0.5 if dias < 0.5 else dias
        tempo = 60*60*24 * dias
        now = time.time()
        print(f'- Analisando temporários da pasta {pasta} com mais de {dias} dias ... ')
        for filename in os.listdir(pasta):
            filestamp = os.stat(os.path.join(pasta, filename)).st_mtime
            filecompare = now - tempo
            if  filestamp < filecompare:
                try:
                    os.remove(os.path.join(pasta, filename))
                    print(f'Temporário removido "{filename}" _o/')
                except Exception as e:
                    print(f'Temporário NÃO removido "{filename}" :( - ERRO: {e}')

    @classmethod
    def limpar_controles(cls, pasta, minutos = 1):
        minutos = 0.5 if minutos < 0.5 else minutos
        tempo = 60 * minutos
        now = time.time()
        #print('Analisando arquivos de controle ... ')
        for filename in os.listdir(pasta):
            if not str(filename).endswith('.lc'):
                continue
            filestamp = os.stat(os.path.join(pasta, filename)).st_mtime
            filecompare = now - tempo
            if  filestamp < filecompare:
                try:
                    os.remove(os.path.join(pasta, filename))
                    #print(f'Controle removido "{filename}" _o/')
                except Exception as e:
                    print(f'Controle NÃO removido "{filename}" :( - ERRO: {e}')

    @classmethod
    def data_hora_str(cls, datahora = None):
        if not datahora:
           return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
           return datahora.strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def tempo_arquivo(cls, arquivo):
        dt_arquivo = cls.data_arquivo(arquivo)
        if (not dt_arquivo):
            return -1
        return (datetime.now() - dt_arquivo).total_seconds()

    @classmethod
    def data_arquivo_str(cls, arquivo):
        if not os.path.isfile(arquivo):
            return ''
        return Util.data_hora_str( cls.data_arquivo(arquivo) )           

    @classmethod
    def data_arquivo(cls, arquivo):
        if not os.path.isfile(arquivo):
            return None
        return datetime.fromtimestamp(os.path.getmtime(arquivo))

    @classmethod
    def gravar_json(cls, arquivo, dados):
        with open(arquivo, 'w') as f:
            f.write(json.dumps(dados, indent = 2))

    @classmethod
    def ler_json(cls, arquivo, padrao = dict() ):
        if os.path.isfile(arquivo):
            with open(arquivo, 'r') as f:
                 dados = f.read()
            if len(dados)>2 and dados.find('{')>=0 and dados[-5:].find('}')>0:
                return json.loads(dados)
        return padrao

    @classmethod
    def gravar_lista_json(cls, arquivo, dados):
        with open(arquivo, 'w') as f:
            for linha in dados:
                f.write(json.dumps(linha) + '\n')

    @classmethod
    def ler_lista_json(cls, arquivo, padrao = []):
        res = padrao
        if os.path.isfile(arquivo):
            res = []
            with open(arquivo, 'r') as f:
                 dados = f.read()
            if len(dados)>2:
               dados = dados.split('\n')
               for linha in dados: 
                   linha = linha.strip()
                   if linha[:1] == '{' and linha[-1:] == '}':
                      res.append(json.loads(linha))
        return res

    # --- NÚMERO DE CPUS -----
    @staticmethod
    def cpus(uma_livre=True):
        num_livres = 1 if uma_livre else 0
        return cpu_count() if cpu_count() < 3 else cpu_count() - num_livres

    @staticmethod
    def get_token():
        tamanho = random.randint(10,15)
        return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(tamanho))

    @staticmethod
    def get_file_temp(pasta = './temp', sufixo = '.filetemp'):
        global TEMP_GERADOS
        arquivo = ''
        while not arquivo or arquivo in TEMP_GERADOS:
              tamanho = random.randint(20,30)
              arquivo = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(tamanho))
              arquivo = f'{arquivo}{sufixo}'
        TEMP_GERADOS = TEMP_GERADOS[:100]
        Util.limpa_file_temp(pasta, sufixo)
        return os.path.join(pasta, f'filetemp_{arquivo}')

    @staticmethod
    def limpa_file_temp(pasta = './temp', sufixo = '.filetemp'):
        tempo = 60 
        now = time.time()
        #print('Analisando arquivos de controle ... ')
        for filename in os.listdir(pasta):
            if not str(filename).endswith(sufixo):
                continue
            if not os.path.split(filename)[1].startswith('filetemp_'):
                continue
            filestamp = os.stat(os.path.join(pasta, filename)).st_mtime
            filecompare = now - tempo
            if  filestamp < filecompare:
                try:
                    os.remove(os.path.join(pasta, filename))
                    print(f'Temporário "{filename}" _o/')
                except Exception as e:
                    print(f'Temporário NÃO removido "{filename}" :( - ERRO: {e}')

    @staticmethod
    def unir_paragrafos_quebrados(texto):
        lista = texto if type(texto) is list else texto.split('\n')
        res = []
        def _final_pontuacao(_t):
            if len(_t.strip()) == 0:
                return False
            return _t.strip()[-1] in PONTUACAO_FINAL_LISTA
        for i, linha in enumerate(lista):
            _ant = lista[i-1] if i>0 else ""
            #print(f'Lista: [{_ant}]' )
            #print('linha {}: |{}| '.format(i,linha.strip()), _final_pontuacao(linha), ABREVIACOES_RGX.search(lista[i-1]) if i>0 else False)
            if i==0:
                res.append(linha)
            elif (not _final_pontuacao(lista[i-1])) or \
                (_final_pontuacao(lista[i-1]) and (ABREVIACOES_RGX.search(lista[i-1]))):
                # print('juntar: ', lista[i-1].strip(), linha.strip())
                if len(res) ==0: res =['']
                res[len(res)-1] = res[-1].strip() + ' '+ linha
            else:
                res.append(linha)
        return res