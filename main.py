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
    best_score = -999999  # quanto maior, melhor
    results = results_json.get("results", [])

    for item in results:
        price = item.get("price")
        original_price = item.get("original_price") or item.get("base_price") or price

        if not price:
            continue

        # desconto artificial baseado em diferença de preço
        discount_pct = 0.0
        if original_price > price:
            discount_pct = (original_price - price) / original_price * 100

        # score: desconto +  lado barato
        score = discount_pct * 10 - price  # peso do desconto + peso do preço baixo

        if score > best_score:
            best_score = score
            best_item = {
                "title": item.get("title"),
                "price": price,
                "original_price": original_price,
                "discount_pct": round(discount_pct, 2),
                "permalink": item.get("permalink"),
                "thumbnail": item.get("thumbnail"),
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

