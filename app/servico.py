# -*- coding: utf-8 -*-

from copy import deepcopy
from flask import Flask, jsonify, request, render_template
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
# limpeza do cache
@app.route(f'{PATH_API}health', methods=['GET'])
@app.route('/health', methods=['GET'])
def get_health():
    return jsonify({'ok'})

###################################################################
# recebe um PDF ou imagem
# retorna json com a análise do PDF
@app.route(f'{PATH_API}analisar_arquivo', methods=['GET','POST'])
def srv_analisar_regras():
    dados = get_post(request)
    return jsonify( {'retorno': 'teste - não imlementado'} )

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
        exemplo = str(dados.get('exemplo',''))
        exemplo = '' if exemplo.find(' -- exemplos')>=0 else exemplo

        tem_arquivo_enviado = controller.request_file_pdf(request_file = request)
        _ini = datetime.now()
        tipo_folha = ''
        try:
            if ('submit' not in dados):
                html_ocr = '' 
                controller.limpar_temporarios()
            elif exemplo and not tem_arquivo_enviado:
                print('Ocerizando arquivo de exemplo: ', exemplo)
                html_ocr, tipo_folha = controller.ocerizar_imagens_para_html(exemplo,
                                                                    ignorar_cache = ignorar_cache, 
                                                                    cabecalho = com_cabecalho, 
                                                                    estampas = com_estampas,
                                                                    citacoes = com_citacoes)
            elif not tem_arquivo_enviado:
                html_ocr = '' 
            else:
                print('Ocerizando arquivo recebido ...')
                html_ocr, tipo_folha = controller.ocerizar_imagens_para_html(request, 
                                                                    ignorar_cache = ignorar_cache, 
                                                                    cabecalho = com_cabecalho, 
                                                                    estampas = com_estampas,
                                                                    citacoes = com_citacoes)
        except Exception as e:
            html_ocr = controller.alerta(f'ERRO: {e}')
            tipo_folha = ''
        tempo = round((datetime.now()-_ini).total_seconds(),2)
        #pedido_limpar_cache = dados.pop('limpar_cache','')
        #print('HTML recebido: ', html_ocr[:100])

        return render_template("aplicar_ocr_arquivo.html", 
                titulo = titulo,
                texto_ocr = Markup(str(html_ocr)),
                tempo = f"{tempo:.3f} s",
                ignorar_cache = ignorar_cache,
                com_cabecalho = com_cabecalho,
                com_estampas = com_estampas,
                com_citacoes = com_citacoes,
                tipo_folha = tipo_folha,
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
    print( '#########################################')
    print( 'Iniciando o serviço')
    print( '-----------------------------------------')
    app.run(host='0.0.0.0', debug=False,port=8000)

