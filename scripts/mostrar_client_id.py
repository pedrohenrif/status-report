import json, os, sys
caminho = os.path.join(os.path.dirname(__file__), "..", "credentials", "service-account.json")
with open(caminho) as f:
    dados = json.load(f)
print("Client ID    :", dados.get("client_id"))
print("Client Email :", dados.get("client_email"))
