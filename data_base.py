import zipfile
import pandas as pd
from sqlalchemy import create_engine
import time
import os

# Caminho para a pasta Downloads
caminho_downloads = r"C:\Users\FABIA\Downloads"

# Caminho completo do arquivo zip
caminho_zip = os.path.join(caminho_downloads, "202403_NovoBolsaFamilia.zip")

# Etapa 1: Extrair o arquivo CSV de dentro do arquivo .zip
with zipfile.ZipFile(caminho_zip, 'r') as zip_ref:
    start_time = time.time()
    # Listando o primeiro arquivo que está no zip
    arq_csv = zip_ref.namelist()[0]
    print(f"Listando o arquivo.csv: {arq_csv}")    
    
    # Extraindo o arquivo para a pasta Downloads
    zip_ref.extract(arq_csv, caminho_downloads)
    print(f"Arquivo extraído para o caminho: {os.path.join(caminho_downloads, arq_csv)}")
    time_end = time.time()
    real_time = time_end - start_time
    print(f'Tempo de extração: {real_time:.2f} segundos')

# Caminho completo do CSV extraído
caminho_csv_extraido = os.path.join(caminho_downloads, arq_csv)

# Etapa 2: Carregar o arquivo CSV usando o Pandas com delimitador correto

# Carregar somente o cabeçalho para definir o DataFrame corretamente
df = pd.read_csv(caminho_csv_extraido, delimiter=';', encoding='latin1', nrows=0)

# Limpar os nomes das colunas (remover aspas e espaços extras)
df.columns = df.columns.str.replace('"', '', regex=True).str.strip().str.replace(';', '', regex=True)

# Renomear as colunas conforme necessário
df.rename(columns={
    'MÊS REFERÊNCIA': 'data_referencia',
    'MÊS COMPETÊNCIA': 'data_competencia',
    'UF': 'uf',
    'CÓDIGO MUNICÍPIO SIAFI': 'codigo_municipio',
    'NOME MUNICÍPIO': 'nome_municipio',
    'CPF FAVORECIDO': 'cpf_beneficiario',
    'NIS FAVORECIDO': 'nis_beneficiario',
    'NOME FAVORECIDO': 'nome_beneficiario',
    'VALOR PARCELA': 'valor_parcela'
}, inplace=True)

# Conectar ao banco de dados PostgreSQL
user = 'postgres'
password = '32481024'
host = 'localhost'
database = 'atividade_bolsa'
engine = create_engine(f'postgresql+psycopg2://{user}:{password}@{host}/{database}')

# Variável para contar o total de linhas importadas
total_linhas_importadas = 0

# Etapa 3: Inserir os dados no banco de dados em lotes com pausa, ignorando o cabeçalho após o primeiro lote
try:
    print("Conexão realizada!\n")
    print("Início da importação dos dados...")

    # Iterar sobre o arquivo em chunks
    start_time = time.time()
    for i, chunk in enumerate(pd.read_csv(caminho_csv_extraido, delimiter=';', encoding='latin1', header = None, chunksize=1000000)):
        # Atribuir os nomes das colunas do df principal a cada chunk
        chunk.columns = df.columns

        # Verificar as colunas do chunk antes de manipular 'valor_parcela'
        print(f"Colunas no chunk {i+1}: {chunk.columns}")
        
        # Verifique a existência da coluna 'valor_parcela' e aplique a conversão
        if 'valor_parcela' in chunk.columns:
            # Corrigir vírgulas e converter para float usando pd.to_numeric com erro 'coerce'
            chunk['valor_parcela'] = pd.to_numeric(chunk['valor_parcela'].str.replace(',', '.', regex=False), errors='coerce')
        else:
            print(f"Coluna 'valor_parcela' não encontrada no chunk {i+1}. Pulando para o próximo chunk.")
            continue  # Pula para o próximo chunk

        # Inserir no banco
        chunk.to_sql('pagamentos', engine, if_exists='append', index=False)
        
        # Incrementar o total de linhas importadas
        total_linhas_importadas += len(chunk)
        
        print(f"Lote {i + 1} inserido com sucesso. Total de linhas importadas até agora: {total_linhas_importadas}")
        
        # Pausa de 3 segundos entre os lotes
        time.sleep(3)
except Exception as e:
    print(f"Ocorreu um erro ao inserir os dados: {e}")

# Medir o tempo total de importação
time_end = time.time() 
real_time = time_end - start_time
print(f'Tempo de importação: {real_time:.2f} segundos')

# Exibir o total de linhas importadas ao final do processo
print(f"Total de linhas importadas: {total_linhas_importadas}")

# Remover o arquivo CSV extraído após a operação
os.remove(caminho_csv_extraido)
print("Arquivo CSV removido com sucesso.")