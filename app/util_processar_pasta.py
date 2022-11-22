# -*- coding: utf-8 -*-

'''
 Autor Luiz Anísio 19/11/2022
 Abre um worker para cada processador da máquina e processa os pdfs da pasta de entrada,
 envia o resultado para a pasta de saída e os erros para a pasta de erros
 n_workers = -1 ==> número de CPUs -1
 n_workers = 0 ==> número de CPUs
 n_workers = ? ==> o número informado

 Exemplo em: 
    if __name__ == '__main__': ....
 '''

from util_fila import WorkerQueue, SafeThread
from util_pdf_compress import compress_pdf
from util_pdf_ocr import ocr_pdf
from datetime import datetime
import shutil
import time
import os
import json
from util import Util
from filelock import FileLock

TEMPO_LOCK = 60

class ProcessarOcr():
    ARQUIVOS_PARADA = ['stop', 'parar','finalizar']

    def __init__(self, entrada = './ocr_entrada', 
                       saida = './ocr_saida', 
                       processando = './ocr_processando',
                       erro = './ocr_erro',
                       n_workers = -1,
                       iniciar = True):
        self.entrada = entrada
        self.saida = saida 
        self.processando = processando
        self.erro = erro
        self.__processar_continuamente__ = True
        self.fila = WorkerQueue(n_workers=n_workers, 
                                retorno = False, 
                                iniciar_workers=True)

        os.makedirs(self.entrada, exist_ok=True)
        os.makedirs(self.saida, exist_ok=True)
        os.makedirs(self.processando, exist_ok=True)
        os.makedirs(self.erro, exist_ok=True)
        if iniciar:
            self.processar_continuamente()

    def pastas(self):
        # ordem de prioridade do status
        return [self.processando, self.entrada, self.saida, self.erro]

    # vai retornar o local do arquivo PDF encontrado para o arquivo ou hash enviado
    def encontrar_arquivo_nas_pastas(self, arquivo):
        _arquivo = os.path.split(arquivo)[1]
        _arquivo = os.path.splitext(_arquivo)[0]
        _arquivo = f'{_arquivo}.pdf'
        # procura o arquivo e arquivo.pdf
        for p in self.pastas():
            if os.path.isfile(os.path.join(p, f'{_arquivo}')):
               return os.path.join(p, _arquivo)
        return None

    @staticmethod
    def atualizar_status(cls, arquivo, dados):
        arquivo_status = os.path.splitext(arquivo)[0] + '.json'
        status = Util.ler_json(arquivo_status)
        status.update(dados)
        Util.gravar_json(arquivo_status)
        return status

    def status_arquivo(self, arquivo, fixo = False):
        if not arquivo:
            return {}
        if not fixo:
            # procura o arquivo nas pastas
            arquivo = self.encontrar_arquivo_nas_pastas(arquivo)
            if not arquivo:
                return {}
        else:
            # usa o arquivo enviado
            if not os.path.isfile(arquivo):
                return {}
        _id_arquivo = os.path.splitext( os.path.split(arquivo)[1] )[0]
        arquivo_status = os.path.splitext(arquivo)[0] + '.json'
        status = Util.ler_json(arquivo_status)
        status['status'] = self.status_arquivo_pela_pasta(arquivo, fixo = True)
        if not 'nome_real' in status:
            status['nome_real'] = f'{_id_arquivo}.pdf'
        if not 'arquivo_pdf' in status:
            status['arquivo_pdf'] = f'{_id_arquivo}.pdf'
        if not 'arquivo_json' in status:
            status['arquivo_json'] = f'{_id_arquivo}.json'
        status['pasta'] = os.path.split(arquivo)[0]
        status['download'] = False
        status['tamanho_final'] = 0
        if arquivo.find(self.saida)>=0:
           status['download'] = True
           status['tamanho_final'] = round(os.path.getsize(arquivo)/1024,2)
        if (not 'fim' in status) and status['download'] :
           status['fim'] = Util.data_arquivo_str(arquivo)
        status['id'] = _id_arquivo
        return status

    def status_arquivo_pela_pasta(self, arquivo, fixo = False):
        if fixo:
           # retorna o status da pasta informada
           if not os.path.isfile(arquivo):
              return ''
           if arquivo.find(self.entrada)>=0:
              return 'Aguardando processamento'
           if arquivo.find(self.processando)>=0:
              return 'Em processamento'
           if arquivo.find(self.saida)>=0:
              return 'Processamento concluído'
           if arquivo.find(self.erro)>=0:
              return 'Erro no processamento'
           return ''
        # busca o arquivo nas pastas
        _arquivo = os.path.split(arquivo)[1]
        if os.path.isfile(os.path.join(self.entrada, _arquivo)):
            return 'Aguardando processamento'
        if os.path.isfile(os.path.join(self.processando, _arquivo)):
            return 'Em processamento'
        if os.path.isfile(os.path.join(self.saida, _arquivo)):
            return 'Processamento concluído'
        if os.path.isfile(os.path.join(self.erro, _arquivo)):
            return 'Erro no processamento'
        return ''

    def parar(self):
        self.__processar_continuamente__ = False

    def processar_continuamente(self):
        global TEMPO_LOCK
        pastas_parada = [self.entrada, self.saida, self.entrada, './']
        arquivos_processando = Util.listar_arquivos(self.processando, 'pdf')
        # ao reiniciar o processamento, move os arquivos que podem ter tido o processamento interrompido
        # para a pasta de entrada para serem processados novamente
        if any(arquivos_processando):
            print(f'Movendo {len(arquivos_processando)} arquivo(s) em processamento para a pasta de entrada ...')
            for a in arquivos_processando:
                try:
                    self.mover_com_controles(a,self.entrada)
                except:
                    print(f'ERRO: não foi possível mover {a} para novo processamento')
        # inicia a avaliação da pasta de entrada
        fila_cheia_timer = 1
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
            arquivos = Util.listar_arquivos(self.entrada, 'pdf')
            arquivos_saida = len(Util.listar_arquivos(self.saida, 'pdf'))
            arquivos_erro = len(Util.listar_arquivos(self.erro, 'pdf'))
            arquivos_processando = len(Util.listar_arquivos(self.processando, 'pdf'))
            qtd_pasta = len(arquivos)
            for a in arquivos:
                # se a fila já está cheia, aguarda para pegar mais da pasta
                if self.fila.tasks_entrada() > self.fila.n_workers * 1.5:
                    str_now = datetime.now().strftime("%H:%M:%S")
                    print(f'Fila de processamento cheia ({self.fila.n_workers} workers): {self.fila.tasks_entrada()} tarefas - {str_now}\n >> Entrada: {qtd_pasta} - Processando: {arquivos_processando} - Saída: {arquivos_saida} - Erros: {arquivos_erro}')
                    time.sleep(fila_cheia_timer) 
                    if fila_cheia_timer < TEMPO_LOCK:
                       fila_cheia_timer += 2
                    break
                # arquivo incompleto - tamanho zero
                if os.path.getsize(a) == 0:
                    continue
                qtd_pasta -= 1
                fila_cheia_timer = 1
                _entrada = a
                _processando = os.path.join(self.processando, os.path.split(a)[1] )
                _controle = f'{a}.lc'
                lock_controle = FileLock(_controle, TEMPO_LOCK)
                with lock_controle:
                    if os.path.isfile(_entrada):
                       print(f'Processando entrada: {_entrada}') 
                       if os.path.isfile(_processando):
                          try:
                             self.mover_com_controles(_processando, None)
                          except Exception as er:
                             print(f'ERRO: não foi possível remover {_processando} para novo processamento >> ERRO: {er}')
                             continue   
                       try: 
                          self.mover_com_controles(_entrada, self.processando)
                       except Exception as er:
                           print(f'ERRO: não foi possível mover {_entrada} para novo processamento >> ERRO: {er}')
                           continue   
                       self.fila(processar_arquivo, (_processando, self.saida, self.erro))
            # remove arquivos de controle com mais de 1 minuto para nova análise do lock
            Util.limpar_controles(self.entrada, minutos=TEMPO_LOCK+10)
            time.sleep(0.5)

    @classmethod
    def mover_com_controles(cls, arquivo, destino):
        origem, nm_arquivo = os.path.split(arquivo)
        tipos = ['.pdf','.json','.txt']
        nm_arquivo = os.path.splitext(nm_arquivo)[0]
        arquivos = [f'{nm_arquivo}{tipo}' for tipo in tipos]
        for arq in arquivos:
            mover_de = os.path.join(origem, arq)
            mover_para = os.path.join(destino, arq) if destino else None
            if os.path.isfile(mover_de):
                if mover_para:
                    shutil.move(mover_de, mover_para)
                else:
                    os.remove(mover_de)


