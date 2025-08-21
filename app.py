# app.py — Gerador de Descrições para Produtos (pt-BR)
# Requisitos: streamlit, openai

import os
import json
import time
import streamlit as st
from openai import OpenAI
from json import JSONDecodeError

# ==================== CONFIG BÁSICA ====================
APP_NAME = os.getenv("APP_NAME", "Gerador de Descrições • SuperFrete")
st.set_page_config(page_title=APP_NAME, page_icon="📝", layout="centered")

# ==================== ESTILO (Poppins + #0fae79) ====================
st.markdown(
    "<link href='https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap' rel='stylesheet'>",
    unsafe_allow_html=True
)
st.markdown("""
<style>
:root { --sf-accent:#0fae79; }
html, body, [class*="css"], [data-testid="stAppViewContainer"] * {
  font-family:'Poppins',sans-serif !important;
}
h1,h2,h3,h4,h5,h6 { color:var(--sf-accent)!important; font-weight:700!important; }
.stButton > button {
  background:var(--sf-accent)!important; color:#fff!important; border:none!important;
  border-radius:10px!important; padding:.65rem 1rem!important; font-weight:600!important;
}
.stButton > button:hover { filter:brightness(.92); }
a { color:var(--sf-accent)!important; text-decoration:none; }
a:hover { text-decoration:underline; }
[data-baseweb="input"] input,[data-baseweb="textarea"] textarea, .stTextArea textarea{
  border:1px solid var(--sf-accent)!important; border-radius:8px!important;
}
.block-container{ padding-top:2rem!important; }

/* ==== Chips do MultiSelect (tags) na cor da marca) ==== */
.stMultiSelect [data-baseweb="tag"]{
  background: rgba(15, 174, 121, 0.12) !important; /* fundo verdinho */
  border: 1px solid #0fae79 !important;
  color: #0fae79 !important;
  border-radius: 999px !important; /* pílula mais bonitinha */
  padding: 2px 8px !important;
}

/* texto dentro do chip */
.stMultiSelect [data-baseweb="tag"] span{
  color: #0fae79 !important;
}

/* ícone do “x” para remover */
.stMultiSelect [data-baseweb="tag"] svg{
  fill: #0fae79 !important;
}

/* hover do chip */
.stMultiSelect [data-baseweb="tag"]:hover{
  background: rgba(15, 174, 121, 0.18) !important;
  border-color: #0fae79 !important;
}

/* borda do campo do multiselect */
.stMultiSelect [data-baseweb="select"] > div{
  border-color: #0fae79 !important;
  border-radius: 8px !important;
}

</style>
""", unsafe_allow_html=True)

# Esconde menu/rodapé se embed=?true
try:
    qp = st.query_params
    if qp.get("embed") == ["true"]:
        st.markdown("""
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """, unsafe_allow_html=True)
except Exception:
    pass

# ==================== ENV VARS ====================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY não encontrada. Configure em Render → Settings → Environment.")
    st.stop()

