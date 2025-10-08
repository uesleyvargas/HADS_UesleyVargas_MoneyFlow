"""
Módulo responsável pela configuração e gerenciamento do banco de dados SQLite
para o aplicativo MyFinance.
"""

import sqlite3
import pandas as pd
import hashlib
import secrets
from datetime import datetime

# --- Configuração do Banco de Dados ---
DB_FILE = "financas.db"

def conectar_bd():
    """Cria uma conexão com o banco de dados SQLite."""
    return sqlite3.connect(DB_FILE)

def verificar_e_atualizar_esquema():
    """Verifica e atualiza o esquema do banco de dados se necessário."""
    conn = conectar_bd()
    cursor = conn.cursor()
    
    # Verifica se a coluna 'usuario_id' existe na tabela transacoes
    try:
        cursor.execute("SELECT usuario_id FROM transacoes LIMIT 1")
    except sqlite3.OperationalError:
        # Se a coluna não existe, adiciona
        print("Adicionando coluna usuario_id à tabela transacoes...")
        cursor.execute("ALTER TABLE transacoes ADD COLUMN usuario_id INTEGER")
        conn.commit()
        print("Coluna usuario_id adicionada com sucesso!")
    
    # Verifica se a coluna 'salt' existe na tabela usuarios
    try:
        cursor.execute("SELECT salt FROM usuarios LIMIT 1")
    except sqlite3.OperationalError:
        # Se a coluna não existe, adiciona
        print("Adicionando coluna salt à tabela usuarios...")
        cursor.execute("ALTER TABLE usuarios ADD COLUMN salt TEXT NOT NULL DEFAULT ''")
        conn.commit()
        print("Coluna salt adicionada com sucesso!")
    
    conn.close()

