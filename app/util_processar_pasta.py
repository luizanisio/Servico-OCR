# -*- coding: utf-8 -*-

'''
 Autor Luiz Anísio 19/11/2022
 Abre um worker para cada processador da máquina e processa os pdfs da pasta de entrada,
 envia o resultado para a pasta de saída e os erros para a pasta de erros
 n_workers = -1 ==> número de CPUs -1
 n_workers = 0 ==> número de CPUs
 n_workers = ? ==> o número informado
 max_workers = informar um máximo de workers - serve para deploy em serviços como um rancher com a máquina física compartilhada

 Um arquivo de status é criado para cada arquivo de entrada:
   - ..saida/nome_do_arquivo.status.json
   - ..saida_ims/nome_do_arquivo.status.json

 Exemplo em: 
    if __name__ == '__main__': ....
 '''

from util_fila import WorkerQueue, SafeThread
from util_pdf_compress import compress_pdf
from util_pdf_ocr import ocr_pdf
from util_ocr import AnaliseImagensOCR
from util_markdown import arquivo_aimg_2_md
from util_html import arquivo_aimg_2_html
from util_pdf_ocr import imagens_pdf

from datetime import datetime
import shutil
import time
import os
import json
from util import Util
from filelock import FileLock
from copy import deepcopy

TEMPO_LOCK = 60

