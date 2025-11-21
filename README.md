# PromoDay API

API em FastAPI que busca automaticamente as melhores ofertas no Mercado Livre
e retorna uma mensagem pronta para envio no WhatsApp via Automate (Android).

## Endpoints

GET /
→ Teste básico da API

GET /promo?keyword=airfryer&min_discount=20
→ Retorna oferta formatada

## Deploy

Feito na Railway com:
web: uvicorn main:app --host 0.0.0.0 --port $PORT
