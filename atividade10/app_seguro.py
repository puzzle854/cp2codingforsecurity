import hashlib
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import secrets
import sqlite3
import uuid

import mysql.connector
from flask import Flask, g, jsonify, render_template_string, request
from werkzeug.exceptions import HTTPException


def criar_app():
    app = Flask(__name__, static_folder=None)
    app.config.update(DEBUG=False, MAX_CONTENT_LENGTH=16384, TRUSTED_HOSTS=['127.0.0.1', 'localhost'])

    def obrigatoria(nome):
        valor = os.environ.get(nome, '')
        if not valor:
            raise RuntimeError(f'Configure a variável de ambiente {nome}.')
        return valor

    usuario_mysql = obrigatoria('MYSQL_USER')
    if usuario_mysql.lower() == 'root':
        raise RuntimeError('Utilize um usuário MySQL dedicado, não root. Veja o início do arquivo.')

    config_mysql = dict(host=os.environ.get('MYSQL_HOST', '127.0.0.1'), port=int(os.environ.get('MYSQL_PORT', '3306')), user=usuario_mysql, password=obrigatoria('MYSQL_PASSWORD'), database=os.environ.get('MYSQL_DATABASE', 'seguranca'), connection_timeout=5, autocommit=False)
    chaves = {}
    for variavel, uid in [('API_KEY_ANA', 1), ('API_KEY_BRUNO', 2)]:
        chave = obrigatoria(variavel)
        if len(chave) < 32:
            raise RuntimeError(f'{variavel}: gere uma chave aleatória com secrets.token_urlsafe(32).')
        digest = hashlib.sha256(chave.encode()).digest()
        if digest in chaves:
            raise RuntimeError('Cada usuário precisa de uma chave diferente.')
        chaves[digest] = uid

    caminho_auditoria = Path(os.environ.get('AUDIT_DB', str(Path(__file__).with_name('auditoria_desafio10.sqlite3'))))

    @contextmanager
    def audit_db():
        con = sqlite3.connect(caminho_auditoria, timeout=5)
        try:
            with con:
                yield con
        finally:
            con.close()

    with audit_db() as con:
        con.execute('CREATE TABLE IF NOT EXISTS auditoria (id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, metodo TEXT NOT NULL, rota TEXT NOT NULL, ip TEXT, quem INTEGER, alvo INTEGER, status INTEGER, resultado TEXT NOT NULL)')

    @contextmanager
    def banco():
        con = mysql.connector.connect(**config_mysql)
        try:
            cur = con.cursor(dictionary=True)
            try:
                yield con, cur
            except Exception:
                con.rollback()
                raise
            finally:
                cur.close()
        finally:
            con.close()

    @app.before_request
    def iniciar_auditoria():
        g.request_id = uuid.uuid4().hex
        g.quem = None
        g.audit_ok = False
        alvo = (request.view_args or {}).get('uid')
        rota = request.url_rule.rule if request.url_rule else '(rota inexistente)'
        try:
            with audit_db() as con:
                con.execute('INSERT INTO auditoria (id, timestamp, metodo, rota, ip, alvo, resultado) VALUES (?, ?, ?, ?, ?, ?, ?)', (g.request_id, datetime.now(timezone.utc).isoformat(), request.method, rota, request.remote_addr, alvo, 'INICIADA'))
            g.audit_ok = True
        except sqlite3.Error:
            app.logger.critical('ALERTA: auditoria indisponível; requisição bloqueada.')
            return jsonify(erro='serviço indisponível'), 503

    @app.after_request
    def finalizar_resposta(resposta):
        if getattr(g, 'audit_ok', False):
            codigo = resposta.status_code
            resultado = 'RECUSADO' if codigo in (401, 403) else 'ERRO' if codigo >= 400 else 'OK'
            try:
                with audit_db() as con:
                    con.execute('UPDATE auditoria SET quem = ?, status = ?, resultado = ? WHERE id = ?', (g.quem, codigo, resultado, g.request_id))
            except sqlite3.Error:
                app.logger.critical('ALERTA: falha na conclusão da auditoria; reconciliar request_id=%s', g.request_id)
                resposta = app.make_response((jsonify(erro='serviço indisponível'), 503))
            if codigo in (401, 403) or codigo >= 500:
                app.logger.warning('ALERTA de segurança: request_id=%s status=%s', g.request_id, codigo)

        resposta.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        resposta.headers['X-Content-Type-Options'] = 'nosniff'
        resposta.headers['X-Frame-Options'] = 'DENY'
        resposta.headers['Cache-Control'] = 'no-store'
        resposta.headers['Referrer-Policy'] = 'no-referrer'
        return resposta

    @app.errorhandler(Exception)
    def tratar_erro(erro):
        if isinstance(erro, HTTPException) and erro.code < 500:
            resposta = erro.get_response()
            resposta.set_data(app.json.dumps({'erro': erro.name}))
            resposta.content_type = 'application/json'
            return resposta
        app.logger.error('Falha interna: tipo=%s request_id=%s', type(erro).__name__, getattr(g, 'request_id', 'indisponível'))
        return jsonify(erro='erro interno'), 500

    @app.get('/api/usuarios/buscar')
    def buscar():
        nome = request.args.get('nome', '')
        if len(nome) > 100:
            return jsonify(erro='nome deve ter no máximo 100 caracteres'), 400
        with banco() as (_, cur):
            cur.execute('SELECT id, nome FROM usuarios WHERE nome LIKE %s ORDER BY id LIMIT %s', (f'%{nome}%', 100))
            usuarios = cur.fetchall()
        return jsonify(usuarios)

    @app.get('/perfil')
    def perfil():
        nome = request.args.get('u', '')
        if len(nome) > 500:
            return jsonify(erro='nome muito longo'), 400
        return render_template_string('<!doctype html><html lang="pt-BR"><meta charset="utf-8"><title>Perfil</title><h1>Bem-vindo, {{ nome }}</h1></html>', nome=nome)

    @app.delete('/api/usuarios/<int:uid>')
    def remover(uid):
        chave = request.headers.get('X-API-Key', '')
        if not chave or len(chave) > 512:
            return jsonify(erro='autenticação necessária'), 401
        recebido = hashlib.sha256(chave.encode()).digest()
        identidade = None
        for esperado, pessoa in chaves.items():
            if secrets.compare_digest(recebido, esperado):
                identidade = pessoa
        if identidade is None:
            return jsonify(erro='autenticação inválida'), 401

        with banco() as (con, cur):
            cur.execute('SELECT id, nivel_acesso FROM usuarios WHERE id = %s FOR UPDATE', (identidade,))
            admin = cur.fetchone()
            if admin is None:
                con.rollback()
                return jsonify(erro='autenticação inválida'), 401
            g.quem = admin['id']
            if admin['nivel_acesso'] < 5:
                con.rollback()
                return jsonify(erro='acesso negado'), 403
            cur.execute('DELETE FROM usuarios WHERE id = %s', (uid,))
            if cur.rowcount == 0:
                con.rollback()
                return jsonify(erro='usuário não encontrado'), 404
            con.commit()
        return jsonify(removido=uid)

    @app.get('/api/relatorio')
    def relatorio():
        if os.environ.get('RELATORIO_TESTE_ERRO', '1') == '1':
            raise RuntimeError('Falha controlada do laboratório')
        with banco() as (_, cur):
            cur.execute('SELECT COUNT(*) AS total_usuarios FROM usuarios')
            relatorio = cur.fetchone()
        return jsonify(relatorio)

    return app


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('werkzeug').disabled = True
    app = criar_app()
    app.run(host='127.0.0.1', port=5000, debug=False, use_reloader=False)