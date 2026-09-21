from flask import Flask, render_template_string
from pymongo import MongoClient

app = Flask(__name__)
mongo = MongoClient("mongodb://localhost:27017/")
incidentes = mongo["seguranca"]["incidentes_xss"]

P1 = "<script>alert('xss1')</script>"
P2 = 'x" onerror="alert(\'xss2\')'

def popular_laboratorio():
    incidentes.delete_many({})
    incidentes.insert_many([
        {"titulo": P1, "ativo": "SRV-WEB01", "severidade": "critica"},
        {"titulo": "Tentativa de XSS em atributo", "ativo": P2, "severidade": "alta"},
    ])

TEMPLATE_SEGURO = """
<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Dashboard seguro</title>
  <style>
    body { font-family: sans-serif; margin: 2rem; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #bbb; padding: .6rem; text-align: left; }
    .seguro { color: #146c2e; font-weight: bold; }
  </style>
</head>
<body>
  <h1>Dashboard seguro</h1>
  <p class="seguro">Jinja2 escapando texto e atributos automaticamente.</p>
  <table>
    <thead><tr><th>Título</th><th>Ativo</th><th>Severidade</th></tr></thead>
    <tbody>
    {% for incidente in incidentes %}
      <tr>
        <td>{{ incidente.titulo }}</td>
        <td><img src="/icone.png" alt="{{ incidente.ativo }}"> {{ incidente.ativo }}</td>
        <td>{{ incidente.severidade }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  <p><a href="/dashboard-inseguro">Comparar com a versão insegura</a></p>
</body>
</html>
"""

TEMPLATE_INSEGURO = """
<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><title>Dashboard inseguro</title></head>
<body>
  <h1>⚠️ DASHBOARD INSEGURO — SOMENTE LABORATÓRIO LOCAL</h1>
  <p>O uso de <code>|safe</code> abaixo remove o escape do Jinja2. A CSP ainda bloqueia scripts inline.</p>
  <table border="1" cellpadding="8">
    <thead><tr><th>Título</th><th>Ativo</th><th>Severidade</th></tr></thead>
    <tbody>
    {% for incidente in incidentes %}
      <tr>
        <td>{{ incidente.titulo|safe }}</td>
        <td><img src="/icone.png" alt="{{ incidente.ativo|safe }}"> {{ incidente.ativo|safe }}</td>
        <td>{{ incidente.severidade }}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
  <p><a href="/dashboard">Voltar à versão segura</a></p>
</body>
</html>
"""

@app.after_request
def aplicar_csp(resposta):
    resposta.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'"
    return resposta

@app.get("/dashboard")
def dashboard():
    dados = list(incidentes.find({}, {"_id": 0}))
    return render_template_string(TEMPLATE_SEGURO, incidentes=dados)

@app.get("/dashboard-inseguro")
def dashboard_inseguro():
    dados = list(incidentes.find({}, {"_id": 0}))
    return render_template_string(TEMPLATE_INSEGURO, incidentes=dados)

if __name__ == "__main__":
    popular_laboratorio()
    app.run(host="127.0.0.1", port=5000, debug=False)