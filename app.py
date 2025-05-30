import os
from flask import Flask, request, jsonify
import requests
from openai import OpenAI

# Configurações Zendesk
ZENDESK_SUBDOMINIO = "scsr"
ZENDESK_EMAIL = "vinicius@staycloud.com.br/token"
ZENDESK_API_TOKEN = "QaCq6WDWwXonPumqbw3zjysEzH43sBhT7CiiKYCx"

# Configuração OpenRouter
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY") or "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"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

app = Flask(__name__)

def responder_zendesk(ticket_id, resposta):
    url = f"https://{ZENDESK_SUBDOMINIO}.zendesk.com/api/v2/tickets/{ticket_id}.json"
    headers = {"Content-Type": "application/json"}
    data = {
        "ticket": {
            "comment": {
                "body": resposta,
                "public": True  # True = Resposta pública (cliente vê), False = interna
            }
        }
    }
    resp = requests.put(url, json=data, auth=(ZENDESK_EMAIL, ZENDESK_API_TOKEN))
    return resp.status_code, resp.text

@app.route("/claudia", methods=["POST"])
def claudia():
    data = request.get_json(force=True)
    # Ajuste conforme seu JSON do Zendesk!
    ticket_id = data.get("ticket_id") or data.get("id")  # ou ajuste a chave conforme chega
    mensagem = data.get("description") or data.get("message")

    if not ticket_id or not mensagem:
        return jsonify({"error": "ticket_id e description/message são obrigatórios!"}), 400

    # IA responde (exemplo com DeepSeek, pode ajustar modelo)
    response = client.chat.completions.create(
        model="deepseek/deepseek-r1-0528-qwen3-8b:free",
        messages=[
            {"role": "system", "content": "Você é a Claudia, IA de suporte técnico N1 da StayCloud, treinada com base na central de ajuda da empresa. Resolva dúvidas frequentes de clientes, oriente sobre configurações, apontamentos de DNS, e outros tópicos técnicos, sempre com precisão e empatia. Responda sempre em português."},
            {"role": "user", "content": mensagem}
        ]
    )
    resposta_ia = response.choices[0].message.content.strip()

    # Envia resposta para o Zendesk
    status, resp = responder_zendesk(ticket_id, resposta_ia)

    return jsonify({
        "status": status,
        "ia_response": resposta_ia,
        "zendesk_response": resp
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