# ==================== OPENAI HELPERS ====================
def call_openai(payload: dict, model: str = "gpt-4o-mini", temperature: float = 0.4):
    """
    Chama OpenAI com schema de saída em JSON estrito.
    Retorna dict decodificado.
    """
    client = OpenAI(api_key=OPENAI_API_KEY)

    system_prompt = (
        "Você é um gerador de descrições de produtos para e-commerce em PT-BR, com foco em SEO e marketplaces. "
        "Seja claro, persuasivo e honesto. Formate a descrição longa em Markdown simples (títulos, listas). "
        "NUNCA invente certificações ou promessas médicas. Use linguagem inclusiva e direta."
    )

    # Schema de saída padronizado
    schema = {
      "titulo_seo": "string",
      "descricao_curta": "string",
      "descricao_longa_md": "string",
      "bullets": ["string", "string"],
      "keywords": ["string", "string"],
      "faq": [{"pergunta": "string", "resposta": "string"}],
      "marketplaces": {
        "mercado_livre": {"titulo": "string", "descricao": "string"},
        "shopee": {"titulo": "string", "descricao": "string", "bullet_points": ["string"]},
        "amazon": {"titulo": "string", "descricao": "string", "bullet_points": ["string"], "search_terms": "string"}
      }
    }

    # Constrói prompt do usuário
    user_prompt = f"""
Gere descrições para produto em PT-BR.

Contexto:
- Nome do produto: {payload.get('nome')}
- Categoria: {payload.get('categoria')}
- Marca: {payload.get('marca') or '—'}
- Características (lista): {', '.join(payload.get('caracteristicas', [])) if payload.get('caracteristicas') else '—'}
- Diferenciais: {', '.join(payload.get('diferenciais', [])) if payload.get('diferenciais') else '—'}
- Público-alvo: {payload.get('publico') or '—'}
- Palavras-chave SEO (sugestivas): {', '.join(payload.get('keywords_usuario', [])) if payload.get('keywords_usuario') else '—'}

TOM & ESTILO:
- Tom: {payload.get('tom')}
- Persona/voz: {payload.get('voz')}
- Regras de clareza: frases curtas, evitar jargão técnico quando possível.
- Políticas: não prometa resultados exagerados, não invente certificações, nada ofensivo.

Saídas desejadas (JSON estrito):
{json.dumps(schema, ensure_ascii=False, indent=2)}

Observações:
- 'descricao_longa_md' deve vir em Markdown com subtítulos (###), listas e chamadas de benefício.
- 'bullets' são itens curtos de especificações/benefícios.
- 'keywords' devem refletir cauda-curta e cauda-longa, sem #.
- Em 'marketplaces', otimize títulos/descrições de forma sucinta.
- Se faltarem dados, assuma o conservador e foque no benefício real.
"""

    # Chamada
    resp = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    content = resp.choices[0].message.content
    try:
        return json.loads(content)
    except JSONDecodeError:
        # fallback básico: retorna texto em campos mínimos
        return {
            "titulo_seo": payload.get("nome", "Título do produto"),
            "descricao_curta": "Descrição curta não pôde ser gerada.",
            "descricao_longa_md": content,
            "bullets": [],
            "keywords": [],
            "faq": [],
            "marketplaces": {"mercado_livre": {}, "shopee": {}, "amazon": {}}
        }

# ==================== SIDEBAR (Config) ====================
with st.sidebar:
    st.markdown("## ⚙️ Configurações")
    tom = st.selectbox("Tom desejado", ["Neutro", "Amigável", "Premium", "Técnico", "Divertido"], index=1)
    voz = st.selectbox("Voz/Persona", ["Marca acolhedora", "Especialista", "Vendedor consultivo", "Minimalista"], index=0)
    marketplaces = st.multiselect("Otimizar para Marketplaces", ["Mercado Livre", "Shopee", "Amazon"], default=["Mercado Livre", "Shopee", "Amazon"])
    temperature = st.slider("Criatividade (temperature)", 0.0, 1.0, 0.4, 0.1)
    st.caption("Dica: valores mais altos geram texto mais criativo; mais baixos, mais direto.")

# ==================== FORM PRINCIPAL ====================
st.markdown(f"## 📝 {APP_NAME}")
st.markdown("Gere rapidamente **título SEO, descrição curta/longa, bullets e versões para marketplaces**.")

with st.form("form"):
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome do produto", placeholder="Ex.: Camiseta básica 100% algodão")
        categoria = st.selectbox("Categoria", ["Moda", "Papelaria", "Acessórios", "Eletrônicos", "Casa & Decoração", "Beleza & Saúde", "Outros"], index=0)
        marca = st.text_input("Marca (opcional)", placeholder="Ex.: SuperFrete Wear")
    with col2:
        publico = st.text_input("Público-alvo (opcional)", placeholder="Ex.: jovens e adultos que buscam conforto")
        keywords_usuario = st.text_input("Palavras-chave SEO (opcionais)", placeholder="Separar por vírgula: camiseta algodão, camiseta preta unissex")

    caracteristicas = st.text_area("Características (uma por linha)", placeholder="Ex.:\n100% algodão\nPreta\nUnissex\nConfortável\nCasual")
    diferenciais = st.text_area("Diferenciais (opcional, uma por linha)", placeholder="Ex.:\nTecido macio e respirável\nModelagem que não torce\nAcabamento reforçado")

    submitted = st.form_submit_button("Gerar descrição")

