import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import requests
from flask import Flask, g, jsonify, request
from pymongo import MongoClient
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


app = Flask(__name__)
mongo = MongoClient("mongodb://localhost:27017/")
db = mongo["seguranca"]
acessos = db["acessos"]
bloqueios = db["bloqueios"]


def obter_ip():
    return request.headers.get("X-Test-IP") or request.remote_addr or "desconhecido"


@app.before_request
def registrar_inicio():
    ip = obter_ip()
    registro = acessos.insert_one({
        "ip": ip,
        "rota": request.path,
        "metodo": request.method,
        "timestamp": datetime.now(timezone.utc),
        "status": None,
    })
    g.acesso_id = registro.inserted_id
    
    bloqueio = bloqueios.find_one({"ip": ip, "bloqueado_ate": {"$gt": datetime.now(timezone.utc)}})
    if bloqueio:
        resposta = jsonify({"erro": "muitas requisições"})
        resposta.status_code = 429
        resposta.headers["Retry-After"] = "60"
        return resposta
    return None


@app.after_request
def registrar_fim(resposta):
    if hasattr(g, "acesso_id"):
        acessos.update_one({"_id": g.acesso_id}, {"$set": {"status": resposta.status_code}})
    return resposta


@app.get("/api/recurso/<nome>")
def recurso(nome):
    return jsonify({"recurso": nome, "status": "ok"}), 200


def agregar_por_ip():
    pipeline = [
        {"$match": {"status": {"$ne": None}, "rota": {"$ne": "/api/analisar"}}},
        {"$group": {
            "_id": "$ip",
            "total": {"$sum": 1},
            "erros_4xx": {"$sum": {"$cond": [{"$and": [{"$gte": ["$status", 400]}, {"$lt": ["$status", 500]}]}, 1, 0]}},
            "rotas": {"$addToSet": "$rota"},
            "inicio": {"$min": "$timestamp"},
            "fim": {"$max": "$timestamp"},
        }},
    ]
    dados = []
    for item in acessos.aggregate(pipeline):
        duracao_min = max((item["fim"] - item["inicio"]).total_seconds() / 60, 1 / 60)
        dados.append({
            "ip": item["_id"],
            "req_por_minuto": item["total"] / duracao_min,
            "taxa_4xx": item["erros_4xx"] / item["total"],
            "rotas_distintas": len(item["rotas"]),
        })
    return dados


@app.post("/api/analisar")
def analisar():
    dados = agregar_por_ip()
    if len(dados) < 2:
        return jsonify({"erro": "são necessários acessos de pelo menos 2 IPs"}), 400

    matriz = np.array([[d["req_por_minuto"], d["taxa_4xx"], d["rotas_distintas"]] for d in dados], dtype=float)
    referencia_normal = np.array([
        [0.5, 0.00, 2],
        [1.0, 0.02, 2],
        [2.0, 0.05, 3],
        [3.0, 0.10, 3],
        [5.0, 0.08, 4]
    ], dtype=float)

    treino = np.vstack([referencia_normal, matriz])
    scaler = StandardScaler()
    treino_escalado = scaler.fit_transform(treino)

    modelo = IsolationForest(contamination=0.2, random_state=42)
    modelo.fit(treino_escalado)

    previsoes = modelo.predict(scaler.transform(matriz))
    relatorio = []
    agora = datetime.now(timezone.utc)

    for dado, previsao in zip(dados, previsoes):
        anomalia = int(previsao) == -1
        if anomalia:
            bloqueios.update_one(
                {"ip": dado["ip"]},
                {"$set": {"bloqueado_ate": agora + timedelta(seconds=60)}},
                upsert=True
            )
        relatorio.append({
            **dado,
            "classificacao": "ANOMALIA" if anomalia else "normal",
            "bloqueado": anomalia
        })

    print("=== Análise de acessos ===")
    for item in relatorio:
        destino = "ANOMALIA -> bloqueado" if item["bloqueado"] else "normal"
        print(f"{item['ip']:<16} [{item['req_por_minuto']:6.1f} req/min | 4xx {item['taxa_4xx']:.2f} | {item['rotas_distintas']} rotas] -> {destino}")

    return jsonify(relatorio), 200


def executar_teste():
    base = "http://127.0.0.1:5000"
    normal = {"X-Test-IP": "192.168.1.10"}
    hostil = {"X-Test-IP": "185.220.101.1"}

    for i in range(5):
        resposta = requests.get(f"{base}/api/recurso/{i % 2}", headers=normal, timeout=5)
        print("normal", resposta.status_code)
        time.sleep(2)

    for i in range(60):
        rota = f"/rota-inexistente-{i % 9}" if i < 40 else f"/api/recurso/{i % 2}"
        requests.get(base + rota, headers=hostil, timeout=5)
        time.sleep(0.15)

    analise = requests.post(f"{base}/api/analisar", headers=normal, timeout=10)
    print("análise", analise.status_code, analise.json())

    proxima = requests.get(f"{base}/api/recurso/final", headers=hostil, timeout=5)
    print("próxima hostil", proxima.status_code, proxima.text, "Retry-After:", proxima.headers.get("Retry-After"))


if __name__ == "__main__":
    if "--test" in sys.argv:
        executar_teste()
    else:
        acessos.delete_many({})
        bloqueios.delete_many({})
        
        app.run(host="127.0.0.1", port=5000, debug=False)