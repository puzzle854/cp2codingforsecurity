import mysql.connector
from pymongo import MongoClient
from datetime import datetime

conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="senha",
    database="seguranca"
)

cursor = conexao.cursor(dictionary=True)

cliente_mongo = MongoClient("mongodb://localhost:27017/")
auditoria = cliente_mongo["seguranca"]["auditoria"]

def alterar_nivel(admin_id, alvo_id, novo_nivel):
    cursor.execute("SELECT id, nome, email, nivel_acesso FROM usuarios WHERE id = %s", (admin_id,))
    admin = cursor.fetchone()
    cursor.execute("SELECT id, nome, email, nivel_acesso FROM usuarios WHERE id = %s", (alvo_id,))
    alvo = cursor.fetchone()

    print(f"Administrador: {admin}")
    print(f"Alvo: {alvo}")

    if not admin or not alvo:
        conexao.rollback()
        resultado, motivo = "RECUSADO", "usuário administrador ou alvo não encontrado"
        print(f"Erro: {motivo.capitalize()}.")
    elif int(admin['nivel_acesso']) < 5:
        conexao.rollback()
        resultado, motivo = "RECUSADO", "usuário sem permissão para alterar níveis"
        print(f"Erro: O usuário não tem permissão para alterar níveis de acesso.")
    elif admin == alvo:
        conexao.rollback()
        resultado, motivo = "RECUSADO", "usuário tentou alterar seu próprio nível"
        print(f"Erro: Um usuário não pode alterar seu próprio nível de acesso.")
    else:
        cursor.execute("UPDATE usuarios SET nivel_acesso = %s WHERE id = %s", (novo_nivel, alvo_id))
        conexao.commit()
        resultado, motivo = "OK", "nível alterado"

    auditoria.insert_one({
        "admin_id": admin_id,
        "alvo_id": alvo_id,
        "nivel_novo": novo_nivel,
        "resultado": resultado,
        "timestamp": datetime.now()
    })

    print(f"{resultado}: admin={admin_id}, alvo={alvo_id}, novo nível: {novo_nivel}. {motivo}")

alterar_nivel(1, 2, 4)
alterar_nivel(2, 3, 5)
alterar_nivel(1, 1, 9)
alterar_nivel(1, 99, 3)

cursor.execute("SELECT id, nome, nivel_acesso FROM usuarios ORDER BY id")

for usuario in cursor.fetchall():
    print(usuario)

total = auditoria.count_documents({})
recusadas = auditoria.count_documents({"resultado": "RECUSADO"})

print(f"Total de auditorias: {total}")
print(f"Tentativas recusadas: {recusadas}")