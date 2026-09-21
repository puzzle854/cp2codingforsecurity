from datetime import datetime, timedelta
import random
from pymongo import MongoClient

cliente = MongoClient("mongodb://localhost:27017/")
banco = cliente["seguranca"]
eventos = banco["eventos"]

eventos.delete_many({})

if "ttl_7_dias" in eventos.index_information():
    eventos.drop_index("ttl_7_dias")

eventos.create_index(
    "timestamp",
    expireAfterSeconds=604800,
    name="ttl_7_dias"
)

agora = datetime.now()
documentos = [
    {
        "timestamp": agora - timedelta(seconds=random.randint(0, 86400)),
        "tipo": "FAIL",
        "fonte": "auth",
        "ip": f"192.168.1.{random.randint(1, 254)}"
    }
    for _ in range(200)
]

eventos.insert_many(documentos)
print(f"Eventos inseridos: {eventos.count_documents({})}")

inicio_janela = datetime.now() - timedelta(hours=24)
pipeline = [
    {
        "$match": {
            "tipo": "FAIL",
            "timestamp": {"$gte": inicio_janela}
        }
    },
    {
        "$group": {
            "_id": {"$hour": "$timestamp"},
            "total": {"$sum": 1}
        }
    },
    {
        "$sort": {"_id": 1}
    }
]

resultado = list(eventos.aggregate(pipeline))

print("\n=== Falhas por hora (últimas 24h) ===")
for item in resultado:
    hora = item["_id"]
    total = item["total"]
    barra = "█" * total
    print(f"{hora:02d}h | {barra} {total}")

if resultado:
    pico = max(resultado, key=lambda item: item["total"])
    print(f"\nHora de pico: {pico['_id']:02d}h ({pico['total']} falhas)")

print("Índice TTL ativo: eventos com mais de 7 dias serão removidos automaticamente.")

cliente.close()