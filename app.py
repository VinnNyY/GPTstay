from openai import OpenAI
from flask import Flask, request, jsonify
import os

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")  # Certifique-se que a variável está setada corretamente no Railway!
)

app = Flask(__name__)

@app.route("/claudia", methods=["POST"])
def claudia():
    data = request.get_json(force=True)
    # Permite receber 'description' tanto na raiz quanto dentro de 'ticket'
    user_msg = ""
    ticket_id = ""
    if "ticket" in data:
        user_msg = data["ticket"].get("description", "")
        ticket_id = data["ticket"].get("id", "")
    else:
        user_msg = data.get("description", "")
        ticket_id = data.get("ticket_id", "")

    if not user_msg:
        return jsonify({"error": "Campo 'description' é obrigatório"}), 400

    try:
        response = client.chat.completions.create(
            model="deepseek/deepseek-r1-0528-qwen3-8b:free",
            messages=[
                {"role": "system", "content": "Você é a Claudia, IA de suporte técnico N1 da StayCloud, treinada com base na central de ajuda da empresa. Resolva dúvidas frequentes de clientes, oriente sobre configurações, apontamentos de DNS, e outros tópicos técnicos, sempre com precisão e empatia. Responda sempre em português."},
                {"role": "user", "content": user_msg}
            ]
        )
        resposta = response.choices[0].message.content.strip()
        return jsonify({"response": resposta, "ticket_id": ticket_id})
    except Exception as e:
        print("ERRO DETALHADO:", e)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