class ProcessarOcr():
    ARQUIVOS_PARADA = ['stop', 'parar','finalizar']
    TIPOS_IMAGENS = ['tiff','jpg','png','tif','pdf']
    SUFIXO_STATUS = '.status.json'

    def __init__(self, iniciar = True):
        self.dthr_limpeza = None
        self.status_geral = {'dthr' : Util.data_hora_str(), 'status':'configurando serviço'}
        self.config = self.carregar_config()
        self.entrada = self.config.get('xocr_entrada','./ocr_entrada')
        self.entrada_img = f'{self.entrada}_img'
        self.saida = self.config.get('xocr_saida','./ocr_saida')
        self.saida_img = f'{self.saida}_img'
        self.processando = self.config.get('xprocessando',r'./ocr_processando')
        self.processando_img = f'{self.processando}_img'
        self.erro = self.config.get('xerro',r'./ocr_erro')
        self.erro_img = f'{self.erro}_img'
        self.__processar_continuamente__ = True
        self.fila = WorkerQueue(n_workers=self.config.get('n_workers',-1), 
                                max_workers = self.config.get('max_workers',0),
                                retorno = False, 
                                iniciar_workers=True)

        for pasta in self.pastas_pdf() + self.pastas_img():
            os.makedirs(pasta, exist_ok=True)
        self.status_geral = {'dthr' : Util.data_hora_str(), 'status':'serviço pronto para iniciar'}
        self.gravar_status_geral(True)
        if iniciar:
            try:
               self.processar_continuamente()
            except Exception as e:
               self.status_geral = {'dthr' : Util.data_hora_str(), 'status':'erro no serviço', 'erro' : str(e)} 

    # configurações básicas do serviço
    # o arquivo é criado se não existir
    CONFIG_PADRAO = {"gerar_md" : True, "gerar_html" : True, 
                     "resolucao_img" : 300, 
                     "resolucao_pdf" : 300, 
                     "n_workers" : -1, "max_workers" : 0,
                     "entrada" : "./ocr_entrada", 
                     "saida" : "./ocr_saida", 
                     "processando" : "./ocr_processando",
                     "erro" : "./ocr_erro",
                     "LEIA-ME": {"entrada" : "./ocr_entrada", 
                                 "saida" : "./ocr_saida", 
                                 "processando" : "./ocr_processando",
                                 "erro" : "./ocr_erro",
                                 "gerar_md": "criar um arquivo MD na pasta de saida_img após gerar análise img de entrada",
                                 "gerar_html": "criar um arquivo HTML na pasta de saida_img após gerar análise img de entrada",
                                 "resolução_img": "resolução da imagem gerada do PDF de entrada para gerar a análise/extração dos textos",
                                 "resolução_pdf": "resolução da imagem gerada do PDF com camada de OCR",
                                 "n_workers" : "número de workers >> -1 para CPUs -1, 0 para todas as CPUS ou um valor específico",
                                 "max_workers" : "máximo de workers caso a máquina tenha um número maior que o que se deseja disponibilizar"}
                    }
    def carregar_config(self):
        arquivo = './config.json'
        config = deepcopy(self.CONFIG_PADRAO)
        del config['LEIA-ME']
        try:
            if os.path.isfile(arquivo):
                with open(arquivo, 'r') as f:
                     dados = json.loads(f.read())
                gravar = False
                for chave in config.keys():
                    if not chave in dados:
                       dados[chave] = config[chave]
                       gravar = True
                # config incompleto - grava as opções default
                if gravar:
                   with open(arquivo, 'w') as f:
                        f.write(json.dumps(self.CONFIG_PADRAO, indent=2)) 
                return dados
        except:
            pass 
        # grava o config padrão se não existir ou se der erro para abrir o config
        print('* CONFIG inexistente ou inconsistente - gravado config padrão')
        with open(arquivo, 'w') as f:
             f.write(json.dumps(self.CONFIG_PADRAO, indent=2)) 
        return config

    def pastas_pdf(self):
        # ordem de prioridade do status
        return [self.processando, self.entrada, self.saida, self.erro]

    def pastas_img(self):
        # ordem de prioridade do status
        return [self.processando_img, self.entrada_img, self.saida_img, self.erro_img]

    def pastas(self):
        return self.pastas_pdf() + self.pastas_img()

    @classmethod
    def verifica_tipo(cls, tipo):
        if tipo not in ('pdf','img'):
           raise Exception('O tipo do análise do arquivo deve ser definido como "pdf" ou "img"') 

    # método de classe para ser usado pelos métodos em processos isolados
    @classmethod
    def nome_arquivo_status(cls, arquivo, pasta_saida):
        ''' recebe o nome do arquivo analisado (pdf, imagem, etc) e a pasta de saída e 
            devolve o nome do arquivo de status na pasta de saída
            ex. ..saida/arquivo.status.json'''
        _arquivo = os.path.splitext(os.path.split(arquivo)[1])[0]
        #print(f'BUSCANDO NOME {arquivo} e devolvendo {_arquivo}')
        return os.path.join(pasta_saida, f'{_arquivo}{cls.SUFIXO_STATUS}')

    # método de classe para ser usado pelos métodos em processos isolados
    @classmethod
    def atualizar_status(cls, arquivo, dados, pasta_saida):
        arquivo_status = cls.nome_arquivo_status(arquivo, pasta_saida)
        status = Util.ler_json(arquivo_status)
        if any(status):
           status.update(dados)
        else:
           status = dados 
           status['dthr_criacao_status'] = Util.data_hora_str()
        Util.gravar_json(arquivo_status, status)
        return status
    
    # método de classe para ser usado pelos métodos em processos isolados
    @classmethod
    def atualizar_status_txt(cls, arquivo, pasta_saida, tipo, status='atualizando...', tamanho = '', final = False):
        cls.verifica_tipo(tipo)
        dados = {f'status_{tipo}': status, f'dthr_{tipo}': Util.data_hora_str()}
        if tamanho == 'i':
           dados[f'tamanho_inicial_{tipo}'] = round(os.path.getsize(arquivo)/1024,2)
        elif tamanho == 'f':
           dados[f'tamanho_final_{tipo}'] = round(os.path.getsize(arquivo)/1024,2)
        dados[f'finalizado_{tipo}'] = final
        return cls.atualizar_status(arquivo=arquivo, dados= dados, pasta_saida=pasta_saida)

    # o serviço que coloca o arquivo na pasta pode gerar um arquivo de status com os dados 
    # do arquivo colocado para controle depois
    # método de classe para ser usado pelos métodos em processos isolados
    @classmethod
    def status_arquivo(cls, arquivo, pastas_saida):
        if type(pastas_saida) in (list, tuple):
           dados = {}
           for pasta in pastas_saida:
               dados.update(cls.status_arquivo(arquivo, pasta))
           return dados
        if type(pastas_saida) is str:
            # arquivo único
            _arquivo = cls.nome_arquivo_status(arquivo, pastas_saida)
            #print(f'Carregando status do arquivo: {arquivo} como ({_arquivo})')
            return Util.ler_json(_arquivo, dict({}) )
        return dict({})

    def status_geral_txt(self):
        return ', '.join([f'{c}:{v}' for c,v in self.status_geral.items()])

    # atualiza a cada 1 min o arquivo de status
    def gravar_status_geral(self, forcado = False):
        dthr_status = self.data_hora_status_geral()
        if dthr_status and not forcado:
           if (datetime.now() - dthr_status).total_seconds() < 60:
              # print(f'Status geral não gravado... {dthr_status}')
              return
        for pasta in [self.saida, self.saida_img]:
            arquivo = os.path.join(pasta, 'status.json')
            _status = deepcopy(self.status_geral)
            _status.update(self.config)
            Util.gravar_json(arquivo, _status)

    # pode ser usado para avaliar a saúdo do serviço
    def data_hora_status_geral(self):
        for pasta in [self.saida, self.saida_img]:
            arquivo = os.path.join(pasta, 'status.json')
            if os.path.isfile(arquivo):
                return Util.data_arquivo(arquivo)
        return None

    # verifica se a data do arquivo status está dentro de um limite de tempo
    def health_check(self, tempo_saude_minutos = 5):
        dthr_status = self.data_hora_status_geral()
        if not dthr_status:
            return {'msg_erro': 'sem arquivo de status geral'}
        if (datetime.now() - dthr_status).total_seconds() <= tempo_saude_minutos * 60:
            return self.status_geral
        return {'msg_erro': f'status do serviço com tempo superior a {tempo_saude_minutos} minutos'}

    @classmethod
    def class_health_check(cls, pastas_saida = [], tempo_saude_minutos = 5):
        dthr_status = None
        dados = None
        for pasta in pastas_saida:
            arquivo = os.path.join(pasta, 'status.json')
            if os.path.isfile(arquivo):
                dthr_status = Util.data_arquivo(arquivo)
                dados = Util.ler_json(arquivo=arquivo, padrao = {'msg_erro': 'arquivo de status não carregado'})
                break
        if not dthr_status:
            return {'msg_erro': 'sem arquivo de status '}
        if (datetime.now() - dthr_status).total_seconds() <= tempo_saude_minutos * 60:
            return dados

    def parar(self):
        self.__processar_continuamente__ = False

    def mover_pasta_entrada(self, tipo):
        processando = self.processando if tipo == 'pdf' else self.processando_img
        entrada = self.entrada if tipo == 'pdf' else self.entrada_img
        tipos = ['pdf'] if tipo == 'pdf' else self.TIPOS_IMAGENS
        for tp in tipos:
            arquivos_processando = Util.listar_arquivos(processando, tp)
            if any(arquivos_processando):
                print(f'Movendo {len(arquivos_processando)} arquivo(s) em processamento para a pasta de entrada ...')
                for a in arquivos_processando:
                    try:
                        print(f'- Movendo {a} para {entrada}') 
                        self.mover_entre_pastas(a, entrada)
                    except:
                        print(f'ERRO: não foi possível mover {a} para {entrada} para novo processamento')

    def processar_continuamente(self):
        global TEMPO_LOCK
        pastas_parada = [self.entrada, self.saida, self.entrada, './']
        self.status_geral = {'dthr' : Util.data_hora_str(), 'status':'iniciando processamento contínuo'}
        # ao reiniciar o processamento, move os arquivos que podem ter tido o processamento interrompido
        # para a pasta de entrada para serem processados novamente (pdf e/ou img)
        self.mover_pasta_entrada('pdf')
        self.mover_pasta_entrada('img')
        
        # inicia a avaliação da pasta de entrada
        fila_cheia_timer = 1
        primeira_rodada = True # para gravar o status geral
        rodada_anterior_vazia = False
        while self.__processar_continuamente__:
            # arquivos para parar o processamento
            # se existir um desses arquivos em uma das pastas, para o serviço
            for a in self.ARQUIVOS_PARADA:
                for p in pastas_parada:
                    self.__processar_continuamente__ = not os.path.isfile(os.path.join(p, a))
                    if not self.__processar_continuamente__:
                        print(f'Arquivo de parada encontrado: "{os.path.join(p, a)}"')
                        break
            # encontrar arquivos e processar
            arquivos_pdf = Util.listar_arquivos(self.entrada, 'pdf')
            arquivos_img = []
            for tipo in self.TIPOS_IMAGENS:
                arquivos_img += Util.listar_arquivos(self.entrada_img, tipo)
            qtd_arquivos_saida = len(Util.listar_arquivos(self.saida, 'pdf')) 
            qtd_arquivos_erro = len(Util.listar_arquivos(self.erro, 'pdf'))
            qtd_arquivos_processando = len(Util.listar_arquivos(self.erro, 'pdf'))
            for tipo in self.TIPOS_IMAGENS:
                qtd_arquivos_saida += len(Util.listar_arquivos(self.saida_img, tipo))
                qtd_arquivos_erro += len(Util.listar_arquivos(self.erro_img, tipo))
                qtd_arquivos_processando += len(Util.listar_arquivos(self.processando_img, tipo))
            # cria uma lista de arquivos e os tipos de processamento
            arquivos = [('pdf', _, self.processando, self.erro, self.saida) for _ in arquivos_pdf]
            arquivos += [('img', _, self.processando_img, self.erro_img, self.saida_img) for _ in arquivos_img]
            qtd_pasta = len(arquivos)
            self.status_geral = {'dthr' : Util.data_hora_str(), 'entrada' : qtd_pasta, 'saida': qtd_arquivos_saida,
                            'processamento': qtd_arquivos_processando, 'erro': qtd_arquivos_erro,
                            'workers' : self.fila.n_workers, 'tarefas' : self.fila.tasks_entrada(),
                            'status' : 'processando continuamente'}
            # se não tinha nada e entraram novos arquivos, 
            # força atualizar o status geral
            if qtd_pasta > 0 and rodada_anterior_vazia:
               primeira_rodada = True 
            rodada_anterior_vazia = qtd_pasta == 0
            self.gravar_status_geral(primeira_rodada)
            primeira_rodada = False
            for tipo, entrada, processando, erro, saida in arquivos:
                # se a fila já está cheia, aguarda para pegar mais da pasta
                if self.fila.tasks_entrada() > self.fila.n_workers * 1.5:
                    str_now = datetime.now().strftime("%H:%M:%S")
                    print(f'Fila de processamento cheia: \n -', self.status_geral_txt())
                    time.sleep(fila_cheia_timer) 
                    if fila_cheia_timer < TEMPO_LOCK:
                       fila_cheia_timer += 2
                    break
                # arquivo incompleto - tamanho zero (o tamanho zero pode ser um arquivo em gravação ainda)
                if (not os.path.isfile(entrada)):
                    continue
                if os.path.getsize(entrada) == 0:
                    self.atualizar_status_txt(entrada,pasta_saida=saida, tipo=tipo, status='arquivo na pasta de entrada com tamanho zero', tamanho = 'i')
                    self.mover_entre_pastas(entrada, erro)
                    continue
                qtd_pasta -= 1
                fila_cheia_timer = 1
                # o arquivo de lock serve para os processos não pegarem o arquivo ao mesmo tempo
                _controle = f'{entrada}.lc'
                lock_controle = FileLock(_controle, TEMPO_LOCK)
                with lock_controle:
                    if os.path.isfile(entrada):
                       print(f'Processando entrada: {entrada}') 
                       _arq_processando = os.path.join(processando, os.path.split(entrada)[1])
                       if os.path.isfile(_arq_processando):
                          try:
                             # se está processando, tenta remover para usar o da entrada novamente
                             # se não remover, mantém na entrada 
                             self.mover_entre_pastas(_arq_processando, None)
                          except Exception as er:
                             print(f'ERRO: não foi possível remover {_arq_processando} para novo processamento >> ERRO: {er}')
                             continue   
                       try: 
                          self.mover_entre_pastas(entrada, processando)
                       except Exception as er:
                           print(f'ERRO: não foi possível mover {entrada} para novo processamento >> ERRO: {er}')
                           continue   
                       if tipo == 'pdf':
                          self.atualizar_status_txt(_arq_processando,pasta_saida=saida, tipo='pdf', status='enviado para a fila de processamento', tamanho = 'i')
                          self.fila(processar_arquivo, (_arq_processando, saida, erro, self.config.get('resolucao_pdf', 300)))
                       else:
                          self.atualizar_status_txt(_arq_processando,pasta_saida=saida, tipo='img', status='enviado para a fila de processamento', tamanho = 'i')
                          self.fila(processar_analise, (_arq_processando, saida, erro, 
                                                        self.config.get('gerar_md', 300),
                                                        self.config.get('gerar_html', 300),
                                                        self.config.get('resolucao_img', 300)))
                          
            # remove arquivos de controle com mais de 1 minuto para nova análise do lock
            Util.limpar_controles(self.entrada, minutos=TEMPO_LOCK+10)
            self.limpar_temporarios()
            time.sleep(0.5)

    # limpa os arquivos processados em 10 dias
    def limpar_temporarios(self):
        # limpa os temporários a cada 10 min
        # cada temporário tem uma data de limite
        if (self.dthr_limpeza is None) or (datetime.now() - self.dthr_limpeza).total_seconds() > 600:
            self.dthr_limpeza = datetime.now()
            Util.limpar_temporarios()
            Util.limpar_temporarios(pasta = self.erro, dias = 2)
            Util.limpar_temporarios(pasta = self.erro_img, dias = 2)
            Util.limpar_temporarios(pasta = self.saida, dias = 10)
            Util.limpar_temporarios(pasta = self.saida_img, dias = 10)

    # precisa de ser um método de classe pois será chamado pelo processo
    @classmethod
    def mover_entre_pastas(cls, arquivo, destino):
        if os.path.isfile(arquivo):
           origem, nm_arquivo = os.path.split(arquivo)
           mover_para = os.path.join(destino, nm_arquivo) if destino else None
           if mover_para:
              #print(f'---- movendo {arquivo} >> {destino}')
              shutil.move(arquivo, mover_para)
           else:
              #print(f'---- removendo {origem}')
              os.remove(arquivo)
        return

    # precisa de ser um método de classe pois será chamado pelo processo
    @classmethod
    def e_arquivo_pdf(cls, arquivo):
        return arquivo.lower().endswith('.pdf')

    @classmethod
    def nome_arquivo_analise(cls,arquivo, pasta_saida):
        nm_entrada = os.path.split(arquivo)[1]
        nm_saida = os.path.splitext(nm_entrada)[0] + '.json'
        return os.path.join(pasta_saida, nm_saida)