##################################################################
# processamento de um arquivo dentro de cada worker
def processar_arquivo(arquivos):
    entrada, pasta_saida, pasta_erro= arquivos
    nm_entrada = os.path.split(entrada)[1]
    saida = os.path.join(pasta_saida, nm_entrada)
    erro = os.path.join(pasta_erro, nm_entrada)
    saida_ngs = os.path.splitext(entrada)[0] + '_ngs_.pdf'
    saida_erro_txt = os.path.splitext(erro)[0] + '.txt'
    try:
        print(f'>>> PROCESSANDO ARQUIVO: {entrada} <<<')
        ocr_pdf(arquivo_entrada=entrada, arquivo_saida=saida_ngs)    
        print(f'>>> ARQUIVO PROCESSADO: {entrada} --> {saida} <<<')
    except Exception as e:
        # move o arquivo para a pasta de erro
        print(f'>>> ERRO DE PROCESSAMENTO: {entrada} --> {erro} <<<')
        ProcessarOcr.mover_com_controles(entrada, pasta_erro)
        try:
            with open(saida_erro_txt, 'w') as fe:
                    fe.write(f'ERRO: {e}')
        except Exception as ee:
            print(f'ERRO processar_arquivo: não foi possível criar o arquivo com o a mensagem de erro de processamento {ee}, erro de processamento: {e}')
    try:
        compress_pdf(saida_ngs, saida)
        print(f'>>> ARQUIVO COMPRIMIDO: {entrada} --> {saida} <<<')
        os.remove(saida_ngs)
    except Exception as e:
        print('ERRO processar_arquivo: não foi possível usar o ghostscript para compactar o arquivo de saída')
        # o arquivo de saída fica sem compressão
        shutil.move(saida_ngs, saida)
    os.remove(entrada)
    ProcessarOcr.mover_com_controles(entrada, pasta_saida)


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
            print('Pastas do serviço: ', cls.SERVICO.pastas())
        return cls.SERVICO

if __name__ == '__main__':
    processar_ocr = ProcessarOcr()
    
