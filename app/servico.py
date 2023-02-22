# -*- coding: utf-8 -*-

from copy import deepcopy
from flask import Flask, jsonify, request, render_template, send_file
from flask import render_template_string, redirect, url_for #, Markup
from markupsafe import Markup

from flask_bootstrap import Bootstrap4 #Bootstrap
from jinja2 import TemplateNotFound

import os
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
    return jsonify( {'retorno': 'uso simplificado de API - ainda não implementado'} )

###################################################################
# recebe um hash e retorna o arquivo se estiver pronto
@app.route(f'{PATH_API}download', methods=['GET','POST'])
def srv_download_arquivo():
    dados = get_post(request)
    controller = Controller()
    _id = dados.get('id','') or dados.get('id_arquivo','')
    tipo = dados.get('tipo','')
    filtro_md = dados.get('filtro_md','')
    status = controller.get_status_id(_id)
    print(f'Buscando id="{_id}" com status = {status} e filtro_md = "{filtro_md}"')
    if status.get('finalizado_pdf') and tipo == 'pdf':
       arquivo_pdf = controller.get_nome_arquivo_pdf(_id)
       if os.path.isfile(arquivo_pdf):
          nome = status.get('nome_real_pdf', os.path.split(arquivo_pdf)[1] ) + '.pdf'
          print(f'Enviando arquivo: "{arquivo_pdf}" como "{nome}" ')
          return send_file(arquivo_pdf, as_attachment=True, attachment_filename =nome, cache_timeout=10)
    if status.get('finalizado_img') and tipo == 'md':
       cabecalho = (not filtro_md) or filtro_md.find('ca')>=0
       estampas = (not filtro_md) or filtro_md.find('es')>=0
       citacoes = (not filtro_md) or filtro_md.find('ci')>=0
       texto_md = controller.get_md_id(_id, cabecalho= cabecalho, estampas=estampas, citacoes=citacoes)
       texto = texto_md.get('md','')
       erro = texto_md.get('erro','')
       if erro:
          controller.alerta(f'Erro ao gerar o arquivo md para envio id={_id} erro: {erro}')
       if texto:
          arquivo = Util.get_file_temp()
          with open(arquivo, 'w') as f:
               f.write(f'{texto}')
          nome = status.get('nome_real_img', f'{_id}' ) + '.md'
          print(f'Enviando arquivo: "{arquivo}" como "{nome}" ')
          return send_file(arquivo, as_attachment=True, mimetype='text/html', attachment_filename =nome, cache_timeout=10)
    return controller.alerta(f'Arquivo não encontrado para download id={_id}')

#############################################################################
#############################################################################
## formulários de análise de arquivo

@app.route(f'{PATH_API}',methods=['GET','POST'])
@app.route(f'{PATH_API}frm_visualizar_arquivo',methods=['GET','POST'])
def frm_visualizar_arquivo():
    ''' Ao receber um id e a chave atualizar = carrega o arquivo 
        Ao receber a chave listar = lista as tarefas do token selecionado
        Ao receber o token em branco, cria um novo token 
        Ao receber um arquivo, liga o hash dele ao token do usuário'''
    try:
        controller = Controller()
        titulo = "Serviço OCR: Visualizar resultado de análise do arquivo"
        dados = get_post(request)
        # print(dados)
        # configurações dos checkbox
        listar = ('listar' in dados)
        atualizar = ('atualizar' in dados)
        token = str(dados.get('token','')).strip()
        # quando entra está ativo na tela de visualização
        chave_on = 1 
        ignorar_cache = 'CHECKED' if dados.get('ignorar_cache') in (True,'on','S',1) else ''
        gerar_pdf =  'CHECKED' if dados.get('gerar_pdf') in (True,'on','S',1)  else ''
        gerar_img =  'CHECKED' if dados.get('gerar_img') in (True,'on','S',1)  else ''
        com_cabecalho = 'CHECKED' if dados.get('com_cabecalho', chave_on) in (True,'on','S',1) else ''
        com_estampas =  'CHECKED' if dados.get('com_estampas', chave_on) in (True,'on','S',1)  else ''
        com_citacoes =  'CHECKED' if dados.get('com_citacoes', chave_on) in (True,'on','S',1)  else ''
        # exemplo para upload de arquivo
        exemplo = str(dados.get('exemplo',''))
        exemplo = '' if exemplo.find(' -- exemplos')>=0 else exemplo

        id_arquivo = str(dados.get('id_arquivo')) 

        _ini = datetime.now()
        status = controller.get_status_id(id_arquivo) if id_arquivo else {}
        #print(f'Preparando para visualizar id = {id_arquivo} com status = {status}')
        # print('dados: ', dados)
        res = {}
        if (not listar) and (not atualizar):
            if exemplo or controller.request_file_send(request_file = request):
                if (not token):
                    token = Util.get_token() 
                res = controller.processar_envio_arquivo(token = token,
                                                         exemplo_ou_request= exemplo or request,
                                                         gerar_img = gerar_img,
                                                         gerar_pdf = gerar_pdf ) 
            listar = True
        
        elif id_arquivo and atualizar and status.get('finalizado_img'):
           print(f'Preparando visualização html: {id_arquivo}') 
           res = controller.get_html_id(id_arquivo, 
                                        cabecalho = com_cabecalho,
                                        estampas = com_estampas,
                                        citacoes = com_citacoes)
        if res.get('erro'):
            res['html'] = controller.alerta(res['erro'])
        download_pdf = status.get('finalizado_pdf')
        download_md = status.get('finalizado_img')
        tipo_folha = res.get('tipo_folha','')
        filtro_md = ('ca' if com_cabecalho else '') + ' ' + \
                    ('ci' if com_citacoes else '') + ' ' + \
                    ('es' if com_estampas else '')
        # listagem de tarefas do usuário
        tarefas_usuario = []
        if listar:
            tarefas_usuario = controller.get_tarefas_usuario(token)
            #print(f'Tarefas do usuário {token}: ', len(tarefas_usuario), tarefas_usuario)
        if not any(tarefas_usuario):
           tarefas_usuario = False 
        tempo = round((datetime.now()-_ini).total_seconds(),2)
        
        return render_template("visualizar_ocr_arquivo.html", 
                titulo = titulo,
                token = token,
                listar = listar,
                atualizar = atualizar,
                texto_ocr = Markup(str(res.get('html',''))),
                id_arquivo = id_arquivo,
                download_pdf = download_pdf,
                download_md = download_md,
                tempo = f"{tempo:.3f} s",
                com_cabecalho = com_cabecalho,
                com_estampas = com_estampas,
                com_citacoes = com_citacoes,
                ignorar_cache = ignorar_cache,
                gerar_img = gerar_img,
                gerar_pdf = gerar_pdf,
                filtro_md = filtro_md,
                tipo_folha = tipo_folha,
                tarefas_usuario = tarefas_usuario,
                qtd_tarefas = len(tarefas_usuario) if type(tarefas_usuario) is list else 0,
                exemplos = get_lista_exemplos_view(''))
    except TemplateNotFound as e:
        return render_template_string(f'Página não encontrada: {e.message}')

def get_lista_exemplos_view(exemplo):
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

