from flask import Flask, jsonify, request
import mysql.connector

app = Flask(__name__)

def conectar_mysql():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="senha",
        database="seguranca"
    )

def autenticar():
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return None

    conexao = conectar_mysql()
    cursor = conexao.cursor(dictionary=True)
    try:
        cursor.execute("SELECT id, nome, nivel FROM analistas WHERE api_key = %s", (api_key,))
        return cursor.fetchone()
    finally:
        cursor.close()
        conexao.close()

@app.get("/api/incidentes/<int:incidente_id>")
def get_incidentes(incidente_id):
    analista = autenticar()
    if analista is None:
        return jsonify({"error": "Autenticação falhou"}), 401

    conexao = conectar_mysql()
    cursor = conexao.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM incidentes WHERE id = %s", (incidente_id,))
        incidente = cursor.fetchone()

        if incidente is None:
            return jsonify({"erro": "incidente não encontrado"}), 404

        if incidente["dono_id"] != analista["id"]:
            return jsonify({"erro": "acesso negado"}), 403

        return jsonify(incidente), 200
    finally:
        cursor.close()
        conexao.close()

if __name__ == "__main__":
    app.run()