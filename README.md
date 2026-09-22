# Monitor de vagas de Dados

Projeto em Python que acompanha vagas públicas de Dados (Analista, Cientista, Engenheiro de Dados, BI, Machine Learning etc.) em APIs públicas e gratuitas, e envia avisos para o Discord quando encontra vagas novas ou alteradas.

Fontes utilizadas por padrão:

- [Remotive](https://remotive.com/) — API pública gratuita, filtrada pela categoria "data";
- [RemoteOK](https://remoteok.com/) — API pública gratuita, filtrada pela tag "data".

Opcionalmente, o projeto também pode acompanhar a página de carreira de uma empresa específica no Gupy (`CAREER_URL`). Essa configuração é pessoal e deve ficar apenas no seu `.env` local ou em secrets do GitHub Actions — nunca commitada no código, para não expor publicamente qual empresa você está de olho.

## Como funciona

~~~text
APIs públicas (Remotive, RemoteOK) + carreira opcional (Gupy)
              ↓
Coleta das vagas
              ↓
Filtro de vagas de Dados
              ↓
Comparação com o snapshot anterior
              ↓
Snapshot e histórico
              ↓
Alerta no Discord
~~~

O sistema identifica:

- vaga nova;
- vaga alterada;
- vaga que não apareceu na consulta atual.

“Não encontrada” não significa necessariamente que a vaga foi encerrada. A fonte precisa confirmar isso.

## Quais vagas são consideradas?

O filtro procura títulos e descrições relacionados a:

- Analista de Dados;
- Cientista de Dados;
- Engenheiro ou Engenharia de Dados;
- Governança de Dados;
- Arquitetura de Dados;
- Analytics;
- Business Intelligence e BI;
- ETL;
- Machine Learning;
- MLOps.

As palavras isoladas “data” e “dados” não são suficientes. Isso evita que vagas de outras áreas sejam selecionadas por mencionarem dados de forma genérica.

## Estrutura do projeto

~~~text
src/                         Código principal
  collector.py               Coleta vagas de uma carreira Gupy (opcional)
  remotive_collector.py      Coleta vagas da API pública da Remotive
  remoteok_collector.py      Coleta vagas da API pública da RemoteOK
  diff.py                    Compara o resultado atual com o anterior
  filter_jobs.py             Filtra vagas de Dados
  models.py                  Modelo padronizado de vaga
  normalizer.py              Normaliza os dados
  notifier.py                Formata e envia os alertas para o Discord
  storage.py                 Salva snapshot e histórico

tests/                       Testes automatizados
data/                        Snapshot e histórico (não commitado)
monitor.py                   Comando principal
.env.example                 Exemplo de configuração
.github/workflows/           Execução automática
~~~

## Configuração local

### 1. Abrir o projeto

~~~powershell
cd D:\Projeto\auto_vagas
~~~

### 2. Criar o ambiente virtual

~~~powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
~~~

### 3. Instalar as dependências

~~~powershell
python -m pip install -r requirements.txt
~~~

### 4. Criar o arquivo de configuração

~~~powershell
Copy-Item .env.example .env
~~~

O arquivo .env é local e não deve ser enviado ao GitHub.

## Configurar o Discord

### Criar o webhook

1. No Discord, abra o servidor onde quer receber os avisos.
2. Vá em Configurações do Servidor > Integrações > Webhooks.
3. Clique em Novo Webhook, escolha o canal e copie a URL do webhook.

### Preencher o .env

~~~env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/SEU_WEBHOOK
~~~

Nunca publique a URL do webhook. Se ela for exposta, revogue-a e gere outra.

## Acompanhar uma empresa específica (opcional)

Se quiser acompanhar também a carreira de uma empresa no Gupy, preencha no seu `.env` local (nunca no repositório):

~~~env
CAREER_URL=https://empresa.gupy.io/
# Opcional: se a API pública/credenciada estiver disponível
GUPY_API_URL=https://api.gupy.io/api/v1/jobs
GUPY_CAREER_PAGE_ID=
GUPY_API_TOKEN=
~~~

O token da API pertence à conta da empresa na Gupy e normalmente exige acesso administrativo. Não tente obter um token privado sem autorização.

## Executar localmente

Execução normal:

~~~powershell
python monitor.py
~~~

Na primeira execução, o sistema cria o snapshot inicial e não envia todas as vagas existentes. Depois, ele avisa somente as diferenças.

Para testar o formato enviando as vagas atuais:

~~~powershell
python monitor.py --test-existing
~~~

## Dados salvos

O sistema utiliza:

~~~text
data/vagas_snapshot.json
data/historico.jsonl
~~~

O snapshot guarda o estado mais recente das vagas. O histórico registra eventos como NEW, CHANGED e MISSING. Esses arquivos ficam fora do controle de versão (`.gitignore`) — no GitHub Actions, são preservados entre execuções via cache, nunca commitados no repositório.

Se a internet ou uma fonte falhar, o snapshot anterior é preservado. Isso evita falsos alertas de remoção em massa.

## Testes

~~~powershell
python -m pytest -q tests -p no:cacheprovider
~~~

Os testes verificam o filtro, acentos, palavras-chave, comparação de vagas e normalização das APIs públicas.

## Configurar o GitHub Actions

O arquivo .github/workflows/monitor.yml faz a execução automática.

### Enviar o projeto ao GitHub

Se ainda não existir um repositório Git local:

~~~powershell
git init
git branch -M main
git add .
git commit -m "feat: monitoramento de vagas de dados"
git remote add origin https://github.com/SEU_USUARIO/auto_vagas.git
git push -u origin main
~~~

Se o repositório já estiver conectado:

~~~powershell
git add .
git commit -m "docs: atualizar documentação"
git push
~~~

### Cadastrar os secrets

No GitHub, abra:

~~~text
Settings > Secrets and variables > Actions > New repository secret
~~~

Crie este secret obrigatório:

~~~text
DISCORD_WEBHOOK_URL
~~~

E, apenas se quiser acompanhar uma empresa específica (opcional e mantido fora do código):

~~~text
CAREER_URL
GUPY_API_URL
GUPY_CAREER_PAGE_ID
GUPY_API_TOKEN
~~~

Cole os respectivos valores e salve.

### Executar manualmente

1. Abra a aba Actions.
2. Selecione Monitorar vagas de Dados.
3. Clique em Run workflow.
4. Confirme em Run workflow.

O status Success indica que a execução terminou corretamente.

### Execução automática

O workflow usa:

~~~yaml
cron: "15 11 * * 1"
~~~

Isso significa uma execução por semana, toda segunda-feira às 11:15 UTC, normalmente às 08:15 no horário de Brasília.

O computador e a IDE podem estar desligados. A execução acontece nos servidores do GitHub.

## Mensagem do Discord

Quando os dados estão disponíveis, cada vaga vira um embed com:

- título em destaque, com link para a vaga;
- empresa;
- tipo de contratação;
- localidade;
- modalidade;
- data de publicação, quando disponível;
- cor diferente para vaga nova, alterada ou não encontrada.

Campos que não existem publicamente são ocultados.

## Frequência e limitações

- O monitor consulta as fontes uma vez por semana.
- As APIs públicas podem mudar e exigir ajustes nos coletores.
- Nem todas as vagas exibem data de publicação.
- Uma vaga não encontrada não é automaticamente considerada encerrada.
- O projeto consulta somente informações públicas.
- O projeto não coleta dados de candidatos.
- A primeira execução cria o snapshot sem enviar todas as vagas atuais.

## Solução de problemas

### O Discord não recebeu mensagem

Verifique:

1. se a URL do webhook está correta;
2. se o webhook ainda existe no canal (pode ter sido apagado);
3. se o secret DISCORD_WEBHOOK_URL foi criado no repositório correto;
4. se o workflow terminou com Success.

### O workflow falhou

Abra Actions, selecione a execução com erro e clique na etapa monitor. Os logs mostram a causa.

### O filtro trouxe vagas demais

Revise KEYWORDS no .env. Evite termos genéricos como data e dados sozinhos.

## Resumo

Depois que o workflow estiver com status Success:

- você pode fechar a IDE;
- o computador pode ser desligado;
- o GitHub verifica as vagas semanalmente;
- o Discord avisa quando houver mudanças;
- a aba Actions mostra o histórico das execuções.
