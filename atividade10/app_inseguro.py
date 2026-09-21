from flask import Flask, request, jsonify
import mysql.connector

app = Flask(__name__)

SENHA_MESTRA = "Cyber@2024"


def db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="senha",
        database="seguranca"
    )


@app.route("/api/usuarios/buscar")
def buscar():
    nome = request.args.get("nome", "")
    con = db()

    try:
        cur = con.cursor(dictionary=True)
        try:
            cur.execute(f"SELECT * FROM usuarios WHERE nome LIKE '%{nome}%'")
            usuarios = cur.fetchall()
        finally:
            cur.close()
    finally:
        con.close()

    return jsonify(usuarios)


@app.route("/perfil")
def perfil():
    return f"<h1>Bem-vindo, {request.args.get('u', '')}</h1>"


@app.route("/api/usuarios/<int:uid>", methods=["DELETE"])
def remover(uid):
    con = db()

    try:
        cur = con.cursor()
        try:
            cur.execute("DELETE FROM usuarios WHERE id = %s", (uid,))
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            cur.close()
    finally:
        con.close()

    return jsonify({"removido": uid})


@app.route("/api/relatorio")
def relatorio():
    con = db()

    try:
        cur = con.cursor()
        try:
            cur.execute("SELECT * FROM tabela_inexistente")
            registros = cur.fetchall()
        finally:
            cur.close()
    finally:
        con.close()

    return jsonify(registros)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1")