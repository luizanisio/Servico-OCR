# -*- coding: utf-8 -*-

'''
 Autor Luiz Anísio 20/11/2022
 Utilitários simples para simplificação de alguns códigos comuns
 '''

import os, time
import hashlib
from datetime import datetime
import json

HASH_BUF_SIZE = 65536  # lets read stuff in 64kb chunks!
class Util():
    @classmethod
    def hash_file(clss, arquivo):
        # BUF_SIZE is totally arbitrary, change for your app!
        # https://stackoverflow.com/questions/22058048/hashing-a-file-in-python

        md5 = hashlib.md5()
        with open(arquivo, 'rb') as f:
            while True:
                data = f.read(HASH_BUF_SIZE)
                if not data:
                    break
                md5.update(data)

        return md5.hexdigest()

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
    def limpar_temporarios(cls, dias = 1):
        dias = 0.5 if dias < 0.5 else dias
        path = "./temp/"
        tempo = 60*60*24 * dias
        now = time.time()
        print('Analisando temporários ... ')
        for filename in os.listdir(path):
            filestamp = os.stat(os.path.join(path, filename)).st_mtime
            filecompare = now - tempo
            if  filestamp < filecompare:
                try:
                    os.remove(os.path.join(path, filename))
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
    def data_arquivo_str(cls, arquivo):
        if not os.path.isfile(arquivo):
            return ''
        return Util.data_hora_str( datetime.fromtimestamp(os.path.getmtime(arquivo)) )           

    @classmethod
    def gravar_json(cls, arquivo, dados):
        with open(arquivo, 'w') as f:
            f.write(json.dumps(dados, indent = 2))

    @classmethod
    def ler_json(cls, arquivo, padrao = {}):
        if os.path.isfile(arquivo):
            with open(arquivo, 'r') as f:
                    dados = f.read()
            if len(dados)>2 and dados.find('{')>=0 and dados[-5:].find('}')>0:
                return json.loads(dados)
        return padrao
