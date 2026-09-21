from flask import Flask, jsonify, request
import mysql.connector

app = Flask(__name__)

conexao = mysql.connector.connect(
    host="localhost",
    user="root",
    password="senha",
    database="seguranca"
)

print("Conectado ao MySQL!")

COLUNAS = {
    "data": "criado_em",
    "sev": "severidade",
    "ip": "ip_origem"
}

ORDENS = {
    "asc": "ASC",
    "desc": "DESC"
}

@app.get("/api/eventos")
def get_eventos():
    ordenar_por = request.args.get("ordenar_por", "data")
    ordem = request.args.get("ordem", "desc")
    tamanho_texto = request.args.get("tamanho", "20")

    if ordenar_por not in COLUNAS:
        return jsonify({"erro": "Parâmetro 'ordenar_por' inválido"}), 400

    if ordem not in ORDENS:
        return jsonify({"erro": "Parâmetro 'ordem' inválido"}), 400

    if not tamanho_texto.isdigit() or int(tamanho_texto) <= 0 or int(tamanho_texto) > 1000:
        return jsonify({"erro": "Parâmetro 'tamanho' inválido"}), 400

    try:
        tamanho = int(tamanho_texto)
    except ValueError:
        return jsonify({
            "erro": "tamanho deve ser inteiro"
        }), 400

    coluna_sql = COLUNAS[ordenar_por]
    ordem_sql = ORDENS[ordem]

    cursor = conexao.cursor(dictionary=True)
    try:
        cursor.execute(f"SELECT id, tipo, severidade, ip_origem, criado_em FROM eventos ORDER BY {coluna_sql} {ordem_sql} LIMIT %s", (tamanho,))
        resultados = cursor.fetchall()
        
        eventos = []
        for linha in resultados:
            if "criado_em" in linha and linha["criado_em"]:
                linha["criado_em"] = linha["criado_em"].strftime("%Y-%m-%d %H:%M:%S")
            eventos.append(linha)

        return jsonify(eventos)
    finally:
        cursor.close()

if __name__ == "__main__":
    app.run()