##################################################################
# processar um arquivo de análise dentro de cada worker
def processar_analise(arquivos):
    entrada, pasta_saida, pasta_erro, gerar_md, gerar_html, dpi = arquivos
    nm_entrada = os.path.split(entrada)[1]
    nm_analise = ProcessarOcr.nome_arquivo_analise(entrada, pasta_saida)
    nm_erro = os.path.join(pasta_erro, nm_entrada)
    saida_erro_txt = os.path.splitext(nm_erro)[0] + '.txt'
    try:
        ProcessarOcr.atualizar_status_txt(entrada,pasta_saida=pasta_saida, tipo='img', status='Processamento iniciado')
        print(f'>>> PROCESSANDO ANÁLISE DE ARQUIVO: {entrada} <<<')
        if ProcessarOcr.e_arquivo_pdf(entrada):
           imagens = imagens_pdf(entrada, dpi = dpi )
        else:
           imagens = entrada
        analise = AnaliseImagensOCR(img=imagens)
        Util.gravar_json(nm_analise, analise.dados())
        ProcessarOcr.atualizar_status_txt(nm_analise,pasta_saida=pasta_saida, tipo='img', status='Processamento concluído', final=True)
        print(f'>>> ANÁLISE DE ARQUIVO PROCESSADA: {entrada} --> {nm_analise} <<<')
    except Exception as e:
        # move o arquivo para a pasta de erro
        print(f'>>> ERRO DE PROCESSAMENTO: {entrada} --> {nm_erro} <<<')
        ProcessarOcr.atualizar_status_txt(entrada,pasta_saida=pasta_saida, tipo='img', status=f'Erro: {str(e)[:30]}...')
        ProcessarOcr.mover_entre_pastas(entrada, pasta_erro)
        try:
            with open(saida_erro_txt, 'w') as fe:
                 fe.write(f'ERRO: {e}')
        except Exception as ee:
            print(f'ERRO processar_arquivo: não foi possível criar o arquivo com o a mensagem de erro de processamento {ee}, erro de processamento: {e}')
    if os.path.isfile(entrada):
       os.remove(entrada)
    if gerar_md:
       arquivo_aimg_2_md(nm_analise)
    if gerar_html:
       arquivo_aimg_2_html(nm_analise)


