# -*- coding: utf-8 -*-

'''
 Autor Luiz Anísio 19/11/2022
 - atualizado 19/02/2023 - max_workers
 Abre n workers para processas os callables em processos independentes
 No map_threads e no map_processos substitui o valor de entrada pelo de saída

 Map com threads:
      WorkerQueue.map_threads(funcao = xxxx, lista = valores)

 Map com processos:
      WorkerQueue.processos(funcao = xxxx, lista = valores)

 Fila com processamento contínuo e/ou funções variáveis
 Os valores precisam ser serializáveis, não é possível utilizar lambda diretamente
      wq = WorkerQueue()
      wq(funcao1 = xxxx, valor = valor1)
      wq(funcao2 = xxxx, valor = valor2)
      ....
      wq.finalizar()
      resultado = wq.resultados()

Outros exemplos em: 
    if __name__ == '__main__': ....
 '''

import time
from typing import Any, Callable
from multiprocessing import Process, cpu_count, Queue
from multiprocessing.dummy import Pool as ThreadPool
import random
from threading import Thread

class WorkerQueue:
    '''
       result_queue = True, cada Callable chamado retona um valor que é armazenado na fila de saída (posição na fila, resultado )
       n_workers = número de workers trabalhando
       _counter = contador da fila
    '''
    # ------ INI --------                    
    def __init__(self, n_workers: int = 10, retorno = True, iniciar_workers = True, max_workers = 0) -> None:
        self.__thread_saida__ = None
        self.n_workers = self.__validar_workers__(n_workers)
        if self.n_workers > max_workers and max_workers > 0:
           self.n_workers = max_workers 
           print(f'Máximo de workers atingido (max={max_workers}) - usando {self.n_workers}')
        self._queue = Queue()
        self._result_queue = Queue() if retorno else None
        # prepara os workers
        self.__workers = {}
        if iniciar_workers:
            self.iniciar()
        self._counter = 0
        self._results = []
        self._erros = []
        #print(f'Iniciando com {self.n_workers} processos - pedidos: {n_workers}')
        #exit()

    # ------- PROCESSAMENTO DA FILA DE ENTRADA
    def worker_queue(self, wid, in_queue: Queue, result_queue: Queue):
        ''' fica em looping infinito até receber uma tarefa None
            caso tenha uma fila de retornos, adiciona o retorno à fila '''
        while True:
            k, tarefa, valor = in_queue.get()
            if tarefa is None:  
                #print(f'Parando fila... {queue.qsize()} itens na fila')
                if result_queue:
                   result_queue.put((None, None)) # sinal para finalizar a fila de saída
                break
            try:
                res = tarefa(valor) 
            except Exception as e:
                print(f'WorkerQueue: ERRO processando a fila de entrada na posição {k} valor enviado {valor} ')
                if result_queue:
                   result_queue.put(e)
                raise e
            if result_queue:
                result_queue.put((k, res)) # coloca o retorno na fila de retorno

    # ------- PROCESSAMENTO DA FILA DE SAÍDA
    def __processar_fila_saida__(self):
        ''' deve ser rodado em uma thread para 
            receber os itens da fila de saída e colocar no result do objeto instanciado
            para ao receber o item None da fila
            '''
        if not self._result_queue:
            return 
        while True:
            k_v = self._result_queue.get()
            # verifica se foi colocado um erro na fila
            if type(k_v) is Exception:
               msg = f'WorkerQueue(ERRO): {k_v}'
               raise Exception(msg) 
            k, valor = k_v
            if (valor is None):
                # vai receber um None para cada processo em execução
                # aguarda as filas zerarem para finalizar
                if self._result_queue.qsize() == 0 and self._queue.qsize() == 0:
                    print(f'Parando fila de saída ... {self._result_queue.qsize()} itens na fila')
                    break
                continue
            # insere no result a posição do item e o valor da tarefa
            self._results.append((k, valor))

    def __iniciar_thread_saida(self):
        # não está controlando a saída
        if not self._result_queue:
           return 
        # já tem uma thread de saída
        if self.__thread_saida__:
           return 
        self.__thread_saida__ = SafeThread(target = self.__processar_fila_saida__)
        self.__thread_saida__.start()

    def __finalizar_thread_saida(self):
        if not self._result_queue:
           return
        print(f'WorkerQueue: Finalizando thread de saída, aguardando {self.tasks_saida()} resultados em processamento')
        self.__thread_saida__.join()
        self.__thread_saida__ = None

    # ------ CALL DA TAREFA --------                    
    def __call__(self, tarefa: Callable, valor = None) -> Any:
        self._queue.put((self._counter, tarefa, valor))
        self._counter+=1

    # --- CONSULTAS -----
    def tasks_entrada(self):
        return self._queue.qsize()
    def tasks_saida(self):
        if not self._result_queue:
           raise Exception('WorkerQueue: fila de saída desativada')
        return self._result_queue.qsize()
    def tasks_finalizadas(self):
        if not self._result_queue:
           raise Exception('WorkerQueue: fila de saída desativada')
        return len(self._results)

    # --- FINALIZAÇÃO -----
    def finalizar(self):
        if any(self.__workers):
            [self._queue.put((None, None, None)) for _ in range(self.n_workers)]
            print(f'WorkerQueue: finalizar(): Queue com {self._queue.qsize()} tarefas na fila')
            for w in self.__workers.values():
                w['process'].join()
                print(f'\tProcesso {w["wid"]} finalizado')
        self.__finalizar_thread_saida()
        #print('Fila de saída capturada')        
        if not self._queue.empty():
           msg = f'WorkerQueue: finalizar() não conseguiu processar toda a fila de tarefas - restando {self._queue.qsize()}'
           if not any(self.__workers.keys()):
              msg += ', verifique se foi executado o método iniciar()'
           raise Exception(msg)
        self.__workers = {}
        print(f'WorkerQueue: {self.n_workers} processos finalizados')

    # --- INICIALIZAÇÃO -----
    def iniciar(self, n_workers: int = None):
        # inicia a thread de saída se não foi iniciada ainda ou se foi finalizada
        self.__iniciar_thread_saida()
        # inicia ou reinicia os workers
        if any(self.__workers.keys()):
           self.finalizar()
        if n_workers is not None:
           self.n_workers = self.__validar_workers__(n_workers)
        self.__workers = {}
        for wid in range(self.n_workers):
            p = Process(target=self.worker_queue, args=(wid, self._queue, self._result_queue), daemon = True)
            self.__workers[wid] = {'wid': wid, 'process' : p}
            p.start()
        print(f'WorkerQueue: {self.n_workers} processos iniciados')

    # --- RESULTADO DO PROCESSO -----        
    def resultados(self, stop = False):
        if not self._result_queue:
           raise Exception('WorkerQueue: fila de saída desativada')
        if stop:
           self.finalizar() 
        self._results.sort(key=lambda x: x[0])
        res = [e for _, e in self._results]
        return res

    # --- NÚMERO DE CPUS -----
    @staticmethod
    def cpus(uma_livre=True):
        num_livres = 1 if uma_livre else 0
        return cpu_count() if cpu_count() < 3 else cpu_count() - num_livres

    # ----------- STATUS DO PROCESSAMENTO
    def status(self):
        return {'processos' : len(self.__workers), 
               'tarefas_entrada' : self.tasks_entrada(),
               'tarefas_saida' : self.tasks_saida(),
               'tarefas_finalizadas' : self.tasks_finalizadas() if self._result_queue else -1
               }

    # aplica a função nos itens da lista substituindo o valor de entrada pelo resultado
    # n_workers: número de threads ou processos >> 0 = número de CPUs // -1 = CPUs -1
    # usa threads - mais leve com baixo custo computacional, pode não aproveitar todas as CPUS 
    @classmethod
    def map_threads(cls, funcao, lista, n_workers = None):
        n_workers = cls.__validar_workers__(n_workers)
        def _transforma(i):
            lista[i] = funcao(lista[i])
        #print(f'Iniciando {n_workers} threads')
        pool = ThreadPool(n_workers)
        pool.map(_transforma, list(range(len(lista))))
        pool.close()
        pool.join()

    # Aplica a função nos itens da lista substituindo o valor de entrada pelo resultado
    # pode receber uma função ou um callable 
    # n_workers: número de threads ou processos >> 0 = número de CPUs // -1 = CPUs -1
    # usa processos e fila para serializar os objetos entre os processos - aproveita as CPUs, 
    # mas tem um custo computacional maior - é bom para processos pesados
    @classmethod
    def map_process(cls, funcao, lista, n_workers = None, retorno = True):
        n_workers = cls.__validar_workers__(n_workers)
        # resolve usando workers para processamentos mais pesados 
        #print(f'Iniciando {n_workers} workers')
        wq = WorkerQueue(n_workers=n_workers, retorno=retorno)
        [wq(funcao, item) for item in lista]
        #print(f'Aguardando finalização da fila com {wq.pending_task_size()} - saída com {wq.finished_task_size()}')
        wq.finalizar()
        if retorno:
           for i, r in enumerate(wq.resultados()):
               lista[i] = r

    @classmethod
    def __validar_workers__(cls, n_workers):
        if (n_workers == None) or type(n_workers) is not int:
           return cls.cpus(False)
        elif n_workers < 1:
           return cls.cpus(True)    
        return n_workers
        
