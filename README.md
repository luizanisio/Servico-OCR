# Serviço OCR
- Prova de Conceito para ocerização de imagens e PDFs usando Tesseract em português

## Projeto implementado em python, com o uso do Tesseract
- O objetivo é analisar qualidade, performance e regiões identificadas pelo Tesseract para permitir a criação de regras ou treinamento de modelos para identificar regiões como Citações, Estampas laterais, Cabeçalho e Rodapé. A identificação pode ser feita por regras simples, como margens em páginas padronizadas (A4, Carta, Legal etc). E também pode ser identificado por repetições de textos em áreas específicas, como cabeçalhos e rodapés.

## O que está disponível
- Foi criado um serviço flask que recebe imagens ou PDFs e retorna uma página HTML com as regiões identificadas.
- As regiões estão sendo identificadas por posicionamento (estampas e citações) ou repetição e posicionamento (cabeçalhos e rodapés).
- A tela apresenta o motivo da identificação da região
- Pode-se filtrar o retorno, removendo regiões não desejadas

![exemplo recorte tela serviço](./img/servico_ocr.png?raw=true "Exemplo recorte tela serviço")

## TODO
- apresentação da análise feita nas imagens enviadas para o Tesseract
- exportação de trechos para fine tunning do Tesseract
- acionamento por api para uso em outros projetos
- criação de componente para reaproveitamento
- aplicação de extrações de entidade nas caixas de texto, respeitando o posicionamento
- identificar início e fim de caracteres de cada box, para melhor posicionamento de extrações

## dependências para o linux - Testado WSL com Debian
- sudo apt-get update

- para a manipulação de imagens pelo Pillow
  - sudo apt-get install poppler-utils 

- para opencv
  - sudo apt-get install ffmpeg libsm6 libxext6  -y  
  - sudo apt-get install libgl1

- tesseract
  - sudo apt-get install tesseract-ocr tesseract-ocr-por  

## Ghostscript para compactação
- nem sempre resolve compactar o PDF gerado, mas para imagens muito simples (PB) pode compactar bem
- vai ser usado quando gerar um PDF de imagem ou de outro PDF
  - sudo apt-get install ghostscript
