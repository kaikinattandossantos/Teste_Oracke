import os
import base64
import requests
import google.generativeai as genai
import json
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from flask_cors import CORS

# === Carregar variáveis de ambiente ===
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# === Configurar Gemini ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash-latest")

# Lista de extensões de arquivo a serem analisadas.
EXTENSOES_SUPORTADAS = (
    ".py", ".ipynb", ".js", ".ts", ".jsx", ".tsx",
    ".html", ".css", ".scss",
    ".java", ".kt", ".swift",
    ".cs", ".go", ".php", ".rb", ".rs",
    ".c", ".cpp", ".h",
    ".sql", ".md"
)

# === Funções de apoio ===

def obter_dono_e_repositorio(repo_url):
    try:
        parts = repo_url.rstrip("/").split("/")
        owner, repo = parts[-2], parts[-1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        return owner, repo
    except:
        return None, None

def ler_arquivo(owner, repo, path):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code == 200:
        return base64.b64decode(res.json()["content"]).decode("utf-8")
    return None

def coletar_arquivos_recursivamente(owner, repo, path=""):
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        return ""
    conteudo_agregado = ""
    itens = res.json()
    for item in itens:
        if item["type"] == "file":
            if item["name"].endswith(EXTENSOES_SUPORTADAS):
                conteudo = ler_arquivo(owner, repo, item["path"])
                if conteudo:
                    conteudo_agregado += f"\n\n# Arquivo: {item['path']}\n\n{conteudo[:2500]}" # Limite um pouco menor para dar espaço para os dois prompts
        elif item["type"] == "dir":
            conteudo_agregado += coletar_arquivos_recursivamente(owner, repo, item["path"])
    return conteudo_agregado

# === Criar app Flask ===
app = Flask(__name__)
CORS(app)

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.json
    repo_url = data.get("repo_url")
    if not repo_url:
        return jsonify({"error": "A URL do repositório é obrigatória."}), 400

    owner, repo = obter_dono_e_repositorio(repo_url)
    if not owner or not repo:
        return jsonify({"error": "Não foi possível identificar o repositório a partir da URL."}), 400

    conteudo_total = coletar_arquivos_recursivamente(owner, repo)
    if not conteudo_total:
        return jsonify({"error": "Nenhum conteúdo relevante encontrado no repositório."}), 404

    # --- PROMPT 1: Gerar o README ---
    prompt_readme = f"""
    Você é um gerador de documentação para repositórios de código.
    Crie um README.md bem estruturado com base nos arquivos do repositório abaixo:
    {conteudo_total}
    Inclua as seções: Nome do projeto, Descrição, Tecnologias utilizadas, Como executar, Requisitos.
    Gere o conteúdo em Markdown puro.
    """

    # --- AJUSTE: PROMPT 2: Encontrar Bugs e Melhorias ---
    prompt_bugs = f"""
    Você é um revisor de código sênior e especialista em encontrar bugs, más práticas e oportunidades de melhoria.
    Analise o seguinte código do repositório e identifique até 5 problemas ou sugestões importantes.

    Código do repositório:
    {conteudo_total}

    Para cada problema encontrado, forneça uma resposta estruturada em um objeto JSON.
    Sua resposta deve ser APENAS o objeto JSON, sem nenhum texto antes ou depois.
    O formato deve ser:
    {{
      "bugs": [
        {{
          "title": "Um título curto para o problema",
          "filepath": "O caminho/do/arquivo/onde_o_problema_esta.py",
          "severity": "Crítico|Alto|Médio|Baixo",
          "type": "Bug|Melhoria|Segurança",
          "problem": "Uma descrição clara e concisa do problema encontrado.",
          "suggestion": "Uma sugestão de como corrigir ou melhorar o código."
        }}
      ]
    }}
    Se nenhum problema for encontrado, retorne um objeto com uma lista de bugs vazia: {{\"bugs\": []}}.
    """

    try:
        # --- Executa as duas análises em paralelo (ou sequencialmente) ---
        print("🤖 Gerando README...")
        resposta_readme = model.generate_content(prompt_readme)
        readme = resposta_readme.text.strip()
        
        print("🐞 Procurando por bugs e melhorias...")
        resposta_bugs = model.generate_content(prompt_bugs)
        
        # Tenta carregar a resposta JSON da análise de bugs
        try:
            # Limpa a resposta para garantir que seja um JSON válido
            cleaned_json_text = resposta_bugs.text.strip().replace("```json", "").replace("```", "")
            bugs_data = json.loads(cleaned_json_text)
        except json.JSONDecodeError:
            print("⚠️ Aviso: A resposta da análise de bugs não era um JSON válido. Retornando lista vazia.")
            bugs_data = {"bugs": []}

        # --- AJUSTE: Retorna os dois resultados para o frontend ---
        return jsonify({
            "readme": readme,
            "bugs": bugs_data.get("bugs", [])
        })

    except Exception as e:
        return jsonify({"error": f"Erro durante a análise com Gemini: {str(e)}"}), 500


@app.route("/commit", methods=["POST"])
def commit_readme():
    data = request.json
    repo_url = data.get("repo_url")
    readme_content = data.get("readme_content")
    if not repo_url or not readme_content:
        return jsonify({"error": "Dados insuficientes para o commit."}), 400
    owner, repo = obter_dono_e_repositorio(repo_url)
    if not owner or not repo:
        return jsonify({"error": "URL do repositório inválida."}), 400
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/README.md"
    payload = {
        "message": "docs: ✨ README.md gerado por IA",
        "content": base64.b64encode(readme_content.encode("utf-8")).decode("utf-8"),
    }
    get_res = requests.get(url, headers=HEADERS)
    if get_res.status_code == 200:
        payload["sha"] = get_res.json()["sha"]
    elif get_res.status_code != 404:
        return jsonify({"error": f"Erro ao buscar README existente: {get_res.json()}"}), 500
    put_res = requests.put(url, headers=HEADERS, json=payload)
    if put_res.status_code in [200, 201]:
        return jsonify({"success": True, "message": "README.md comitado com sucesso!", "url": put_res.json().get('content', {}).get('html_url')})
    else:
        return jsonify({"error": f"Erro ao fazer commit no GitHub: {put_res.json()}"}), 500

# === Início da aplicação ===
if __name__ == "__main__":
    app.run(debug=True, port=5000)
