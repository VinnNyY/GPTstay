from openai import OpenAI
from flask import Flask, request, jsonify
import requests
import os

# Configuração do OpenRouter (IA)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

# Configurações Zendesk via variável de ambiente
ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN")  # agora flexível!
ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL")
ZENDESK_API_TOKEN = os.getenv("ZENDESK_API_TOKEN")

app = Flask(__name__)

def responder_zendesk(ticket_id, resposta):
    url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets/{ticket_id}.json"
    auth = (f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN)
    headers = {"Content-Type": "application/json"}
    data = {
        "ticket": {
            "comment": {
                "body": resposta,
                "public": True  # True = público (cliente vê)
            }
        }
    }
    resp = requests.put(url, json=data, auth=auth, headers=headers)
    return resp.status_code, resp.text

@app.route("/claudia", methods=["POST"])
def claudia():
    data = request.get_json(force=True)
    ticket = data.get("ticket", data)  # Pega o dict 'ticket' se houver, senão usa o root

    user_msg = ticket.get("description", "")
    ticket_id = ticket.get("id", "")

    # Zendesk pode enviar o comentário dentro de 'comment'!
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
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