### thread com controle de erro no join
### para uso na thread da fila de saída
# https://stackoverflow.com/a/68405992/10322624
class SafeThread(Thread):
    def __init__(self, *args, **kwargs):
        super(SafeThread, self).__init__(*args, **kwargs)
        self.exception = None

    def run(self) -> None:
        try:
            super(SafeThread, self).run()
        except Exception as ex:
            self.exception = ex

    def join(self, *args, **kwargs) -> None:
        super(SafeThread, self).join(*args, **kwargs)
        if self.exception:
            raise self.exception

#########################################################
##########  TESTES - imports internos para não carregar
##########           quando não for teste
#########################################################        
class MeuCallable:
    def __init__(self, soma, tempo_espera = 2) -> None:
        self.__soma = soma
        self.__tempo_espera = tempo_espera
    def __call__(self, valor) -> Any:
        if self.__tempo_espera > 0:
           time.sleep(random.random() * self.__tempo_espera)
        # teste de erro
        if valor == -1:
            raise Exception('MeuCallable: erro com valor = -1')
        return valor + self.__soma

def processo_pesado(tempo):
    import math
    from datetime import datetime
    import os
    startTime = datetime.now()
    print(f' - Processo pesado iniciado #{os.getpid()}: {startTime}')
    while (datetime.now() - startTime).total_seconds() < tempo:
        r = math.sqrt(math.log(math.factorial(200)) * math.log(math.factorial(200)))
    WorkerQueue.map_threads(funcao = lambda x:math.factorial(x), lista=[100]*100, n_workers = 100)
    print(f' - Processo pesado finalizado #{os.getpid()}: {(datetime.now() - startTime).total_seconds()}s')
    return r

