from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse
import threading

app = FastAPI(
    title="PromoDay API",
    description="API que recebe dados do ML a partir do PC e entrega mensagens prontas para o WhatsApp",
    version="2.0"
)

# Armazena os últimos resultados recebidos do PC
LATEST_DATA = {}

def generate_affiliate_link(original_url: str) -> str:
    """
    Ajuste para o padrão do seu link de afiliado.
    Por enquanto retorna o link normal.
    """
    return original_url  # TODO: adaptar seu padrão de afiliado


def compute_best_offer(keyword: str, results_json: dict, min_discount_pct: float = 10.0):
    best_item = None
    best_disc = 0

    for item in results_json.get("results", []):
        price = item.get("price")
        original_price = item.get("original_price") or price

        if not price or not original_price:
            continue

        discount_pct = (original_price - price) / original_price * 100

        if discount_pct >= min_discount_pct and discount_pct > best_disc:
            best_disc = discount_pct
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
    link = generate_affiliate_link(item["permalink"])

    msg = f"""
🔥 *PROMODAY – OFERTA ENCONTRADA!* 🔥

🛍️ {item['title']}
💸 De: ~R$ {item['original_price']:.2f}~
➡️ Por: *R$ {item['price']:.2f}*
📉 Desconto: *{item['discount_pct']}%*

🔗 Link com desconto:
{link}

🧠 Palavra-chave analisada: *{keyword}*
⚠️ Preço pode mudar a qualquer momento!
    """
    return msg.strip()


@app.get("/")
def root():
    return {"status": "OK", "service": "PromoDay API"}


# ============================================
#  ENDPOINT QUE RECEBE DADOS DO PC
# ============================================

@app.post("/promo_data")
def receive_data(
    keyword: str = Body(...),
    results: dict = Body(...)
):
    """
    O PC envia:
    {
      "keyword": "airfryer",
      "results": { dados completos do ML }
    }
    """
    LATEST_DATA[keyword] = results
    return {"status": "received", "keyword": keyword}


# ============================================
#  ENDPOINT PARA O ANDROID PEGAR A MENSAGEM
# ============================================

@app.get("/message")
def get_message(keyword: str, min_discount: float = 10.0):
    """
    Automate chama:
    GET /message?keyword=airfryer&min_discount=20
    """
    if keyword not in LATEST_DATA:
        return {"message": None, "info": "Nenhum dado enviado pelo PC ainda."}

    best_offer = compute_best_offer(keyword, LATEST_DATA[keyword], min_discount)

    if not best_offer:
        return {"message": None, "info": "Nenhuma oferta com desconto mínimo."}

    message = format_message(best_offer, keyword)
    return {"message": message, "item": best_offer}
