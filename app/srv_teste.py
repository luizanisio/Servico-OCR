# -*- coding: utf-8 -*-

from flask import Flask, jsonify, request, render_template
from flask import render_template_string, redirect, url_for #, Markup

app = Flask(__name__, template_folder='./templates')

PATH_API = '/'


###################################################################
# limpeza do cache
#@app.route(f'{PATH_API}health', methods=['GET'])
@app.route('/', methods=['GET'])
@app.route('/health', methods=['GET'])
def get_health():
    return jsonify({'ok':'ok'})


#############################################################################
#############################################################################

if __name__ == "__main__":
    # carrega as regras
    #carregar_exemplos()
    print( '#########################################')
    print( 'Iniciando o serviço')
    print( '-----------------------------------------')
    app.run(host='0.0.0.0', debug=False,port=8000)