def teste_erro_map(processo = True):
    lista1 = list(range(1000))
    lista1 = lista1 + [-1] + lista1
    clb = MeuCallable(soma=0,tempo_espera=0)
    if processo:
        WorkerQueue.map_process(funcao = clb, lista=lista1)
    else:
        WorkerQueue.map_threads(funcao = clb, lista=lista1)
    print('Finalizado - essa mensagem não deveria aparecer')

def teste_erro_fila(retorno):
    lista1 = list(range(1000))
    lista1 = lista1 + [-1] + lista1
    clb = MeuCallable(soma=0,tempo_espera=0)
    wq = WorkerQueue( retorno= False)
    for i in lista1:
        wq(clb, valor=i)
    wq.finalizar()
    print('Finalizado - essa mensagem não deveria aparecer')

def teste_tempos():
    # teste com Map
    from datetime import datetime

    lista1 = list(range(50000))
    lista2 = list(range(50000))
    lista3 = list(range(50000))
    teste = [_ + 1000 for _ in range(50000)]
    func = lambda x: x+1000
    clb = MeuCallable(soma=1000,tempo_espera=0)

    print('----- Threads com retorno')
    t = datetime.now()
    WorkerQueue.map_threads(funcao = func, lista=lista1)
    dt = (datetime.now() - t).total_seconds()
    print(f'Tempo: {dt}s:', lista1[:10],'..', lista1[-5:])

    print('\n----- Processos com retorno')
    t = datetime.now()
    WorkerQueue.map_process(funcao = clb, lista=lista2)
    dt = (datetime.now() - t).total_seconds()
    print(f'Tempo: {dt}s:', lista2[:10],'..', lista2[-5:])

    print('Testando valores de processos e threads: ', end='')
    for n1, n2, t in zip(lista1,lista2, teste):
        assert n1 == t, f'{n1} diferente de {t}'
        assert n2 == t, f'{n2} diferente de {t}'
    print('OK  _o/')        

    print('\n----- Processos sem retorno')
    t = datetime.now()
    WorkerQueue.map_process(funcao = clb, lista=lista3, retorno = False)
    dt = (datetime.now() - t).total_seconds()
    print(f'Tempo: {dt}s:', lista3[:10],'..', lista1[-5:])


