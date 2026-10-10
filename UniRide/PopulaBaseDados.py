#!/usr/bin/env python
"""
Popula o banco de dados do UniRide (db.sqlite3) com dados de teste.

Os dados reproduzem o que aparece nas telas do protótipo (pasta html/):
Bernardo, Ana, Lucas, Mariana, João e Sofia, com trajetos saindo de
Botafogo, Flamengo e Humaitá, e mais alguns alunos para a busca de
caronas ter resultados.

Como usar (no mesmo diretório do arquivo db.sqlite3 e do manage.py):

    python manage.py migrate
    python PopulaBaseDados.py

ATENÇÃO: o script APAGA todos os registros das tabelas do UniRide
(Aluno, Veiculo, Trajeto, Solicitacao e Avaliacao) e os usuários de teste
listados abaixo antes de inserir os dados de novo. Pode rodar quantas vezes
quiser. O superusuário criado com `createsuperuser` NÃO é apagado.

Todos os usuários de teste entram com o e-mail como nome de usuário e a
senha definida em SENHA_PADRAO (por exemplo: bernardo@puc-rio.br / uniride123).
"""
import base64
import hashlib
import secrets
import sqlite3
import string
from typing import Dict, List, Tuple

# --- Configurações ---
DB_DESTINO = 'db.sqlite3'
SENHA_PADRAO = 'uniride123'

# Mesmo número de iterações que o Django usa por padrão para guardar senhas.
# Se a versão do Django for outra, o login continua funcionando
# (o Django apenas atualiza o formato da senha no primeiro login).
ITERACOES_SENHA = 1_500_000

# Tabelas do UniRide, na ordem em que devem ser apagadas
# (primeiro as que dependem das outras)
TABELAS_UNIRIDE = ['Avaliacao', 'Solicitacao', 'Trajeto', 'Veiculo', 'Aluno']

# --- Dados de teste ---

# (chave, nome, e-mail, matrícula, curso, membro desde)
ALUNOS = [
    ('bernardo', 'Bernardo Souza', 'bernardo@puc-rio.br', '2410101', 'Engenharia de Computação', '2024-03-04'),
    ('ana', 'Ana Ribeiro', 'ana.ribeiro@puc-rio.br', '2310202', 'Administração', '2024-02-19'),
    ('lucas', 'Lucas Ferreira', 'lucas.ferreira@puc-rio.br', '2220303', 'Engenharia de Produção', '2024-08-12'),
    ('mariana', 'Mariana Costa', 'mariana.costa@puc-rio.br', '2410404', 'Direito', '2025-03-10'),
    ('joao', 'João Almeida', 'joao.almeida@puc-rio.br', '2510505', 'Economia', '2025-08-04'),
    ('sofia', 'Sofia Martins', 'sofia.martins@puc-rio.br', '2410606', 'Design', '2024-09-02'),
    ('rafael', 'Rafael Lima', 'rafael.lima@puc-rio.br', '2310707', 'Engenharia Mecânica', '2024-03-18'),
    ('camila', 'Camila Duarte', 'camila.duarte@puc-rio.br', '2210808', 'Psicologia', '2023-08-21'),
    ('beatriz', 'Beatriz Rocha', 'beatriz.rocha@puc-rio.br', '2510909', 'Comunicação Social', '2025-08-11'),
    ('gustavo', 'Gustavo Alves', 'gustavo.alves@puc-rio.br', '2411010', 'Arquitetura e Urbanismo', '2024-08-05'),
    ('larissa', 'Larissa Mendes', 'larissa.mendes@puc-rio.br', '2311111', 'Relações Internacionais', '2024-03-11'),
    ('diego', 'Diego Nogueira', 'diego.nogueira@puc-rio.br', '2511212', 'Ciência da Computação', '2025-03-17'),
]

# (chave do motorista, placa, modelo, cor)
VEICULOS = [
    ('bernardo', 'RIO2A24', 'Chevrolet Onix', 'Prata'),
    ('ana', 'KRT4B19', 'Hyundai HB20', 'Branco'),
    ('lucas', 'LQX7C31', 'Volkswagen Gol', 'Preto'),
    ('mariana', 'MCS3D58', 'Renault Kwid', 'Vermelho'),
    ('rafael', 'GVA5E62', 'Toyota Corolla', 'Cinza'),
    ('camila', 'TJC8F07', 'Fiat Argo', 'Azul'),
]

SEG_A_SEX = 'seg,ter,qua,qui,sex'

