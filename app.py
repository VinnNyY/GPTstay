from openai import OpenAI
from flask import Flask, request, jsonify
import os
import requests

print('DEBUG: OPENROUTER_API_KEY:', os.getenv('OPENROUTER_API_KEY'))
print('DEBUG: ZENDESK_API_TOKEN:', os.getenv('ZENDESK_API_TOKEN'))
print('DEBUG: ZENDESK_EMAIL:', os.getenv('ZENDESK_EMAIL'))
print('DEBUG: ZENDESK_SUBDOMAIN:', os.getenv('ZENDESK_SUBDOMAIN'))

# Configuração dos clientes e variáveis de ambiente
openai_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

ZENDESK_EMAIL = os.getenv("ZENDESK_EMAIL")
ZENDESK_API_TOKEN = os.getenv("ZENDESK_API_TOKEN")
ZENDESK_SUBDOMAIN = os.getenv("ZENDESK_SUBDOMAIN")

app = Flask(__name__)

@app.route("/claudia", methods=["POST"])
def claudia():
    print('\n=== RECEBEU CHAMADA NO /claudia ===')
    try:
        data = request.get_json(force=True)
        print('DEBUG: JSON recebido:', data)
    except Exception as e:
        print('ERRO AO LER JSON:', e)
        return jsonify({"error": "Falha ao ler JSON"}), 400

    # Permitir dois formatos de JSON recebidos do webhook
    if "ticket" in data:
        ticket = data["ticket"]
        ticket_id = ticket.get("id")
        user_msg = (
            ticket.get("description")
            or (ticket.get("comment", {}).get("body") if ticket.get("comment") else "")
        )
    else:
        ticket_id = data.get("ticket_id")
        user_msg = data.get("description") or (
            data.get("comment", {}).get("body") if data.get("comment") else ""
        )

    print(f"DEBUG: ticket_id = {ticket_id}")
    print(f"DEBUG: user_msg = {user_msg}")

    if not user_msg or not ticket_id:
        print("ERRO: JSON deve conter 'ticket_id' e 'description' ou 'comment.body'")
        return jsonify({"error": "JSON deve conter 'ticket_id' e 'description' ou 'comment.body'"}), 400

    try:
        # IA responde
        print("DEBUG: Chamando IA...")
        response = openai_client.chat.completions.create(
            model="deepseek/deepseek-r1-0528-qwen3-8b:free",
            messages=[
                {"role": "system", "content": "Você é a Claudia, IA de suporte técnico N1 da StayCloud, treinada com base na central de ajuda da empresa. Resolva dúvidas frequentes de clientes, oriente sobre configurações, apontamentos de DNS, e outros tópicos técnicos, sempre com precisão e empatia. Responda sempre em português."},
                {"role": "user", "content": user_msg}
            ]
        )
        claudia_response = response.choices[0].message.content.strip()
        print("DEBUG: Resposta da IA:", claudia_response)
    except Exception as e:
        print("ERRO IA:", e)
        return jsonify({"error": f"Erro na IA: {e}"}), 500

    # Enviar resposta para o Zendesk
    try:
        url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets/{ticket_id}.json"
        headers = {
            "Content-Type": "application/json"
        }
        # O email precisa estar no formato: user@dominio/token
        auth = (f"{ZENDESK_EMAIL}/token", ZENDESK_API_TOKEN)
        print("DEBUG: Enviando resposta para Zendesk...")
        print("DEBUG: URL:", url)
        print("DEBUG: Headers:", headers)
        print("DEBUG: Auth:", auth)
        data_json = {
            "ticket": {
                "comment": {
                    "body": claudia_response,
                    "public": True
                }
            }
        }
        print("DEBUG: Corpo do PUT:", data_json)
        r = requests.put(url, headers=headers, json=data_json, auth=auth)
        print("DEBUG: Status code Zendesk:", r.status_code)
        print("DEBUG: Resposta Zendesk:", r.text)
        if r.status_code not in [200, 201]:
            print("ERRO ZENDESK:", r.text)
            return jsonify({"error": f"Erro ao responder no Zendesk: {r.text}"}), 500

    except Exception as e:
        print("ERRO AO ENVIAR PARA O ZENDESK:", e)
        return jsonify({"error": f"Erro ao enviar resposta para o Zendesk: {e}"}), 500

    print("=== FINALIZOU /claudia ===\n")
    return jsonify({"response": claudia_response, "ticket_id": ticket_id})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
