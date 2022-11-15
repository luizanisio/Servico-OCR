# -*- coding: utf-8 -*-
'''
 Autor Luiz Anísio 12/11/2022
 Recebe um PDF e gera um novo PDF com camada de OCR sobre a imagem do PDF original
 
 pip install PyPDF2==2.11.1
 '''

import pytesseract
from pytesseract import Output
from PIL import features,Image
import PyPDF2
print('-----------------------------------')
print('- Verificação PIL libtiff: ', features.check('libtiff'))
print('-----------------------------------')

from pdf2image import convert_from_path
import io
import os

from util_imagem import cor_imagem
from util_pdf_compress import compress_pdf
import numpy as np

def imagens_pdf(arquivo_entrada='', dpi = 300, np_array = True):
    # extrair as imagens do PDF
    imagens = convert_from_path(arquivo_entrada, dpi=dpi)
    if np_array:
       return [np.array(_) for _ in imagens] 
    return imagens


def ocr_pdf(arquivo_entrada, arquivo_saida = None):
    temp = './temp/'
    if (not arquivo_entrada) or (not os.path.isfile(arquivo_entrada)):
        print('Arquivo de entrada não encontrado: ', arquivo_entrada)
        exit()
    if not arquivo_saida:
        arquivo_saida, _ = os.path.splitext(arquivo_entrada)
        arquivo_saida = f'{arquivo_entrada}_OCR_.pdf'

    pages = convert_from_path(arquivo_entrada, dpi=300)
    for image in pages:
        cor_imagem(image, False)

    pdf_writer = PyPDF2.PdfFileWriter()
    print(f'Ocerizando arquivo:', flush=True)
    print(f' - entrada: ', arquivo_entrada)
    print(f' - saída: ', arquivo_saida)
    for i, image in enumerate(pages):
        print(' - página', i+1, flush=True)
        image = cor_imagem(image)
        page = pytesseract.image_to_pdf_or_hocr(image,lang='por', extension='pdf')
        pdf = PyPDF2.PdfFileReader(io.BytesIO(page))
        pdf_writer.addPage(pdf.getPage(0))
    # export the searchable PDF to searchable.pdf
    print(' - gravando PDF com OCR', flush=True, end='')
    with open(arquivo_saida, "wb") as f:
        pdf_writer.write(f)
        print(' - ', round(os.path.getsize(arquivo_saida)/1000,2),'kBytes')
    return arquivo_saida

if __name__ == '__main__':
    import sys
    import os
    import json

    arquivo = ''
    arquivo_padrao = './exemplos/testes-extração.pdf'
    for i, arg in enumerate(sys.argv[1:]):
        print(f"- {arg}")
        if os.path.isfile(arg):
            arquivo = arg
            print(f'Arquivo encontrado: {arquivo}')
            break
    if not arquivo:
        arquivo = arquivo_padrao
        print(f'Arquivo padrão utilizado: {arquivo}')

    if not os.path.isfile(arquivo):
        print(f'Arquivo não encontrado: {arquivo}')
        exit()
    
    if not str(arquivo).lower().endswith('.pdf'):
       print('Não implementado para arquivos diferentes de PDF') 
       exit()

    arquivo_saida = ocr_pdf(arquivo)    
    compress_pdf(arquivo_saida, arquivo_saida)


    
