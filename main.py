from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse

app = FastAPI(
    title="PromoDay API",
    description="API que recebe dados do PC e entrega mensagens prontas para o WhatsApp",
    version="2.1"
)

LATEST_DATA = {}  # Banco em memória


def generate_affiliate_link(original_url: str) -> str:
    """
    Ajuste para seu link de afiliado.
    """
    return original_url


def compute_best_offer(keyword: str, results_json: dict, min_discount_pct: float = 5.0):
    best_item = None
    best_discount = -9999  # permite pegar qualquer produto com desconto real

    for item in results_json.get("results", []):
        price = item.get("price")
        original_price = item.get("original_price") or item.get("base_price")

        # Se não tem preço original, assume sem desconto
        if not original_price:
            original_price = price

        if not price or not original_price:
            continue

        discount_pct = (original_price - price) / max(original_price, 0.01) * 100

        if discount_pct >= min_discount_pct and discount_pct > best_discount:
            best_discount = discount_pct
            best_item = {
                "title": item.get("title"),
                "price": price,
                "original_price": original_price,
                "discount_pct": round(discount_pct, 2),
                "permalink": item.get("permalink"),
                "thumbnail": item.get("thumbnail")
            }

    return best_item


def format_message(item: dict, keyword: str) -> str:
    link = generate_affiliate_link(item["permalink"])

    msg = f"""
🔥 *PROMODAY – OFERTA QUENTE DETECTADA!* 🔥

🛍️ {item['title']}

💸 De: ~R$ {item['original_price']:.2f}~
➡️ Por: *R$ {item['price']:.2f}*
📉 Economia: *{item['discount_pct']}%*

🔗 Compre com desconto:
{link}

🧠 Monitorando: *{keyword}*
⚠️ Estoque e preços podem mudar rapidamente.
"""
    return msg.strip()


@app.get("/")
def root():
    return {"status": "OK", "service": "PromoDay API"}


@app.post("/promo_data")
def receive_data(
    keyword: str = Body(...),
    results: dict = Body(...)
):
    """
    Recebido do PC (fetcher)
    """
    LATEST_DATA[keyword] = results
    return {"status": "received", "keyword": keyword}


@app.get("/message")
def get_message(keyword: str, min_discount: float = 5.0):
    if keyword not in LATEST_DATA:
        return {"message": None, "info": "Nenhum dado recebido ainda para essa palavra-chave."}

    best = compute_best_offer(keyword, LATEST_DATA[keyword], min_discount)

    if not best:
        return {"message": None, "info": "Nenhuma oferta com desconto suficiente."}

    msg = format_message(best, keyword)
    return {"message": msg, "item": best}
