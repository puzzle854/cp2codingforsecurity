# Auditoria de Segurança — OWASP Top 10:2025

- **Demonstração 1 — SQL Injection (A05:2025 – Injeção):** 
  **Impacto:** Permite manipular consultas SQL, acessar registros indevidos e, potencialmente, alterar ou excluir dados. 
  **Correção:** Utilizar consultas parametrizadas (*prepared statements*), validar entradas e nunca concatenar dados do usuário diretamente no comando SQL.

- **Demonstração 2 — Cross-Site Scripting (XSS) (A05:2025 – Injeção):** 
  **Impacto:** Permite que o conteúdo fornecido pelo usuário seja interpretado como código no navegador, executando scripts maliciosos no contexto da aplicação. 
  **Correção:** Escapar ou codificar a saída HTML, validar entradas e evitar a inserção de conteúdo não confiável diretamente nas páginas.

- **Demonstração 3 — DELETE sem autenticação/autorização adequada (A01:2025 – Controle de Acesso Quebrado):** 
  **Impacto:** Permite que usuários não autorizados executem operações destrutivas, como a exclusão de registros. 
  **Correção:** Exigir autenticação e aplicar autorização baseada em função ou permissão em todas as operações sensíveis.

- **Demonstração 4 — Vazamento de erro/traceback (A02:2025 – Configuração Insegura):** 
  **Impacto:** Expõe detalhes internos da aplicação (bibliotecas, caminhos, consultas ou estrutura do sistema) que podem facilitar novos ataques. 
  **Correção:** Desabilitar o modo de depuração (*debug*) em produção, retornar mensagens de erro genéricas ao cliente e registrar os detalhes técnicos exclusivamente nos logs internos do servidor.

- **Demonstração 5 — Campo `senha` retornado pela API (A01:2025 – Controle de Acesso Quebrado):** 
  **Impacto:** Expõe informações sensíveis a clientes que não deveriam recebê-las, aumentando o risco de comprometimento de contas. 
  **Correção:** Aplicar projeção de campos, retornando apenas os dados estritamente necessários e filtrando ativamente senhas ou credenciais.

- **Demonstração 6 — Headers de segurança ausentes (A02:2025 – Configuração Insegura):** 
  **Impacto:** Reduz as proteções nativas fornecidas pelo navegador, facilitando ataques como XSS, *clickjacking* e interpretação insegura de conteúdo (*MIME sniffing*). 
  **Correção:** Configurar cabeçalhos de segurança adequados (ex: `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`) e demais diretivas protetivas.

- **Demonstração 7 — Credencial fixa no código-fonte (A07:2025 – Falhas de Autenticação):** 
  **Impacto:** Uma credencial exposta no código (*hard-coded*) pode ser recuperada por quem obtiver acesso ao repositório e reutilizada para invadir recursos protegidos. 
  **Correção:** Remover credenciais do código, passar a utilizar variáveis de ambiente ou gerenciadores de segredos e rotacionar as chaves já comprometidas.

- **Demonstração 8 — Ausência de trilha de auditoria e registros (A09:2025 – Falhas de Registro e Monitoramento):** 
  **Impacto:** Dificulta a detecção de ações suspeitas, a investigação de incidentes e a identificação de quem executou operações críticas. 
  **Correção:** Registrar eventos relevantes de autenticação, autorização e alteração de dados, proteger os logs contra manipulação e implementar sistemas de monitoramento com alertas.