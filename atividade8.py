from datetime import datetime, timezone

import numpy as np
from flask import Flask, jsonify, request
from pymongo import MongoClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import confusion_matrix, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split


app = Flask(__name__)
mongo = MongoClient("mongodb://localhost:27017/")
previsoes = mongo["seguranca"]["previsoes"]


def treinar_modelo():
    rng = np.random.default_rng(42)
    normais = np.column_stack([
        rng.integers(0, 4, 400),
        rng.integers(1, 5, 400),
        rng.integers(500, 18000, 400),
        rng.integers(7, 23, 400)
    ])
    riscosos = np.column_stack([
        rng.integers(8, 31, 400),
        rng.integers(6, 26, 400),
        rng.integers(50000, 220000, 400),
        rng.integers(0, 7, 400)
    ])
    entradas = np.vstack([normais, riscosos])
    rotulos = np.concatenate([np.zeros(len(normais), dtype=int), np.ones(len(riscosos), dtype=int)])
    
    x_treino, x_teste, y_treino, y_teste = train_test_split(
        entradas, rotulos, test_size=0.25, random_state=42, stratify=rotulos
    )
    
    modelo = RandomForestClassifier(n_estimators=200, random_state=42)
    modelo.fit(x_treino, y_treino)
    
    previstos = modelo.predict(x_teste)
    metricas = {
        "precisao": round(float(precision_score(y_teste, previstos, zero_division=0)), 4),
        "recall": round(float(recall_score(y_teste, previstos, zero_division=0)), 4),
        "f1": round(float(f1_score(y_teste, previstos, zero_division=0)), 4),
        "matriz": confusion_matrix(y_teste, previstos).tolist(),
        "aviso": "A acurácia foi omitida porque pode esconder falhas importantes quando as classes estão desbalanceadas.",
    }
    return modelo, metricas


modelo, METRICAS = treinar_modelo()


def validar_features(corpo):
    if not isinstance(corpo, dict) or "features" not in corpo:
        return None, "corpo JSON com campo features é obrigatório"
    features = corpo["features"]
    if not isinstance(features, list):
        return None, "features deve ser uma lista"
    if len(features) != 4:
        return None, f"esperadas 4 features, recebidas {len(features)}"
    if any(isinstance(valor, bool) or not isinstance(valor, (int, float)) for valor in features):
        return None, "features devem ser numéricas"
    if any(valor < 0 for valor in features[:3]) or not 0 <= features[3] <= 23:
        return None, "features fora dos intervalos permitidos"
    return [float(valor) for valor in features], None


@app.post("/api/triagem")
def triagem():
    features, erro = validar_features(request.get_json(silent=True))
    if erro:
        return jsonify({"erro": erro}), 400

    entrada = np.array([features])
    classe = int(modelo.predict(entrada)[0])
    probabilidades = modelo.predict_proba(entrada)[0]
    confianca = round(float(probabilidades[list(modelo.classes_).index(classe)]), 4)
    risco = "alto" if classe == 1 else "baixo"

    previsoes.insert_one({
        "entrada": features,
        "saida": risco,
        "confianca": confianca,
        "timestamp": datetime.now(timezone.utc),
    })

    return jsonify({"risco": risco, "confianca": confianca}), 200


@app.get("/api/modelo/metricas")
def metricas():
    return jsonify(METRICAS), 200


if __name__ == "__main__":
    previsoes.delete_many({})
    app.run(host="127.0.0.1", port=5000, debug=False)