# ==================== PROCESSAMENTO ====================
def split_lines(s):
    if not s: return []
    return [x.strip(" •-—\t ") for x in s.splitlines() if x.strip()]

if submitted:
    if not nome:
        st.error("Informe pelo menos o **Nome do produto**.")
        st.stop()

    payload = {
        "nome": nome.strip(),
        "categoria": categoria,
        "marca": marca.strip() if marca else None,
        "publico": publico.strip() if publico else None,
        "caracteristicas": split_lines(caracteristicas),
        "diferenciais": split_lines(diferenciais),
        "keywords_usuario": [k.strip() for k in (keywords_usuario or "").split(",") if k.strip()],
        "tom": tom,
        "voz": voz,
        "marketplaces": marketplaces,
    }

    with st.spinner("Gerando descrições com IA..."):
        try:
            result = call_openai(payload, model="gpt-4o-mini", temperature=temperature)
        except Exception as e:
            emsg = str(e).lower()
            if "insufficient_quota" in emsg or ("429" in emsg and "quota" in emsg):
                st.error("Sem créditos na OpenAI agora. Verifique Billing/Usage e a variável OPENAI_API_KEY.")
            elif "rate limit" in emsg or "429" in emsg:
                st.warning("Muitos pedidos. Aguarde alguns segundos e tente novamente.")
            else:
                st.error(f"Erro ao gerar descrição: {e}")
            st.stop()

    st.success("Pronto! Revise e ajuste se necessário.")

    # ==================== SAÍDAS ====================
    titulo = result.get("titulo_seo", "").strip()
    desc_curta = result.get("descricao_curta", "").strip()
    desc_longa_md = result.get("descricao_longa_md", "").strip()
    bullets = result.get("bullets", []) or []
    keywords = result.get("keywords", []) or []
    faq = result.get("faq", []) or []
    mkt = result.get("marketplaces", {}) or {}

    st.markdown("### 🔎 Título SEO")
    st.text_area("Título SEO (copiável)", value=titulo, height=60)

    st.markdown("### ✂️ Descrição curta")
    st.text_area("Descrição curta (copiável)", value=desc_curta, height=100)

    st.markdown("### 📄 Descrição longa (Markdown)")
    st.text_area("Descrição longa (copiável)", value=desc_longa_md, height=280)

    st.markdown("### ✅ Bullet points")
    if bullets:
        st.markdown("\n".join([f"- {b}" for b in bullets]))
    else:
        st.caption("Sem bullets retornados.")

    st.markdown("### 🧩 Palavras-chave sugeridas")
    if keywords:
        st.write(" • ".join(keywords))
    else:
        st.caption("Sem keywords retornadas.")

    st.markdown("### ❓ FAQ sugerida")
    if faq:
        for qa in faq:
            st.write(f"**Q:** {qa.get('pergunta','')}")
            st.write(f"**A:** {qa.get('resposta','')}")
            st.write("")
    else:
        st.caption("Sem FAQ retornada.")

    # ==================== MARKETPLACES ====================
    st.markdown("## 🛒 Versões para Marketplaces")
    ml = mkt.get("mercado_livre", {}) if isinstance(mkt, dict) else {}
    sh = mkt.get("shopee", {}) if isinstance(mkt, dict) else {}
    am = mkt.get("amazon", {}) if isinstance(mkt, dict) else {}

    with st.expander("Mercado Livre"):
        ml_t = ml.get("titulo","").strip()
        ml_d = ml.get("descricao","").strip()
        st.text_area("Título (ML)", value=ml_t, height=60)
        st.text_area("Descrição (ML)", value=ml_d, height=220)

    with st.expander("Shopee"):
        sh_t = sh.get("titulo","").strip()
        sh_d = sh.get("descricao","").strip()
        sh_bullets = sh.get("bullet_points", []) or []
        st.text_area("Título (Shopee)", value=sh_t, height=60)
        st.text_area("Descrição (Shopee)", value=sh_d, height=220)
        if sh_bullets:
            st.text_area("Bullets (Shopee)", value="\n".join([f"- {b}" for b in sh_bullets]), height=140)

    with st.expander("Amazon"):
        am_t = am.get("titulo","").strip()
        am_d = am.get("descricao","").strip()
        am_bullets = am.get("bullet_points", []) or []
        am_terms = am.get("search_terms","").strip()
        st.text_area("Título (Amazon)", value=am_t, height=60)
        st.text_area("Descrição (Amazon)", value=am_d, height=220)
        if am_bullets:
            st.text_area("Bullets (Amazon)", value="\n".join([f"- {b}" for b in am_bullets]), height=140)
        st.text_area("Search Terms / Palavras de busca", value=am_terms, height=80)

    # ==================== DOWNLOADS ====================
    st.markdown("## ⬇️ Exportar")
    md_export = f"""# {titulo or nome}

## Descrição curta
{desc_curta}

## Descrição longa
{desc_longa_md}

## Bullet points
{"".join([f"- {b}\\n" for b in bullets]) or "- —"}

## Palavras-chave
{"; ".join(keywords) or "—"}

## FAQ
{"".join([f"**Q:** {qa.get('pergunta','')}\\n\\n**A:** {qa.get('resposta','')}\\n\\n" for qa in faq]) or "—"}

## Marketplaces
### Mercado Livre
**Título**: {ml.get('titulo','')}
**Descrição**:
{ml.get('descricao','')}

### Shopee
**Título**: {sh.get('titulo','')}
**Descrição**:
{sh.get('descricao','')}
**Bullets**:
{"".join([f"- {b}\\n" for b in sh.get('bullet_points',[])])}

### Amazon
**Título**: {am.get('titulo','')}
**Descrição**:
{am.get('descricao','')}
**Bullets**:
{"".join([f"- {b}\\n" for b in am.get('bullet_points',[])])}
**Search Terms**: {am.get('search_terms','')}
""".strip()

    txt_export = f"""TÍTULO SEO: {titulo}

DESCRIÇÃO CURTA:
{desc_curta}

DESCRIÇÃO LONGA:
{desc_longa_md}

BULLETS:
{chr(10).join(['- ' + b for b in bullets])}

KEYWORDS:
{', '.join(keywords)}

FAQ:
{chr(10).join([f'Q: {qa.get("pergunta","")} | A: {qa.get("resposta","")}' for qa in faq])}

[Mercado Livre]
Título: {ml.get('titulo','')}
Descrição: {ml.get('descricao','')}

[Shopee]
Título: {sh.get('titulo','')}
Descrição: {sh.get('descricao','')}
Bullets:
{chr(10).join(['- ' + b for b in sh.get('bullet_points',[])])}

[Amazon]
Título: {am.get('titulo','')}
Descrição: {am.get('descricao','')}
Bullets:
{chr(10).join(['- ' + b for b in am.get('bullet_points',[])])}
Search Terms: {am.get('search_terms','')}
""".strip()

    st.download_button("Baixar como Markdown (.md)", data=md_export.encode("utf-8"), file_name="descricao_produto.md")
    st.download_button("Baixar como Texto (.txt)", data=txt_export.encode("utf-8"), file_name="descricao_produto.txt")

else:
    st.info("Preencha o formulário acima e clique em **Gerar descrição**.")
    st.caption("Dica: liste 3–6 características claras; a IA organiza e otimiza para SEO/marketplaces.")

