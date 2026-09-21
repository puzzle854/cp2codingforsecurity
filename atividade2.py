from pymongo import MongoClient
import mysql.connector
from mysql.connector import Error

conexao = None
cliente_mongo = None

try:
    conexao = mysql.connector.connect(
        host="localhost",
        user="root",
        password="senha",
        database="seguranca"
    )

    print("Conectado ao MySQL!")

    cursor = conexao.cursor(dictionary=True)

    consulta = """
        SELECT
            al.tipo,
            al.severidade,
            at.nome,
            at.ip,
            at.criticidade
        FROM alertas AS al
        INNER JOIN ativos AS at
            ON al.ativo_id = at.id
        WHERE al.id >= %s
    """

    cursor.execute(consulta, (1,))
    resultados = cursor.fetchall()

    documentos = []

    for linha in resultados:
        documento = {
            "tipo": linha["tipo"],
            "severidade": linha["severidade"],
            "ativo": {
                "nome": linha["nome"],
                "ip": linha["ip"],
                "criticidade": linha["criticidade"]
            }
        }

        documentos.append(documento)

    cliente_mongo = MongoClient("mongodb://localhost:27017/")
    banco_mongo = cliente_mongo["seguranca"]
    colecao_alertas = banco_mongo["alertas"]

    colecao_alertas.delete_many({})

    if documentos:
        resultado_mongo = colecao_alertas.insert_many(documentos)

        print(
            f"Documentos inseridos: "
            f"{len(resultado_mongo.inserted_ids)}"
        )

    cursor.execute("SELECT COUNT(*) AS total FROM alertas")
    total_mysql = cursor.fetchone()["total"]

    total_mongo = colecao_alertas.count_documents({})

    if total_mysql == total_mongo:
        status = "MIGRAÇÃO ÍNTEGRA"
    else:
        status = "MIGRAÇÃO FALHA"

    print(
        f"MySQL: {total_mysql} alertas | "
        f"MongoDB: {total_mongo} documentos -> {status}"
    )

except Error as erro:
    print(f"Erro no MySQL: {erro}")

except Exception as erro:
    print(f"Erro durante a migração: {erro}")

finally:
    if conexao is not None and conexao.is_connected():
        cursor.close()
        conexao.close()

    if cliente_mongo is not None:
        cliente_mongo.close()