##################################################################
# processamento de um arquivo dentro de cada worker
def processar_arquivo(arquivos):
    entrada, pasta_saida, pasta_erro, dpi= arquivos
    nm_entrada = os.path.split(entrada)[1]
    saida = os.path.join(pasta_saida, nm_entrada)
    erro = os.path.join(pasta_erro, nm_entrada)
    saida_ngs = os.path.splitext(saida)[0] + '_ngs_.pdf'
    saida_erro_txt = os.path.splitext(erro)[0] + '.txt'
    try:
        ProcessarOcr.atualizar_status_txt(entrada, pasta_saida=pasta_saida, tipo='pdf', status='Processamento iniciado', tamanho='i')
        print(f'>>> PROCESSANDO ARQUIVO: {entrada} <<<')
        ocr_pdf(arquivo_entrada=entrada, arquivo_saida=saida_ngs, dpi = dpi)    
        ProcessarOcr.atualizar_status_txt(entrada, pasta_saida=pasta_saida, tipo='pdf', status='OCR concluído - enviado para compactação', tamanho='f')
        print(f'>>> ARQUIVO PROCESSADO: {entrada} --> {saida} <<<')
    except Exception as e:
        # move o arquivo para a pasta de erro
        print(f'>>> ERRO DE PROCESSAMENTO: {entrada} --> {erro} <<<')
        ProcessarOcr.atualizar_status_txt(entrada,pasta_saida=pasta_saida, tipo='pdf', status=f'Erro: {str(e)[:30]}...')
        ProcessarOcr.mover_entre_pastas(entrada, pasta_erro)
        try:
            with open(saida_erro_txt, 'w') as fe:
                    fe.write(f'ERRO: {e}')
        except Exception as ee:
            print(f'ERRO processar_arquivo: não foi possível criar o arquivo com o a mensagem de erro de processamento {ee}, erro de processamento: {e}')
        return
    try:
        ProcessarOcr.atualizar_status_txt(entrada,pasta_saida=pasta_saida, tipo='pdf', status=f'Iniciando compactação')
        r = compress_pdf(saida_ngs, saida)
        
        # mantém a melhor compressão
        if r >0:
           print(f'>>> ARQUIVO COMPRIMIDO: {entrada} --> {saida} --> ratio = {round(r,2)}<<<')
           os.remove(saida_ngs)
           compactado = f' - compactado {r:.2f}'
        else:
           print(f'>>> ARQUIVO COMPRIMIDO E IGNORADO: {entrada} --> {saida} --> ratio = {round(r,2)}<<<')
           os.remove(saida) 
           shutil.move(saida_ngs, saida)
           compactado = ' - compactação ignorada'
    except Exception as e:
        print('ERRO processar_arquivo: não foi possível usar o ghostscript para compactar o arquivo de saída')
        # o arquivo de saída fica sem compressão
        shutil.move(saida_ngs, saida)
        compactado = ' - compactação impossível'
    os.remove(entrada)
    ProcessarOcr.atualizar_status_txt(saida,pasta_saida=pasta_saida, tipo='pdf', status=f'Processamento concluído{compactado}', tamanho='f', final=True)

class ProcessarOcrThread():
    THREAD_ATIVA = None
    SERVICO = None
    def __init__(self):
        self.servico()

    @ classmethod
    def finalizar(cls):
        if cls.SERVICO:
           cls.SERVICO.parar()
        if cls.THREAD_ATIVA:
           cls.THREAD_ATIVA.join()
           cls.THREAD_ATIVA = None

    @classmethod
    def servico(cls):
        if not cls.SERVICO:
            print('ProcessarOcrThread: iniciando thread de processamento de pastas')
            cls.SERVICO = ProcessarOcr(iniciar=False)
            cls.THREAD_ATIVA = SafeThread(target = cls.SERVICO.processar_continuamente)
            cls.THREAD_ATIVA.start()
            print('----------------------------------------------------------------------------')
            print('- SERVIÇO DE OCR ')
            print('- Config do serviço: ', ', '.join([f'{c}={v}' for c,v in cls.SERVICO.config.items()]))
            #print('- Pastas do serviço: ', cls.SERVICO.pastas())
            print('----------------------------------------------------------------------------')
        return cls.SERVICO

if __name__ == '__main__':
    processar_ocr = ProcessarOcr()
    