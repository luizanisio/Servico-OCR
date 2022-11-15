import os, time
import hashlib

HASH_BUF_SIZE = 65536  # lets read stuff in 64kb chunks!
def hash_file(arquivo):
    # BUF_SIZE is totally arbitrary, change for your app!
    # https://stackoverflow.com/questions/22058048/hashing-a-file-in-python

    md5 = hashlib.md5()
    with open(arquivo, 'rb') as f:
        while True:
            data = f.read(HASH_BUF_SIZE)
            if not data:
                break
            md5.update(data)

    return md5.hexdigest()

def listar_arquivos(pasta, extensao='txt', inicio=''):
    if not os.path.isdir(pasta):
        msg = f'Não foi encontrada a pasta "{pasta}" para listar os arquivos "{extensao}"'
        raise Exception(msg)
    res = []
    _inicio = str(inicio).lower()
    _extensao = f".{extensao}".lower() if extensao else ''
    for path, dir_list, file_list in os.walk(pasta):
        for file_name in file_list:
            if (not inicio) and file_name.lower().endswith(f"{_extensao}"):
                res.append(os.path.join(path,file_name))
            elif file_name.lower().endswith(f"{_extensao}") and file_name.lower().startswith(f"{_inicio}"):
                res.append(os.path.join(path,file_name))
    return res

def limpar_temporarios(dias = 1):
    dias = 0.5 if dias < 0.5 else dias
    path = "./temp/"
    tempo = 60*60*24 * dias
    now = time.time()
    print('Analisando temporários ... ')
    for filename in os.listdir(path):
        filestamp = os.stat(os.path.join(path, filename)).st_mtime
        filecompare = now - tempo
        if  filestamp < filecompare:
            try:
                os.path.remove(filename)
                print(f'Temporário removido "{filename}" _o/')
            except Exception as e:
                print(f'Temporário NÃO removido "{filename}" :( - ERRO: {e}')
