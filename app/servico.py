# -*- coding: utf-8 -*-

from copy import deepcopy
from flask import Flask, jsonify, request, render_template, send_file
from flask import render_template_string, redirect, url_for #, Markup
from markupsafe import Markup

from flask_bootstrap import Bootstrap4 #Bootstrap
from jinja2 import TemplateNotFound

import os
import json
from datetime import datetime

###################################################################
# controller
from app_controller import Controller
from util import Util 

app = Flask(__name__, template_folder='./templates')
bootstrap  = Bootstrap4(app)

PATH_API = '/'

###################################################################
# converte request ou dados para dict 
def get_post(req:request):
    res = (
            dict(req.args)
            or req.form.to_dict()
            or req.get_json(force=True, silent=True)
            or {}
        )
    #print('Dados enviados: ', res)
    return res

###################################################################
# health para monitoramento do serviço 
@app.route(f'{PATH_API}health', methods=['GET'])
@app.route('/health', methods=['GET'])
def get_health():
    return jsonify({'ok' : True})

###################################################################
# recebe um PDF ou imagem
# retorna json com a análise do PDF
@app.route(f'{PATH_API}analisar_arquivo', methods=['GET','POST'])
def srv_analisar_arquivo():
    dados = get_post(request)
    return jsonify( {'retorno': 'uso simplificado de API - ainda não imlementado'} )

###################################################################
# recebe um hash e retorna o arquivo se estiver pronto
@app.route(f'{PATH_API}download', methods=['GET','POST'])
def srv_download_arquivo():
    dados = get_post(request)
    controller = Controller()
    _id = dados.get('id','')
    status = controller.status_arquivo_saida(_id)
    if 'download' in status and 'pasta' in status and 'arquivo_pdf' in status:
       arquivo_pdf = os.path.join(status.get('pasta',''), status.get('arquivo_pdf',''))
       if os.path.isfile(arquivo_pdf):
          nome = status.get('nome_real', os.path.split(arquivo_pdf)[1] )
          print(f'Enviando arquivo: "{arquivo_pdf}" como "{nome}" ')
          return send_file(arquivo_pdf, as_attachment=True, attachment_filename =nome)
    return controller.alerta(f'Arquivo não encontrado para download id={_id}')

#############################################################################
#############################################################################
## formulários de análise de arquivo

@app.route(f'{PATH_API}',methods=['GET','POST'])
@app.route(f'{PATH_API}frm_analisar_arquivo',methods=['GET','POST'])
def frm_analisar_arquivo():
    try:
        controller = Controller()
        titulo = "Serviço OCR: Análise de arquivo"
        dados = get_post(request)
        # print(dados)
        # configurações dos checkbox
        inicio = ('submit' not in dados)
        ignorar_cache = 'CHECKED' if dados.get('ignorar_cache') in (True,'on','S',1) else ''
        com_cabecalho = 'CHECKED' if inicio or dados.get('com_cabecalho') in (True,'on','S',1) else ''
        com_estampas =  'CHECKED' if inicio or dados.get('com_estampas') in (True,'on','S',1)  else ''
        com_citacoes =  'CHECKED' if inicio or dados.get('com_citacoes') in (True,'on','S',1)  else ''
        id_arquivo = dados.get('id')
        saida_pdf =  'CHECKED' if dados.get('saida_pdf') in (True,'on','S',1)  else ''
        exemplo = str(dados.get('exemplo',''))
        exemplo = '' if exemplo.find(' -- exemplos')>=0 else exemplo

        tem_arquivo_enviado = controller.request_file_send(request_file = request)
        _ini = datetime.now()
        try:
            res = {'html' : ""}
            # página inicial, sem envio de informações, roda a limpeza dos temporários
            if ('submit' not in dados):
                controller.limpar_temporarios()
            # tem um exemplo selecionado e não foi enviado arquivo
            elif exemplo and not tem_arquivo_enviado:
                print(f'Ocerizando arquivo de exemplo: {exemplo}')
                res = controller.ocerizar_arquivo_recebido(exemplo,
                                                            ignorar_cache = ignorar_cache, 
                                                            cabecalho = com_cabecalho, 
                                                            estampas = com_estampas,
                                                            citacoes = com_citacoes,
                                                            saida_pdf = saida_pdf)
            # foi enviado um id específico par acompanhar
            elif id_arquivo and not tem_arquivo_enviado:
                print(f'Localizando id: {id_arquivo}')
                res = controller.status_por_id(id_arquivo)
            # foi enviado um arquivo
            else:
                print('Ocerizando arquivo recebido ...')
                res = controller.ocerizar_arquivo_recebido(request, 
                                                            ignorar_cache = ignorar_cache, 
                                                            cabecalho = com_cabecalho, 
                                                            estampas = com_estampas,
                                                            citacoes = com_citacoes,
                                                            saida_pdf = saida_pdf)
        except Exception as e:
            res = {'erro': f'ERRO: {e}' }

        if res.get('erro'):
            res['html'] = controller.alerta(res['erro'])
        download_arquivo = None
        if res.get('id'):
           exemplo = ''
           #res['html'] = f'Dados para download: {res}'
           download_arquivo = res
        tipo_folha = res.get('tipo_folha','')
        tempo = round((datetime.now()-_ini).total_seconds(),2)
        
        # só informa um * para dizer que ignorou, mas não mantém ativo
        ignorar_cache = '*' if ignorar_cache else ''
        
        return render_template("aplicar_ocr_arquivo.html", 
                titulo = titulo,
                texto_ocr = Markup(str(res.get('html',''))),
                download_arquivo = download_arquivo,
                tempo = f"{tempo:.3f} s",
                ignorar_cache = ignorar_cache,
                com_cabecalho = com_cabecalho,
                com_estampas = com_estampas,
                com_citacoes = com_citacoes,
                saida_pdf = saida_pdf,
                tipo_folha = tipo_folha,
                displaychkhtml = 'display: none' if saida_pdf else '',
                exemplos = get_lista_exemplos(exemplo))
    except TemplateNotFound as e:
        return render_template_string(f'Página não encontrada: {e.message}')

def get_lista_exemplos(exemplo):
    controller = Controller()
    res = [(_[0], 'SELECTED' if exemplo == _[0] else '') for _ in controller.listar_exemplos()]        
    res.insert(0, (' -- exemplos -- ', 'SELECTED' if not exemplo else ''))
    return res

#############################################################################
#############################################################################

if __name__ == "__main__":
    # carrega as regras
    #carregar_exemplos()
    from util_processar_pasta import ProcessarOcrThread
    print( '##############################################')
    print( 'Iniciando o serviço de ocerização de pastas')
    print( '-------------------------------------------------')
    ProcessarOcrThread()
    print( '-------------------------------------------------')
    print( 'Iniciando o serviço Flask')
    print( '-------------------------------------------------')
    app.run(host='0.0.0.0', debug=False,port=8000)
    print( '-------------------------------------------------')
    print( 'Finalizando o serviço de ocerização de pastas')
    print( '-------------------------------------------------')

    ProcessarOcrThread.finalizar()