# (chave do trajeto, chave do aluno, tipo, origem, horário, vagas, dias)
TRAJETOS = [
    # Ofertas de carona (quem tem carro)
    ('of_bernardo', 'bernardo', 'OFERECE', 'Botafogo', '07:20', 2, SEG_A_SEX),
    ('of_ana', 'ana', 'OFERECE', 'Botafogo', '07:20', 2, 'seg,qua,sex'),
    ('of_lucas', 'lucas', 'OFERECE', 'Flamengo', '07:30', 3, SEG_A_SEX),
    ('of_mariana', 'mariana', 'OFERECE', 'Humaitá', '07:15', 1, 'ter,qui'),
    ('of_rafael', 'rafael', 'OFERECE', 'Leblon', '07:40', 3, 'seg,qua'),
    ('of_camila', 'camila', 'OFERECE', 'Tijuca', '06:50', 4, SEG_A_SEX),
    # Procuras de carona (vagas = 0)
    ('pr_joao', 'joao', 'PROCURA', 'Botafogo', '07:20', 0, SEG_A_SEX),
    ('pr_sofia', 'sofia', 'PROCURA', 'Botafogo', '07:15', 0, 'seg,qua,sex'),
    ('pr_beatriz', 'beatriz', 'PROCURA', 'Copacabana', '07:30', 0, 'ter,qui'),
    ('pr_gustavo', 'gustavo', 'PROCURA', 'Laranjeiras', '07:20', 0, SEG_A_SEX),
    ('pr_larissa', 'larissa', 'PROCURA', 'Jardim Botânico', '08:00', 0, 'seg,qua'),
    ('pr_diego', 'diego', 'PROCURA', 'Flamengo', '07:30', 0, 'seg,ter,qui'),
]

# (chave da solicitação, chave do trajeto oferecido, chave do passageiro, status, data em UTC)
SOLICITACOES = [
    ('s_bernardo_ana', 'of_ana', 'bernardo', 'ACEITA', '2026-08-10 12:00:00'),     # "Carona ativa" do Bernardo
    ('s_joao_bernardo', 'of_bernardo', 'joao', 'PENDENTE', '2026-10-08 22:15:00'),  # solicitação recebida
    ('s_sofia_bernardo', 'of_bernardo', 'sofia', 'PENDENTE', '2026-10-09 13:40:00'),  # solicitação recebida
    ('s_gustavo_lucas', 'of_lucas', 'gustavo', 'ACEITA', '2026-08-17 14:05:00'),
    ('s_diego_lucas', 'of_lucas', 'diego', 'ACEITA', '2026-08-24 18:30:00'),
    ('s_beatriz_mariana', 'of_mariana', 'beatriz', 'ACEITA', '2026-08-25 11:20:00'),
    ('s_larissa_rafael', 'of_rafael', 'larissa', 'RECUSADA', '2026-09-01 20:45:00'),
]

# (chave da solicitação, chave do avaliador, chave do avaliado, estrelas, comentário, data em UTC)
AVALIACOES = [
    ('s_bernardo_ana', 'bernardo', 'ana', 5, 'Pontual e muito simpática. Recomendo!', '2026-08-14 13:00:00'),
    ('s_bernardo_ana', 'ana', 'bernardo', 5, 'Sempre no ponto combinado.', '2026-08-14 15:10:00'),
    ('s_gustavo_lucas', 'gustavo', 'lucas', 4, 'Saiu uns minutos atrasado, mas a viagem foi tranquila.', '2026-08-21 12:30:00'),
    ('s_gustavo_lucas', 'lucas', 'gustavo', 5, '', '2026-08-21 19:00:00'),
    ('s_diego_lucas', 'diego', 'lucas', 5, 'Ótima conversa no caminho.', '2026-08-28 12:15:00'),
    ('s_diego_lucas', 'lucas', 'diego', 4, '', '2026-08-28 20:40:00'),
    ('s_beatriz_mariana', 'beatriz', 'mariana', 5, 'Carro limpo e direção cuidadosa.', '2026-08-27 13:50:00'),
    ('s_beatriz_mariana', 'mariana', 'beatriz', 5, 'Super educada.', '2026-08-27 16:25:00'),
]


