# Railway • File Drop / Download (Flask)

App simples para **distribuir arquivos**: lista arquivos da pasta `files/`, permite **download** e (opcional) **upload com token**.

## ⚙️ Variáveis de ambiente (Railway)
- `UPLOAD_TOKEN` (opcional): se definido, é exigido no `/upload` (via campo do formulário, `?token=` ou header `X-Upload-Token`).
- `INDEX_TOKEN` (opcional): se definido, é exigido para acessar `/` e `/api/list` (via query `?t=` ou header `X-Index-Token`).
- `BLOCK_EMPTY_ZIP` (0/1, padrão 0): se `1`, **bloqueia download** e **rejeita upload** de **ZIP vazio** ou **corrompido**.
- `MAX_CONTENT_LENGTH_MB` (padrão 200): limita o tamanho do upload.
- `SECRET_KEY` (padrão "change-me"): chave do Flask para mensagens flash.

## 🚀 Deploy no Railway
1. Crie um novo projeto e conecte este repositório (ou faça `railway up` pela CLI).
2. Service type: **Python** (buildpack padrão). 
3. Configure as variáveis (mínimo recomendado: `UPLOAD_TOKEN`).
4. Deploy. O serviço sobe no `PORT` que o Railway injeta.

## ▶️ Rodar localmente
```bash
python3 -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export PORT=8080
python app.py
# Acesse http://localhost:8080/
```

## 📂 Pastas
```
/files           # coloque seus arquivos aqui (já tem .gitkeep)
/templates       # HTML (index, upload)
/static          # estáticos (css/js se precisar)
app.py           # app Flask
Procfile         # comando web (Gunicorn)
requirements.txt # dependências
```

## 🔒 Dicas de uso
- Para enviar do seu PC e baixar no VD: suba pelo `/upload` (com `UPLOAD_TOKEN`). No VD, abra a URL do app e faça o download.
- Quer impedir index público? Use `INDEX_TOKEN` e compartilhe a URL com `?t=SEU_TOKEN`.
- Ative `BLOCK_EMPTY_ZIP=1` para garantir **"ZIP não vazio"** antes de distribuir.
- Para verificar por API: `GET /api/list` retorna JSON com nome, tamanho, data e metadados de ZIP.

## 🧪 Smoke test
- Envie um `.zip` com 2 arquivos → lista deve mostrar **"2 itens"** na coluna **ZIP** e o download deve funcionar.
- Envie um `.zip` vazio com `BLOCK_EMPTY_ZIP=1` → upload deve ser **rejeitado** com aviso.
- Baixe um arquivo → o navegador deve baixar e o SHA (12) exibido deve mudar se o arquivo mudar.

Boa distribuição! 🧰


### Nota
- **GET /upload é público** (exibe o formulário). O **POST /upload** exige token quando `UPLOAD_TOKEN` estiver definido.
