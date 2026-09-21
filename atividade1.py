perfis = {
    "credenciais_do_SOC": {"schema_fixo": True,  "precisa_acid": True,  "escala_horizontal": False, "tolera_atraso_de_consistencia": False, "dado_sensivel": True},
    "telemetria_de_sensores": {"schema_fixo": False, "precisa_acid": False, "escala_horizontal": True,  "tolera_atraso_de_consistencia": True,  "dado_sensivel": False},
    "trilha_de_auditoria": {"schema_fixo": False, "precisa_acid": False, "escala_horizontal": True,  "tolera_atraso_de_consistencia": False, "dado_sensivel": True},
    "carrinho_de_licencas": {"schema_fixo": True,  "precisa_acid": True,  "escala_horizontal": False, "tolera_atraso_de_consistencia": False, "dado_sensivel": False},
    "cache_de_sessoes": {"schema_fixo": True,  "precisa_acid": False, "escala_horizontal": True,  "tolera_atraso_de_consistencia": True,  "dado_sensivel": True},
}

def assinatura(perfil):
    return (
        perfil["schema_fixo"],
        perfil["precisa_acid"],
        perfil["escala_horizontal"],
        perfil["tolera_atraso_de_consistencia"],
        perfil["dado_sensivel"],
    )

def escolher_banco(perfil):
    return "MySQL" if (perfil["schema_fixo"] and perfil["precisa_acid"]) else "MongoDB"

def escolher_cap(perfil):
    if perfil["dado_sensivel"]:
        return "CP"
    return "AP" if perfil["tolera_atraso_de_consistencia"] else "CP"

JUSTIFICATIVAS = {
    (True, True, False, False, True): (
        "MySQL atende ao schema fixo e às transações ACID. "
        "Permitir acesso a um usuário revogado é inaceitável; "
        "é preferível bloquear temporariamente um acesso válido."
    ),
    (False, False, True, True, False): (
        "MongoDB aceita eventos com estruturas variadas e favorece a escala "
        "horizontal. Parar completamente de receber eventos durante um ataque "
        "é inaceitável; alguns segundos de atraso são toleráveis."
    ),
    (False, False, True, False, True): (
        "MongoDB atende ao schema variável e à escala horizontal. "
        "Históricos divergentes são inaceitáveis, pois a auditoria deixaria "
        "de provar com segurança quem realizou cada ação."
    ),
    (True, True, False, False, False): (
        "MySQL oferece schema fixo e transações ACID. Vender mais licenças "
        "do que existem é inaceitável, pois um cliente pode pagar sem "
        "receber o acesso adquirido."
    ),
    (True, False, True, True, True): (
        "MongoDB atende à necessidade de escala horizontal sem exigir ACID. "
        "Manter válido um token revogado é inaceitável, pois um atacante "
        "poderia continuar se passando pela vítima após o logout."
    ),
}

RISCOS_OWASP = {
    (True, True, False, False, True): (
        "A07 — uma réplica desatualizada pode autenticar um usuário "
        "cuja autorização já foi revogada."
    ),
    (False, False, True, True, False): (
        "A09 — interromper a coleta cria uma janela sem registros e alertas, "
        "permitindo que ataques ocorram sem detecção."
    ),
    (False, False, True, False, True): (
        "A08 — dados sem verificação de integridade podem ser alterados "
        "para ocultar ações e manipular o resultado da auditoria."
    ),
    (True, True, False, False, False): (
        "A06 — um projeto sem controle transacional pode vender a mesma "
        "licença mais de uma vez."
    ),
    (True, False, True, True, True): (
        "A07 — uma réplica desatualizada pode aceitar um token revogado "
        "e permitir que um atacante se passe pela vítima."
    ),
}

def recomendar(perfil):
    sig = assinatura(perfil)
    return {
        "banco": escolher_banco(perfil),
        "cap": escolher_cap(perfil),
        "justificativa": JUSTIFICATIVAS.get(sig, "Justificativa não encontrada."),
        "risco_owasp": RISCOS_OWASP.get(sig, "Risco não mapeado."),
    }

for nome, perfil in perfis.items():
    resultado = recomendar(perfil)
    print(f"\n{nome}")
    print(f"  Banco: {resultado['banco']}")
    print(f"  CAP: {resultado['cap']}")
    print(f"  Justificativa: {resultado['justificativa']}")
    print(f"  Risco OWASP: {resultado['risco_owasp']}")