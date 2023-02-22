# -*- coding: utf-8 -*-

import os
from util import Util
from util_processar_pasta import ProcessarOcr
from datetime import datetime

'''
 Autor Luiz Anísio 17/02/2023
 Controla os tokens e seus arquivos para listagem de tarefas em andamento/concluídas

 usado com o Servico-OCR
 - quando um token coloca um arquivo para processar, é gerado um arquivo token-id para saber que esse token pediu esse arquivo
 - se vários tokens pedirem o mesmo arquivo, funciona como uma relação 1-n   
 
 retorna uma lista de jsons com os status dos arquivos
 '''

class TokensUsuario():
    def __init__(self, pastas_saida) -> None:
        # a pasta de tokens contém a relação token-arquivo
        # vários usuários podem ter enviado o mesmo arquivo, então há aproveitamento de processamento
        # pastas_saida são as pastas do serviço de OCR que contém os status dos arquivos
        self.pasta_tokens = './tokens/'
        self.dthr_limpeza = None
        os.makedirs(self.pasta_tokens, exist_ok=True)
        self.pastas_saida = pastas_saida

    def listar_tarefas(self, token):
        if not token:
           return []
        arquivos = Util.listar_arquivos(self.pasta_tokens, extensao='json', inicio=f'{token}-')
        #print(f'Arquivos encontrados para o token [{token}]: ', arquivos)
        if not any(arquivos):
            return []
        # procura as tarefas dos ids
        res = []
        for pasta in self.pastas_saida:
            for arquivo in arquivos:
                nome_arquivo_status = os.path.split(arquivo)[1]
                nome_arquivo_status = str(nome_arquivo_status)[len(token)+1:]
                nome_id = os.path.splitext(nome_arquivo_status)[0]
                #print(f'Procurando status do arquivo para token {token}: {nome_arquivo_status}')
                status = ProcessarOcr.status_arquivo(nome_arquivo_status, pasta)
                #print(f'Status {nome_arquivo_status}: {status}')
                ok = False
                # linha imagem
                if status.get('nome_real_img'):
                    linha = {'tipo' : 'img', 'nome_real' : status.get('nome_real_img',nome_arquivo_status) }
                    linha['download'] = str(nome_id) if status.get('finalizado_img') else ''
                    linha['tamanho_inicial'] = status.get('tamanho_inicial_img', 0 ) 
                    linha['tamanho_final'] = status.get('tamanho_final_img', 0 )
                    linha['status'] = status.get('status_img', 'status indisponível' )
                    linha['inicio'] = status.get('inicio_img', '' )
                    linha['dthr'] = status.get('dthr_img', '' )
                    linha['finalizado'] = status.get('finalizado_img')
                    linha['id'] = nome_id
                    res.append(linha)
                    ok = True
                if status.get('nome_real_pdf'):
                    linha = {'tipo' : 'pdf', 'nome_real' : status.get('nome_real_pdf',nome_arquivo_status) }
                    linha['download'] = str(nome_id) if status.get('finalizado_pdf') else ''
                    linha['tamanho_inicial'] = status.get('tamanho_inicial_pdf', 0 ) 
                    linha['tamanho_final'] = status.get('tamanho_final_pdf', 0 )
                    linha['status'] = status.get('status_pdf', 'status indisponível' )
                    linha['inicio'] = status.get('inicio_pdf', '' )
                    linha['dthr'] = status.get('dthr_pdf', '' )
                    linha['finalizado'] = status.get('finalizado_pdf')
                    linha['id'] = nome_id
                    res.append(linha)
                    ok = True
                # atualiza o token por ser válido
                if ok:
                   #print('Atualizando token: ', arquivo) 
                   Util.gravar_json(arquivo, dados={'token' : token, 'id' : nome_arquivo_status, 'dthr' : Util.data_hora_str()})
        res.sort(key= lambda k:k.get('nome_real'))
        return res

    def limpar_temporarios(self):
        # limpa as relações token-id a cada 5 min
        # limpa as relações com mais de 10 dias
        if (self.dthr_limpeza is None) or (datetime.now() - self.dthr_limpeza).total_seconds() > 300:
           Util.limpar_temporarios(self.tokens.pasta_tokens, dias = 10)
           self.dthr_limpeza = datetime.now()

    def arquivo_token(self, token, id):
        return os.path.join(self.pasta_tokens, f'{token}-{id}.json')

    def incluir_id(self, token, id):
        arquivo = self.arquivo_token(token, id)
        Util.gravar_json(arquivo, dados={'token' : token, 'id' : id})

    def remover_id(self, token, id):
        arquivo = self.arquivo_token(token, id)
        if os.path.isfile(arquivo):
            try:
                os.remove(arquivo)
            except :
                print(f'Erro ao remover o arquivo de token {arquivo}: {e}')
                pass

if __name__ == '__main__':
    pastas_saida = ['./ocr_saida', './ocr_saida_img']
    tk = TokensUsuario(pastas_saida=pastas_saida)
    token = 'luiz'

    incluir = ['teste_citacao_01', 'Gerar Erro', 'teste_citacao_02', 'teste12345', 'testes-extração', 
               'notícia_br_linux_tesseract', 'Artigo Seleção por consequências B F Skinner', 'testes-extração_repetição',
               'vocabulario analise do comportamento','vocabulario analise do comportamento2' ]
    #for nome in incluir:
    #    tk.incluir_id(token, nome)
    tarefas = tk.listar_tarefas(token)
    print(f'Tarefas do token "{token}" ')
    [print(_) for _ in tarefas]
    print('------------------------------')
    print('Health Check Serviço-OCR: ', ProcessarOcr.class_health_check(pastas_saida=pastas_saida))