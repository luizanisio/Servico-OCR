# Serviço OCR
- Prova de Conceito para ocerização de imagens e PDFs usando Tesseract em português

## Projeto implementado em python, com o uso do Tesseract
- O objetivo é analisar qualidade, performance e regiões identificadas pelo Tesseract para permitir a criação de regras ou treinamento de modelos para identificar regiões como Citações, Estampas laterais, Cabeçalho e Rodapé. A identificação pode ser feita por regras simples, como margens em páginas padronizadas (A4, Carta, Legal etc). E também pode ser identificado por repetições de textos em áreas específicas, como cabeçalhos e rodapés.

## O que está disponível
- Foi criado um serviço flask que recebe imagens ou PDFs e processa eles em batch, permitindo acompanhar a fila de tarefas e visualizar os arquivos da extração (html) ou baixar uma versão Markdown ou PDF da análise realizada.
- As regiões estão sendo identificadas por posicionamento (estampas e citações) ou repetição e posicionamento (cabeçalhos e rodapés).
- A tela apresenta o motivo da identificação do tipo da região
- Pode-se filtrar o retorno, removendo regiões não desejadas
- O arquivo `config.json` contém configurações do serviço como o nome das pastas, DPIs para as análises, número de workers, dentre outros. Caso não exista, ele será criado com o padrão de cada configuração.
- O campo `token` do serviço é usado para listar as tarefas do usuário, podendo ser digitado livremente ou será criado ao enviar um arquivo a primeira vez. A ideia é o usuário enviar vários arquivos no mesmo token. O usuário precisa dele para acompanhar as tarefas enviadas. Não é garantida a segurança com esse token, apenas restringe um pouco o livre acesso às tarefas entre usuários pois é só uma poc.
- O serviço instancia a classe `ProcessarOcr` disponível no arquivo `util_processar_pasta.py` para processar continuamente as tarefas de OCR enviadas pela tela.
- Pode-se acionar o serviço de processamento contínuo independente do serviço flask chamando `python util_processar_pasta.py` usando o `config.json` para ajustar as configurações desejadas.
  - O processo em background realiza o OCR de PDF para PDF (pasta entrada) ou PDF/PNG/JPG/TIF para HTML/MD (pasta entrada_img) e atualiza o status das tarefas em arquivos `nome_arquivo_entrada.status.json`
    - .\entrada
    - .\entrada_img (processa imagens ou PDFs com a saída no formato json de análise, MD e/ou HTML
    - .\processamento
    - .\processamento_img
    - .\erro
    - .\erro_img
    - .\saida
    - .\saida_img
  
> 💡 <sub>Nota: é feito um controle de todos os arquivos enviados e status de cada um para acompanhamento, tanto no caso de PDF para PDF como PDF para MD/HTML. O arquivo fica na pasta `saida` ou `saida_img` dependendo do tipo de processamento solicitado.<br> Caso um arquivo seja enviado novamente para OCR, será identificado pelo hash e não será processado duas vezes. Para sobrepor o processamento anterior, basta selecionar a opção "ignorar-cache" ao enviar o arquivo.</sub>

![exemplo recorte tela serviço](./img/servico_ocr_20230223_3.png?raw=true "Exemplo recorte tela serviço - HTML e PDF")

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
  - em `util_ocr.py` tem um exemplo funcional, falta apresentar no serviço
- exportação de trechos para fine tunning do Tesseract
- acionamento por api para uso em outros projetos
- criação de componente para reaproveitamento
- aplicação de extrações de entidade nas caixas de texto, respeitando o posicionamento
- identificar início e fim de caracteres de cada box, para melhor posicionamento de extrações
- melhor compactação de arquivos PDF com OCR
- análise se o PDF de entrada precisa de OCR ou pode ser analisado (estampas, cabeçalho, rodapé, citações) com o texto existente
- possibilidade de recriar a camada de OCR no pdf original sem precisar criar um novo que pode ficar maior

## dependências para o linux - Testado WSL com Debian
- sudo apt-get update

- para a manipulação de imagens pelo Pillow
  - sudo apt-get install poppler-utils 

- tesseract
  - sudo apt-get install tesseract-ocr tesseract-ocr-por  
  - sudo apt-get install libtesseract-dev -y
  - sudo apt-get install -y libleptonica-dev 

## Ghostscript para compactação
- nem sempre resolve compactar o PDF gerado, mas para imagens muito simples (PB) pode compactar bem
- é usado pelo serviço de processamento em background após gerar um PDF com camada de OCR
  - sudo apt-get install ghostscript