def inicializar_bd():
    """Cria as tabelas do banco de dados e insere dados iniciais."""
    conn = conectar_bd()
    cursor = conn.cursor()

    # Tabela unificada para transações financeiras (COM usuario_id)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT NOT NULL,
        descricao TEXT,
        valor REAL NOT NULL,
        data DATE NOT NULL,
        categoria TEXT NOT NULL,
        efetuado INTEGER,
        fixo INTEGER,
        usuario_id INTEGER,
        FOREIGN KEY (usuario_id) REFERENCES usuarios (id)
    )
    """)

    # Tabela para categorias
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        tipo TEXT NOT NULL
    )
    """)
    
    # Tabela para usuários (COM A COLUNA SALT)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL DEFAULT '',
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        ativo INTEGER DEFAULT 1
    )
    """)
    
    # Adicionar categorias iniciais apenas uma vez
    cursor.execute("SELECT COUNT(*) FROM categorias")
    if cursor.fetchone()[0] == 0:
        categorias_iniciais = [
            ('Salário', 'receita'), ('Investimentos', 'receita'), ('Comissão', 'receita'),
            ('Alimentação', 'despesa'), ('Aluguel', 'despesa'), ('Gasolina', 'despesa'),
            ('Saúde', 'despesa'), ('Lazer', 'despesa')
        ]
        cursor.executemany("INSERT INTO categorias (nome, tipo) VALUES (?, ?)", categorias_iniciais)

    conn.commit()
    conn.close()
    
    # Verifica e atualiza o esquema se necessário
    verificar_e_atualizar_esquema()

# --- Funções de Hash ---

def hash_password(password):
    """Gera um hash seguro para a senha usando hashlib."""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return password_hash, salt

def verificar_password(password, stored_hash, salt):
    """Verifica se a senha corresponde ao hash armazenado."""
    test_hash = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return test_hash == stored_hash

# --- Funções de Transações ---

def ler_transacoes(usuario_id=None):
    """Lê transações do banco de dados filtrando por usuário."""
    conn = conectar_bd()
    
    # Query base para transações - AGORA FILTRA APENAS POR USUÁRIO ESPECÍFICO
    if usuario_id:
        query_receitas = """
        SELECT valor as Valor, efetuado as Efetuado, fixo as Fixo, 
               data as Data, categoria as Categoria, descricao as Descrição 
        FROM transacoes 
        WHERE tipo='receita' AND usuario_id = ?
        """
        query_despesas = """
        SELECT valor as Valor, efetuado as Efetuado, fixo as Fixo, 
               data as Data, categoria as Categoria, descricao as Descrição 
        FROM transacoes 
        WHERE tipo='despesa' AND usuario_id = ?
        """
        
        df_receitas = pd.read_sql_query(query_receitas, conn, params=(usuario_id,))
        df_despesas = pd.read_sql_query(query_despesas, conn, params=(usuario_id,))
    else:
        # Se não tem usuario_id, retorna DataFrame vazio para novo usuário
        df_receitas = pd.DataFrame(columns=['Valor', 'Efetuado', 'Fixo', 'Data', 'Categoria', 'Descrição'])
        df_despesas = pd.DataFrame(columns=['Valor', 'Efetuado', 'Fixo', 'Data', 'Categoria', 'Descrição'])
    
    conn.close()
    return df_receitas, df_despesas

def ler_categorias():
    """Lê categorias do banco de dados (são globais, não por usuário)."""
    conn = conectar_bd()
    df_cat = pd.read_sql_query("SELECT nome, tipo FROM categorias", conn)
    conn.close()
    
    cat_receita = df_cat[df_cat['tipo'] == 'receita']['nome'].tolist()
    cat_despesa = df_cat[df_cat['tipo'] == 'despesa']['nome'].tolist()
    return cat_receita, cat_despesa

def salvar_transacao(tipo, descricao, valor, data, categoria, efetuado, fixo, usuario_id=None):
    """Salva uma transação no banco de dados."""
    if usuario_id is None:
        raise ValueError("usuário_id é obrigatório para salvar transações")
    
    conn = conectar_bd()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transacoes (tipo, descricao, valor, data, categoria, efetuado, fixo, usuario_id) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (tipo, descricao, valor, data, categoria, efetuado, fixo, usuario_id))
    conn.commit()
    conn.close()

# --- Funções de Autenticação ---

def criar_usuario(username, email, password):
    """Cria um novo usuário."""
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        
        # Verifica se usuário ou email já existem
        cursor.execute("SELECT id FROM usuarios WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            conn.close()
            return False, "Usuário ou email já existem"
        
        # Cria hash e salt da senha
        password_hash, salt = hash_password(password)
        
        # Insere o novo usuário
        cursor.execute("""
            INSERT INTO usuarios (username, email, password_hash, salt) 
            VALUES (?, ?, ?, ?)
        """, (username, email, password_hash, salt))
        
        # Obtém o ID do novo usuário
        user_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return True, f"Usuário criado com sucesso. ID: {user_id}"
        
    except sqlite3.Error as e:
        return False, f"Erro de banco de dados: {str(e)}"
    except Exception as e:
        return False, f"Erro ao criar usuário: {str(e)}"

def autenticar_usuario(username_or_email, password):
    """Autentica um usuário."""
    try:
        conn = conectar_bd()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, username, email, password_hash, salt, ativo 
            FROM usuarios 
            WHERE (username = ? OR email = ?) AND ativo = 1
        """, (username_or_email, username_or_email))
        
        usuario = cursor.fetchone()
        conn.close()
        
        if usuario and verificar_password(password, usuario[3], usuario[4]):
            return {
                'id': usuario[0],
                'username': usuario[1],
                'email': usuario[2],
                'ativo': usuario[5]
            }
        
        return None
        
    except Exception as e:
        print(f"Erro na autenticação: {e}")
        return None

def buscar_usuario_por_id(usuario_id):
    """Busca usuário por ID."""
    conn = conectar_bd()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, username, email, ativo FROM usuarios WHERE id = ? AND ativo = 1", (usuario_id,))
    
    usuario = cursor.fetchone()
    conn.close()
    
    if usuario:
        return {
            'id': usuario[0],
            'username': usuario[1],
            'email': usuario[2],
            'ativo': usuario[3]
        }
    
    return None

# --- Variáveis globais ---
cat_receita = []
cat_despesa = []

def inicializar_app():
    """Inicializa o aplicativo carregando dados iniciais."""
    global cat_receita, cat_despesa
    inicializar_bd()
    cat_receita, cat_despesa = ler_categorias()
    print("Aplicativo inicializado com sucesso!")

# Inicializa ao importar o módulo
inicializar_app()