def gera_hash_senha(senha: str) -> str:
    """
    Gera a senha no mesmo formato que o Django guarda na tabela auth_user
    (pbkdf2_sha256$iterações$sal$hash), para os usuários de teste conseguirem fazer login.
    :param senha: Senha em texto puro.
    :return: Senha criptografada no formato do Django.
    """
    alfabeto = string.ascii_letters + string.digits
    sal = ''.join(secrets.choice(alfabeto) for _ in range(22))
    chave = hashlib.pbkdf2_hmac('sha256', senha.encode(), sal.encode(), ITERACOES_SENHA)
    hash_b64 = base64.b64encode(chave).decode('ascii').strip()
    return f"pbkdf2_sha256${ITERACOES_SENHA}${sal}${hash_b64}"


def verifica_tabelas(cursor: sqlite3.Cursor) -> bool:
    """
    Verifica se as tabelas do UniRide já foram criadas pelo `python manage.py migrate`.
    :param cursor: Cursor aberto no banco de destino.
    :return: True se todas as tabelas existem.
    """
    cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    existentes = {linha[0] for linha in cursor.fetchall()}
    faltando = [t for t in TABELAS_UNIRIDE + ['auth_user'] if t not in existentes]
    if faltando:
        print(f"Tabelas não encontradas: {', '.join(faltando)}")
        print("Rode `python manage.py migrate` antes deste script.")
        return False
    return True


def limpa_dados(cursor: sqlite3.Cursor, emails: List[str]):
    """
    Apaga os dados das tabelas do UniRide e os usuários de teste
    para o script poder ser executado várias vezes sem duplicar registros.
    :param cursor: Cursor aberto no banco de destino.
    :param emails: E-mails (nomes de usuário) dos usuários de teste.
    :return: None
    """
    for tabela in TABELAS_UNIRIDE:
        cursor.execute(f"DELETE FROM {tabela}")

    # Faz os ids das tabelas do UniRide recomeçarem do 1
    placeholders = ', '.join(['?'] * len(TABELAS_UNIRIDE))
    cursor.execute(f"DELETE FROM sqlite_sequence WHERE name IN ({placeholders})", TABELAS_UNIRIDE)

    # Apaga somente os usuários de teste (nunca um superusuário)
    placeholders = ', '.join(['?'] * len(emails))
    filtro = f"SELECT id FROM auth_user WHERE username IN ({placeholders}) AND is_superuser = 0"
    cursor.execute(f"DELETE FROM auth_user_groups WHERE user_id IN ({filtro})", emails)
    cursor.execute(f"DELETE FROM auth_user_user_permissions WHERE user_id IN ({filtro})", emails)
    cursor.execute(f"DELETE FROM auth_user WHERE id IN ({filtro})", emails)
    print("Dados anteriores apagados.")


def insere_alunos(cursor: sqlite3.Cursor) -> Dict[str, int]:
    """
    Cria um usuário do Django (tabela auth_user) e um registro na tabela Aluno para cada aluno de teste.
    :param cursor: Cursor aberto no banco de destino.
    :return: Dicionário {chave do aluno: id na tabela Aluno}.
    """
    ids = {}
    for chave, nome, email, matricula, curso, membro_desde in ALUNOS:
        primeiro_nome, _, sobrenome = nome.partition(' ')
        cursor.execute(
            """
            INSERT INTO auth_user (password, last_login, is_superuser, username, first_name, last_name,
                                   email, is_staff, is_active, date_joined)
            VALUES (?, NULL, 0, ?, ?, ?, ?, 0, 1, ?)
            """,
            (gera_hash_senha(SENHA_PADRAO), email, primeiro_nome, sobrenome, email, membro_desde + ' 12:00:00'),
        )
        usuario_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO Aluno (usuario_id, nome, email, matricula, curso, membro_desde)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (usuario_id, nome, email, matricula, curso, membro_desde),
        )
        ids[chave] = cursor.lastrowid
        print(f"  Aluno criado: {nome} ({email})")
    return ids


def insere_veiculos(cursor: sqlite3.Cursor, alunos: Dict[str, int]):
    """
    Insere os veículos dos alunos que oferecem carona.
    :param cursor: Cursor aberto no banco de destino.
    :param alunos: Dicionário {chave do aluno: id na tabela Aluno}.
    :return: None
    """
    dados = [(alunos[motorista], placa, modelo, cor) for motorista, placa, modelo, cor in VEICULOS]
    cursor.executemany("INSERT INTO Veiculo (motorista_id, placa, modelo, cor) VALUES (?, ?, ?, ?)", dados)
    print(f"  {len(dados)} veículos inseridos.")


