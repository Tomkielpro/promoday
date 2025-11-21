from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests

app = FastAPI(
    title="PromoDay API",
    description="API que busca ofertas no Mercado Livre para o PromoDay",
    version="1.1"
)

ML_SITE = "MLB"  # Brasil


def generate_affiliate_link(original_url: str) -> str:
    """
    Ajuste para o padrão do seu link de afiliado.
    Por enquanto retorna o link normal.
    """
    return original_url  # TODO: adaptar seu padrão de afiliado


def find_best_offer(keyword: str, min_discount_pct: float):
    url = f"https://api.mercadolibre.com/sites/{ML_SITE}/search"
    params = {
        "q": keyword,
        "limit": 30,
        "sort": "price_asc"
    }

    # NECESSÁRIO PARA EVITAR ERRO 403 (Mercado Livre bloqueia sem User-Agent)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json",
    }

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        raise Exception(f"Erro ao buscar dados do ML: {e}")

    data = response.json()
    best_item = None
    best_discount = 0

    for item in data.get("results", []):
        price = item.get("price")
        original_price = item.get("original_price") or price

        if not price or not original_price:
            continue

        discount_pct = (original_price - price) / original_price * 100

        if discount_pct >= min_discount_pct and discount_pct > best_discount:
            best_discount = discount_pct
            best_item = {
                "title": item.get("title"),
                "price": price,
                "original_price": original_price,
                "discount_pct": round(discount_pct, 2),
                "thumbnail": item.get("thumbnail"),
                "permalink": item.get("permalink")
            }

    return best_item


def format_message(item: dict, keyword: str) -> str:
    affiliate = generate_affiliate_link(item["permalink"])

    msg = f"""
🔥 *PROMODAY – OFERTA ENCONTRADA!* 🔥

🛍️ {item['title']}
💸 De: ~R$ {item['original_price']:.2f}~
➡️ Por: *R$ {item['price']:.2f}*
📉 Desconto: *{item['discount_pct']}%*

🔗 Link com desconto:
{affiliate}

🧠 Palavra-chave analisada: *{keyword}*
⚠️ Preço pode mudar a qualquer momento!
    """

    return msg.strip()


@app.get("/")
def root():
    return {"status": "OK", "service": "PromoDay API"}


@app.get("/promo")
def promo(
    keyword: str = Query(..., description="Ex: fone, airfryer, cafeteira"),
    min_discount: float = Query(10.0, description="Desconto mínimo em %")
):
    try:
        offer = find_best_offer(keyword, min_discount)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

    if not offer:
        return {"message": None, "info": "Sem ofertas relevantes agora."}

    message = format_message(offer, keyword)

    return {
        "message": message,
        "item": offer
    }
