# Serviço OCR
- Prova de Conceito para ocerização de imagens e PDFs usando Tesseract em português

## Projeto implementado em python, com o uso do Tesseract
- O objetivo é analisar qualidade, performance e regiões identificadas pelo Tesseract para permitir a criação de regras ou treinamento de modelos para identificar regiões como Citações, Estampas laterais, Cabeçalho e Rodapé. A identificação pode ser feita por regras simples, como margens em páginas padronizadas (A4, Carta, Legal etc). E também pode ser identificado por repetições de textos em áreas específicas, como cabeçalhos e rodapés.

## O que está disponível
- Foi criado um serviço flask que recebe imagens ou PDFs e retorna uma página HTML com as regiões identificadas.
- As regiões estão sendo identificadas por posicionamento (estampas e citações) ou repetição e posicionamento (cabeçalhos e rodapés).
- A tela apresenta o motivo da identificação da região
- Pode-se filtrar o retorno, removendo regiões não desejadas
- Processo em background realizando OCR de PDF para PDF e atualizando o status 
  - pode-se usar o arquivo `util_processar_pasta.py` para realizar um processamento contínuo do tipo pasta de entrada e pasta de saída:
    - .\entrada
    - .\processamento
    - .\erro
    - .\saida
  - `python util_processar_pasta.py` 
> 💡 <sub>Nota: será feito um controle de todos os arquivos enviados e status de cada um para acompanhamento, tanto no caso de PDF para PDF como PDF para HTML</sub>

![exemplo recorte tela serviço](./img/servico_ocr_2.png?raw=true "Exemplo recorte tela serviço - HTML e PDF")

## Exemplo de extração e metadados gerados
```
 [ {'pagina'     : 0 ...n número da página 
    'box'        : 0 ...n reinicia a cada página
    'id'         : 0 ...n até o último box (na ordem para leitura)
    'pagina_la' : [500,75], -> largura e altura da página
    'pagina_tipo' : A4, Legal .. -> tipo da página identificado
    'box_xyla'     : [10,14,30,45], -> x,y  largura, altura da caixa
    'alt_linhas'   : 23, -> média da altura das linhas do box
    'alt_linhas_med' : 30  -> média da altura das linhas da página
    'qtd_linhas'   : 3,  -> linhas da caixa
    'qtd_boxes'    : 2,  -> boxes na página
    'qtd_letras'   : 44, -> letras únicas
    'qtd_palavras' : 22, -> palavras únicas
    'margens_edsi' : [5,5,3,7] -> margens até a caixa mais próxima - esquerda, direita, superior, inferior
    'bordas'     : [D,E,S,I..] -> Direita, Esquerda, Superior, Inferior (está em uma ou mais bordas)
    'texto' : 'bla bla bla',
    'tipo_sugerido': ... descrição do motivo do tipo sugerido (bordas, repetição etc)
    'tipo': C, R, T... Cabeçalho, Rodapé, Título, Folha, Citação ...
     },
  ]
```

## TODO
- apresentação da análise feita nas imagens enviadas para o Tesseract
- exportação de trechos para fine tunning do Tesseract
- acionamento por api para uso em outros projetos
- criação de componente para reaproveitamento
- aplicação de extrações de entidade nas caixas de texto, respeitando o posicionamento
- identificar início e fim de caracteres de cada box, para melhor posicionamento de extrações
- melhor compactação de arquivos PDF com OCR

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
- é usado pelo serviço de processamento em background após gerar um PDF com camada de OCR
  - sudo apt-get install ghostscript
