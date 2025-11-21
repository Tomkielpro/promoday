from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
from typing import Optional

app = FastAPI(
    title="PromoDay API",
    description="API que busca melhores ofertas no Mercado Livre para o PromoDay",
    version="0.1.0",
)

ML_SITE_ID = "MLB"  # Brasil

# 👉 coloque aqui sua lógica de link de afiliado
def generate_affiliate_link(product_url: str) -> str:
    """
    ATENÇÃO:
    - Entre no Portal do Afiliado do Mercado Livre.
    - Use o 'Gerador de links' para ver como fica o SEU formato de link.
    - Depois adapte esta função.
    Por enquanto, vou só devolver a própria URL do produto.
    """
    return product_url  # TODO: adaptar com seu padrão de link afiliado


def find_best_deal(keyword: str, min_discount_pct: float = 15.0) -> Optional[dict]:
    search_url = f"https://api.mercadolibre.com/sites/{ML_SITE_ID}/search"
    params = {
        "q": keyword,
        "limit": 30,
        "sort": "price_asc",  # barato primeiro, só pra ajudar
    }

    resp = requests.get(search_url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    best_item = None
    best_discount_pct = 0.0

    for item in data.get("results", []):
        price = item.get("price")
        original_price = item.get("original_price") or item.get("base_price") or price

        if not price or not original_price or original_price <= 0:
            continue

        discount_pct = (original_price - price) / original_price * 100.0

        # ignora se não tiver desconto relevante
        if discount_pct < min_discount_pct:
            continue

        if discount_pct > best_discount_pct:
            best_discount_pct = discount_pct
            best_item = {
                "id": item.get("id"),
                "title": item.get("title"),
                "price": price,
                "original_price": original_price,
                "discount_pct": round(discount_pct, 2),
                "permalink": item.get("permalink"),
                "thumbnail": item.get("thumbnail"),
            }

    return best_item


def format_whatsapp_message(item: dict, keyword: str) -> str:
    title = item["title"]
    price = item["price"]
    original_price = item["original_price"]
    discount_pct = item["discount_pct"]
    affiliate_url = generate_affiliate_link(item["permalink"])

    msg = f"""🔥 PROMOÇÃO RELÂMPAGO PROMODAY 🔥

🛍️ {title}

💸 De: ~R$ {original_price:.2f}~
💥 Por: *R$ {price:.2f}*
📉 Desconto: *{discount_pct:.1f}%*

🔗 Link com desconto:
{affiliate_url}

🕒 Oferta encontrada automaticamente para: *{keyword}*
⚠️ Preço e estoque podem mudar a qualquer momento."""
    return msg


@app.get("/promo")
def get_promo(
    keyword: str = Query(..., description="Palavra-chave da busca, ex: smartphone, fone, airfryer"),
    min_discount: float = Query(15.0, description="Desconto mínimo em % para considerar oferta"),
):
    """
    Endpoint chamado pelo Automate (Android):
    - Ex: GET /promo?keyword=smartphone&min_discount=20
    - Retorna JSON com campo 'message' pronto pro WhatsApp.
    """
    try:
        item = find_best_deal(keyword, min_discount_pct=min_discount)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Erro ao buscar ofertas no Mercado Livre", "detail": str(e)},
        )

    if not item:
        return {"message": None, "info": "Nenhuma oferta com desconto mínimo encontrada."}

    message = format_whatsapp_message(item, keyword)
    return {
        "message": message,
        "item": item,
    }


@app.get("/")
def root():
    return {"status": "ok", "service": "PromoDay API"}