def teste_chamadas_independentes():
    # Instancia o Worker
    wq = WorkerQueue()
    # envia os Callables
    def fabricar_tarefas(n=20, soma=0, tempo_espera = 2):
        c = MeuCallable(soma, tempo_espera)
        for i in range(n):
            wq(c, i)

    fabricar_tarefas(n=20, tempo_espera = 2)
    # Retorna os resultados parciais
    time.sleep(2)
    print('Status parcial:', wq.status())
    
    # aguarda finalizar tudo
    wq.finalizar()
    assert len(wq.resultados()) == 20, 'Não foram retornadas as 20 tarefas enviadas'
    print('-----------------------------------')
    print('Status adicionados novos:', wq.status())
    # inclui mais tarefas sem iniciar
    fabricar_tarefas(n = 20, soma = 20, tempo_espera = 1)
    # inicia o processamento de 20 tarefas
    wq.iniciar()
    # inclui mais 10 tarefas no meio do processamento
    fabricar_tarefas(n = 10, soma = 40, tempo_espera = 1)
    wq.finalizar()    
    # retorna os resultados finais depois de duas chamadas
    print('-----------------------------------')
    print('Status finalizar():', wq.status())
    assert len(wq.resultados()) == 50, 'Não foram retornadas as 50 tarefas enviadas'

def teste_pesado():
    from datetime import datetime
    # tarefas de 5s de cálculos - todas iguais
    def fabricar_tarefas():
        return [30 for _ in range(WorkerQueue.cpus()*2)]
    lista = fabricar_tarefas()
    startTime = datetime.now()
    print('---------------------------------------------')
    print(f'THREADS TESTE PESADO INICIADO: {startTime}')
    WorkerQueue.map_threads(funcao = processo_pesado, lista=lista)
    tempo_threads = (datetime.now() - startTime).total_seconds()
    print(f'THREADS TESTE PESADO FINALIZADO: {tempo_threads}s')

    lista = fabricar_tarefas()
    print('---------------------------------------------')
    startTime = datetime.now()
    print(f'PROCESSOS TESTE PESADO INICIADO: {startTime}')
    WorkerQueue.map_process(funcao = processo_pesado, lista=lista)
    tempo_processos = (datetime.now() - startTime).total_seconds()
    print(f'PROCESSOS TESTE PESADO FINALIZADO: {tempo_processos}s')

    print('---------------------------------------------')
    print(f'Tempo por threads: {tempo_threads}')
    print(f'Tempo por processos: {tempo_processos}')

if __name__ == '__main__':

    #print("########## CHAMADA DANDO ERRO COM MAP PROCESSO")
    #teste_erro_map(True)
    #print("########## CHAMADA DANDO ERRO COM MAP THREADS")
    #teste_erro_map(False)
    #print("########## CHAMADA DANDO ERRO COM FILA DE SAÍDA")
    #teste_erro_fila(True)
    #print("########## CHAMADA DANDO ERRO SEM FILA DE SAÍDA")
    #teste_erro_fila(False)
    print("########## CHAMADAS INDEPENDENTES")
    teste_chamadas_independentes()
    print("\n########## MAP PROCESSOS e THREADS")
    teste_tempos()
    #print("\n########## TESTE PESADO")
    #teste_pesado()