def insere_trajetos(cursor: sqlite3.Cursor, alunos: Dict[str, int]) -> Dict[str, int]:
    """
    Insere os trajetos (ofertas e procuras de carona).
    :param cursor: Cursor aberto no banco de destino.
    :param alunos: Dicionário {chave do aluno: id na tabela Aluno}.
    :return: Dicionário {chave do trajeto: id na tabela Trajeto}.
    """
    ids = {}
    for chave, aluno, tipo, origem, horario, vagas, dias in TRAJETOS:
        marcados = dias.split(',')
        flags = [1 if dia in marcados else 0 for dia in ['dom', 'seg', 'ter', 'qua', 'qui', 'sex', 'sab']]
        cursor.execute(
            """
            INSERT INTO Trajeto (aluno_id, tipo, origem, destino, horario, vagas,
                                 dom, seg, ter, qua, qui, sex, sab, ativo)
            VALUES (?, ?, ?, 'PUC-Rio', ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (alunos[aluno], tipo, origem, horario + ':00', vagas, *flags),
        )
        ids[chave] = cursor.lastrowid
    print(f"  {len(ids)} trajetos inseridos.")
    return ids


def insere_solicitacoes(cursor: sqlite3.Cursor, alunos: Dict[str, int], trajetos: Dict[str, int]) -> Dict[str, int]:
    """
    Insere os pedidos de carona (pendentes, aceitos e recusados).
    :param cursor: Cursor aberto no banco de destino.
    :param alunos: Dicionário {chave do aluno: id na tabela Aluno}.
    :param trajetos: Dicionário {chave do trajeto: id na tabela Trajeto}.
    :return: Dicionário {chave da solicitação: id na tabela Solicitacao}.
    """
    ids = {}
    for chave, trajeto, passageiro, status, data in SOLICITACOES:
        cursor.execute(
            "INSERT INTO Solicitacao (trajeto_id, passageiro_id, status, data_criacao) VALUES (?, ?, ?, ?)",
            (trajetos[trajeto], alunos[passageiro], status, data),
        )
        ids[chave] = cursor.lastrowid
    print(f"  {len(ids)} solicitações inseridas.")
    return ids


def insere_avaliacoes(cursor: sqlite3.Cursor, alunos: Dict[str, int], solicitacoes: Dict[str, int]):
    """
    Insere as avaliações feitas depois das caronas aceitas.
    :param cursor: Cursor aberto no banco de destino.
    :param alunos: Dicionário {chave do aluno: id na tabela Aluno}.
    :param solicitacoes: Dicionário {chave da solicitação: id na tabela Solicitacao}.
    :return: None
    """
    dados: List[Tuple] = [
        (solicitacoes[solicitacao], alunos[avaliador], alunos[avaliado], estrelas, comentario, data)
        for solicitacao, avaliador, avaliado, estrelas, comentario, data in AVALIACOES
    ]
    cursor.executemany(
        """
        INSERT INTO Avaliacao (solicitacao_id, avaliador_id, avaliado_id, estrelas, comentario, data)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        dados,
    )
    print(f"  {len(dados)} avaliações inseridas.")


def main():
    """
    Função principal para coordenar a população do banco de dados.
    :return: None
    """
    print("--- INICIANDO POPULAÇÃO DO BANCO UniRide ---")
    print(f"Conectando ao banco de destino: {DB_DESTINO}...")
    conn = sqlite3.connect(DB_DESTINO)
    conn.execute("PRAGMA foreign_keys = ON")  # garante que as chaves estrangeiras sejam respeitadas
    cursor = conn.cursor()

    if not verifica_tabelas(cursor):
        conn.close()
        return

    try:
        limpa_dados(cursor, [aluno[2] for aluno in ALUNOS])
        print("Inserindo dados (criar as senhas pode levar uns 15 segundos)...")
        alunos = insere_alunos(cursor)
        insere_veiculos(cursor, alunos)
        trajetos = insere_trajetos(cursor, alunos)
        solicitacoes = insere_solicitacoes(cursor, alunos, trajetos)
        insere_avaliacoes(cursor, alunos, solicitacoes)

        # Confirma as mudanças
        conn.commit()
        print(f"Inserção concluída! Senha de todos os usuários de teste: {SENHA_PADRAO}")
    except sqlite3.Error as e:
        print(f"Erro ao popular o banco de dados: {e}")
        # Se ocorrer um erro, desfaz tudo o que foi feito nesta execução
        conn.rollback()
    finally:
        conn.close()

    print("--- PROCESSO CONCLUÍDO ---")


if __name__ == "__main__":
    main()
