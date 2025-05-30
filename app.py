from openai import OpenAI
from flask import Flask, request, jsonify
import os
import requests

# Configure sua chave do OpenRouter como variável de ambiente: OPENROUTER_API_KEY
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Configurações Zendesk
ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN", "autonotify")  # <--- Altere aqui se precisar
ZENDESK_API_TOKEN = os.getenv("ZENDESK_API_TOKEN")                # Token da API Zendesk
ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL")                        # Email admin da Zendesk

app = Flask(__name__)

def responder_zendesk(ticket_id, resposta):
    """
    Faz um POST para responder ao ticket do Zendesk automaticamente
    """
    if not (ZENDESK_API_TOKEN and ZENDESK_EMAIL and ZENDESK_SUBDOMAIN):
        return False, "Zendesk env vars não configuradas"

    url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets/{ticket_id}.json"
    auth = (f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN)
    payload = {
        "ticket": {
            "comment": {
                "body": resposta,
                "public": True
            }
        }
    }

    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.put(url, json=payload, auth=auth, headers=headers, timeout=15)
        return resp.status_code, resp.json()
    except Exception as e:
        return False, str(e)

@app.route("/claudia", methods=["POST"])
def claudia():
    data = request.get_json(force=True)
    ticket = data.get("ticket", data)  # Pega dict interno ou root

    user_msg = ticket.get("description", "")
    ticket_id = ticket.get("id", "")

    # Também aceita caso venha como "comment": {"body": "..."}
    if not user_msg and "comment" in ticket:
        user_msg = ticket["comment"].get("body", "")

    if not user_msg or not ticket_id:
        return jsonify({"error": "Campos obrigatórios não encontrados (description/comment e id)"}), 400

    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1-0528-qwen3-8b:free",
            messages=[
                {"role": "system", "content": "Você é a Claudia, IA de suporte técnico N1 da StayCloud, treinada com base na central de ajuda da empresa. Resolva dúvidas frequentes de clientes, oriente sobre configurações, apontamentos de DNS, e outros tópicos técnicos, sempre com precisão e empatia. Responda sempre em português."},
                {"role": "user", "content": user_msg}
            ]
        )
        resposta = response.choices[0].message.content.strip()
        status, zendesk_resp = responder_zendesk(ticket_id, resposta)
        return jsonify({
            "status": status,
            "ticket_id": ticket_id,
            "ia_response": resposta,
            "zendesk_response": zendesk_resp
        })
    except Exception as e:
        print("ERRO DETALHADO:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
