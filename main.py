from fastapi import FastAPI, Body
from fastapi.responses import JSONResponse

app = FastAPI(
    title="PromoDay API",
    description="API que recebe dados do PC e entrega mensagens prontas para o WhatsApp (itens em alta + maior desconto).",
    version="3.0"
)

# Armazena último snapshot de resultados por palavra-chave
LATEST_DATA = {}


def generate_affiliate_link(original_url: str) -> str:
    """
    Aqui você adapta depois para o padrão do seu link de afiliado do Mercado Livre.
    Por enquanto, retorna o link normal.
    """
    return original_url


def compute_best_offer(keyword: str, results_json: dict, min_discount_pct: float = 5.0):
    """
    Escolhe o melhor item combinando:
    - desconto (%) quando existir
    - itens em alta (sold_quantity)
    - preço (para não trazer só coisa cara)
    Estratégia:
      1) Tenta achar o melhor score COM desconto >= min_discount_pct
      2) Se não tiver, pega o melhor score geral (tendência + preço)
    """
    results = results_json.get("results", [])
    if not results:
        return None

    best_with_discount = None
    best_with_discount_score = -1e18

    best_fallback = None
    best_fallback_score = -1e18

    for item in results:
        price = item.get("price")
        original_price = item.get("original_price") or item.get("base_price") or price
        if not price:
            continue

        sold_qty = item.get("sold_quantity") or 0

        # calcula desconto real quando possível
        discount_pct = 0.0
        if original_price and original_price > 0 and original_price > price:
            discount_pct = (original_price - price) / original_price * 100.0

        # score principal: queremos desconto + item em alta
        # ajuste de pesos se quiser depois
        score = discount_pct * 2.0 + sold_qty * 0.1 - price * 0.001

        # fallback: mesmo que não tenha desconto, pegamos algo muito vendido e razoável
        fallback_score = sold_qty * 0.1 - price * 0.001

        # atualiza melhor com desconto
        if discount_pct >= min_discount_pct and score > best_with_discount_score:
            best_with_discount_score = score
            best_with_discount = {
                "title": item.get("title"),
                "price": price,
                "original_price": original_price,
                "discount_pct": round(discount_pct, 2),
                "permalink": item.get("permalink"),
                "thumbnail": item.get("thumbnail"),
                "sold_quantity": sold_qty,
            }

        # atualiza melhor geral (fallback)
        if fallback_score > best_fallback_score:
            best_fallback_score = fallback_score
            best_fallback = {
                "title": item.get("title"),
                "price": price,
                "original_price": original_price,
                "discount_pct": round(discount_pct, 2),
                "permalink": item.get("permalink"),
                "thumbnail": item.get("thumbnail"),
                "sold_quantity": sold_qty,
            }

    # prioriza item com desconto REAL, se existir
    if best_with_discount:
        return best_with_discount

    # senão, devolve o item mais “quente” (vendido) + preço ok
    return best_fallback


def format_message(item: dict, keyword: str) -> str:
    link = generate_affiliate_link(item["permalink"])
    discount_pct = item.get("discount_pct", 0.0) or 0.0
    sold_qty = item.get("sold_quantity", 0) or 0

    # se não tiver desconto real, muda o texto levemente
    if discount_pct > 0:
        desconto_txt = f"📉 Desconto: *{discount_pct:.1f}%*"
    else:
        desconto_txt = "📉 Desconto: *em destaque hoje*"

    msg = f"""
🚀 *PROMODAY – OFERTA QUENTE DO DIA!* 🚀

🛍️ {item['title']}

💸 De: ~R$ {item['original_price']:.2f}~
➡️ Por: *R$ {item['price']:.2f}*
{desconto_txt}
🔥 Vendas recentes: *{sold_qty}*+

🔗 Confira a oferta:
{link}

🧠 Categoria / busca monitorada: *{keyword}*
⚠️ Preço e estoque podem mudar a qualquer momento.
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
    Endpoint chamado pelo PC (promoday-fetcher.py)
    keyword: ex. "airfryer"
    results: JSON bruto retornado pelo ML
    """
    LATEST_DATA[keyword] = results
    return {"status": "received", "keyword": keyword}


@app.get("/message")
def get_message(keyword: str, min_discount: float = 5.0):
    """
    Endpoint chamado pelo Automate (Android)
    Exemplo:
      GET /message?keyword=airfryer&min_discount=5
    """
    if keyword not in LATEST_DATA:
        return {"message": None, "info": "Nenhum dado recebido ainda para essa palavra-chave."}

    best = compute_best_offer(keyword, LATEST_DATA[keyword], min_discount_pct=min_discount)

    if not best:
        return {"message": None, "info": "Nenhuma oferta relevante encontrada."}

    msg = format_message(best, keyword)
    return {"message": msg, "item": best}
