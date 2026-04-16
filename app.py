import streamlit as st
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd
import requests
from ddgs import DDGS
from newspaper import Article
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

# -----------------------------
# Sources presse française
# -----------------------------
FRENCH_NEWS_DOMAINS = [

# centre / généralistes
"lemonde.fr",
"francetvinfo.fr",
"ouest-france.fr",

# centre droit
"lefigaro.fr",
"lesechos.fr",

# gauche
"liberation.fr",
"nouvelobs.com",

# droite
"valeursactuelles.com",

# droite radicale / extrême droite
"fdesouche.com",
"ripostelaique.com",
"boulevardvoltaire.fr",
"egaliteetreconciliation.fr",
"reseauinternational.net"

# international
"france24.com",
"rfi.fr"
]

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

try:
    from streamlit_mic_recorder import speech_to_text
    MICRO_AVAILABLE = True
except Exception:
    speech_to_text = None
    MICRO_AVAILABLE = False


# -----------------------------
# Configuration page
# -----------------------------
st.set_page_config(
    page_title="DOXA Detector",
    page_icon="🧠",
    layout="wide",
)

st.image("banner2.png", use_container_width=True)
st.caption("Laboratoire de calibration cognitive — M = (G + N) − D")
st.markdown("---")

st.markdown("""
<style>
div[data-testid="stProgressBar"] > div > div > div > div {
    height: 20px;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# Mga teksto sa Filipino
# -----------------------------
T = {
    "settings": "Mga Setting",
    "load_example": "I-load ang Halimbawa",
    "show_method": "Ipakita ang Paraan",
    "hard_fact_score_scale": "Saklaw ng Hard Fact Score",
    "scale_0_5": "napakahina",
    "scale_6_9": "duda-duda",
    "scale_10_14": "posible ngunit kailangang beripikahin",
    "scale_15_20": "istruktural na matibay",
    "topic_section": "Pagsusuri ng maraming artikulo ayon sa paksa",
    "topic": "Paksang susuriin",
    "topic_placeholder": "halimbawa: artificial intelligence",
    "analyze_topic": "📰 Suriin ang 10 artikulo tungkol sa paksang ito",
    "searching": "Naghahanap at sinusuri ang mga artikulo...",
    "articles_analyzed": "mga artikulong nasuri.",
    "analyzed_articles": "Mga Artikulong Nasuri",
    "avg_hard_fact": "Average na Hard Fact",
    "avg_classic_score": "Average na klasikong score",
    "topic_doxa_index": "Indeks ng doxa ng paksa",
    "high": "Mataas",
    "medium": "Katamtaman",
    "low": "Mababa",
    "credibility_score_dispersion": "Pagkakaiba ng mga score ng kredibilidad",
    "article_label": "Artikulo",
    "no_exploitable_articles_found": "Walang artikulong mapakinabangan para sa paksang ito.",
    "enter_keyword_first": "Maglagay muna ng keyword o paksa.",
    "url": "Suriin ang artikulo mula sa URL",
    "load_url": "🌐 I-load ang artikulo mula sa URL",
    "article_loaded_from_url": "Na-load ang artikulo mula sa URL.",
    "unable_to_retrieve_text": "Hindi makuha ang teksto mula sa URL na ito.",
    "paste_url_first": "Ilagay muna ang URL.",
    "paste": "I-paste dito ang artikulo o teksto",
    "analyze": "🔍 Suriin ang artikulo",
    "manual_paste": "manwal na pag-paste",
    "loaded_url_source": "artikulong na-load mula sa URL",
    "text_source": "Pinagmulan ng teksto",
    "paste_text_or_load_url": "Mag-paste ng teksto o mag-load ng URL, pagkatapos ay i-click ang « 🔍 Suriin ang artikulo ».",
    "classic_score": "Klasikong score",
    "improved_score": "Pinahusay na score",
    "hard_fact_score": "Hard Fact Score",
    "help_classic_score": "M = (G + N) − D",
    "help_improved_score": "Idinagdag ang V at parusang R",
    "help_hard_fact_score": "Mas mahigpit na pagsusuri ng mga pahayag at mga sanggunian",
    "credibility_gauge": "Antas ng Kredibilidad",
    "fragile": "Mahina",
    "fragile_message": "Ang teksto ay may seryosong kahinaan sa istruktura o sa mga katotohanan.",
    "doubtful": "Duda-duda",
    "doubtful_message": "May ilang kapani-paniwalang elemento ngunit nananatiling hindi tiyak.",
    "plausible": "Posible",
    "plausible_message": "Mukhang makatotohanan ang teksto ngunit kailangan pa ring beripikahin.",
    "robust": "Matibay",
    "robust_message": "Ang teksto ay may matibay na batayan sa istruktura at mga katotohanan.",
    "score": "Score",
    "verdict": "Hatol",
    "summary": "Buod ng pagsusuri",
    "strengths_detected": "Mga lakas na natukoy",
    "few_strong_signals": "Kaunti lamang ang matibay na senyales.",
    "weaknesses_detected": "Mga kahinaang natukoy",
    "no_major_weakness": "Walang malaking kahinaan na natukoy ng heuristic.",
    "presence_of_source_markers": "May mga palatandaan ng mga sanggunian o datos",
    "verifiability_clues": "May mga palatandaan ng beripikasyon: link, numero, petsa o porsiyento",
    "text_contains_nuances": "May mga nuance, limitasyon o kontra-punto ang teksto",
    "text_evokes_robust_sources": "Binabanggit ng teksto ang mga mapagkakatiwalaang institusyonal na sanggunian",
    "some_claims_verifiable": "Ang ilang pahayag ay maaaring beripikahin",
    "overly_assertive_language": "Sobrang tiyak o absolutistang wika",
    "notable_emotional_sensational_charge": "May kapansin-pansing emosyonal o sensasyonal na tono",
    "almost_total_absence_of_verifiable_elements": "Halos walang elementong maaaring beripikahin",
    "text_too_short": "Masyadong maikli ang teksto para sa matibay na pahayag",
    "multiple_claims_very_fragile": "Maraming pangunahing pahayag ang napakahina",
    "hard_fact_checking_by_claim": "Fact-checking ng mga pahayag",
    "claim": "Pahayag",
    "status": "Estado",
    "verifiability": "Beripikabilidad",
    "risk": "Panganib",
    "number": "Numero",
    "date": "Petsa",
    "named_entity": "Pangalan",
    "attributed_source": "Tinukoy na sanggunian",
    "yes": "Oo",
    "no": "Hindi",
    "to_verify": "Dapat beripikahin",
    "rather_verifiable": "Medyo beripikable",
    "very_fragile": "Napakahina",
    "low_credibility": "Mababang kredibilidad",
    "prudent_credibility": "Maingat na kredibilidad",
    "rather_credible": "Medyo kapani-paniwala",
    "strong_credibility": "Malakas na kredibilidad",
    "paste_longer_text": "Mag-paste ng mas mahabang teksto upang makakuha ng mas detalyadong pagsusuri.",
    "llm_analysis": "Pagsusuri ng mécroyance para sa mga sistema",
    "llm_intro": "Ginagamit ng seksyong ito ang mga modelong hango sa teorya upang suriin ang posisyong kognitibo ng isang sistema.",
    "overconfidence": "Sobrang kumpiyansa",
    "calibration": "Relatibong kalibrasyon",
    "revisability": "Revisability (R)",
    "cognitive_closure": "Kognitibong pagsasara",
    "interpretation": "Interpretasyon",
    "llm_metrics": "Mga derived na metric",
    "zone_closure": "Zone ng kognitibong pagsasara: mas mataas ang katiyakan kaysa sa pagkaunawa.",
    "zone_stability": "Zone ng nababagong katatagan.",
    "zone_lucidity": "Zone ng lumalaking kalinawan.",
    "zone_rare": "Bihirang zone ng mataas na integrasyon ng kognisyon.",
    "zone_pansapience": "Hipotetikong pan-sapience.",
    "zone_asymptote": "Perpektong asymptote ng kaalaman.",
    "out_of_spectrum": "Halaga na lampas sa teoretikal na saklaw.",
    "external_corroboration_module": "🔎 Module ng panlabas na corroboration",
    "external_corroboration_caption": "Naghahanap ng mga panlabas na sanggunian upang kumpirmahin o kontrahin ang mga pangunahing pahayag.",
    "corroboration_in_progress": "Naghahanap ng corroboration...",
    "generated_query": "Nabuo na query",
    "no_strong_sources_found": "Walang sapat na matibay na sanggunian.",
    "no_corroboration_found": "Walang natagpuang corroboration.",
    "corroborated": "Nakumpirma",
    "mixed": "Halo-halo",
    "not_corroborated": "Hindi nakumpirma",
    "insufficiently_documented": "Hindi sapat ang dokumentasyon",
    "corroboration_verdict": "Hatol ng corroboration",
    "match_score": "Score ng pagtutugma",
    "contradiction_signal": "Signal ng kontradiksyon",
    "detected": "Natukoy",
    "not_detected": "Hindi natukoy",
    "ai_module": "Module ng AI",
    "ai_module_caption": "Muling sinusuri ng AI ang heuristikong pagsusuri.",
    "generate_ai_analysis": "✨ Bumuo ng AI analysis",
    "ai_unavailable": "Hindi available ang AI module.",
    "ai_analysis_result": "Resulta ng AI analysis",
    "method": "Paraan",
    "original_formula": "Orihinal na pormula",
    "articulated_knowledge_density": "G: densidad ng artikuladong kaalaman.",
    "integration": "N: integrasyon ng konteksto at nuance.",
    "assertive_rigidity": "D: matigas na katiyakan.",
    "disclaimer": "Ang app na ito ay hindi kapalit ng mamamahayag o mananaliksik.",
}

# -----------------------------
# Triangle cognitif 3D
# -----------------------------
def plot_cognitive_triangle_3d(G: float, N: float, D: float):
    G_pt = [10, 0, 0]
    N_pt = [0, 10, 0]
    D_pt = [0, 0, 10]
    P = [G, N, D]

    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection="3d")

    verts = [[G_pt, N_pt, D_pt]]
    tri = Poly3DCollection(verts, alpha=0.18, edgecolor="black", linewidths=1.5)
    ax.add_collection3d(tri)

    ax.plot([G_pt[0], N_pt[0]], [G_pt[1], N_pt[1]], [G_pt[2], N_pt[2]], linewidth=2)
    ax.plot([N_pt[0], D_pt[0]], [N_pt[1], D_pt[1]], [N_pt[2], D_pt[2]], linewidth=2)
    ax.plot([D_pt[0], G_pt[0]], [D_pt[1], G_pt[1]], [D_pt[2], G_pt[2]], linewidth=2)

    ax.scatter(*G_pt, s=80)
    ax.scatter(*N_pt, s=80)
    ax.scatter(*D_pt, s=80)

    ax.text(G_pt[0] + 0.3, G_pt[1], G_pt[2], "G", fontsize=12, weight="bold")
    ax.text(N_pt[0], N_pt[1] + 0.3, N_pt[2], "N", fontsize=12, weight="bold")
    ax.text(D_pt[0], D_pt[1], D_pt[2] + 0.3, "D", fontsize=12, weight="bold")

    ax.scatter(*P, s=140, marker="o")
    ax.text(P[0] + 0.2, P[1] + 0.2, P[2] + 0.2, "Texte", fontsize=11, weight="bold")

    ax.plot([0, G], [0, 0], [0, 0], linestyle="--", linewidth=1)
    ax.plot([0, 0], [0, N], [0, 0], linestyle="--", linewidth=1)
    ax.plot([0, 0], [0, 0], [0, D], linestyle="--", linewidth=1)
    ax.plot([0, G], [0, N], [0, D], linestyle=":", linewidth=1.5)

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_zlim(0, 10)

    ax.set_xlabel("G — gnōsis")
    ax.set_ylabel("N — nous")
    ax.set_zlabel("D — doxa")
    ax.set_title("Triangle cognitif 3D")
    ax.view_init(elev=24, azim=35)

    return fig


# -----------------------------
# OpenAI client
# -----------------------------
def get_openai_client() -> Optional["OpenAI"]:
    if OpenAI is None:
        return None

    api_key = st.secrets.get("OPENAI_API_KEY")
    if not api_key:
        return None

    try:
        return OpenAI(api_key=api_key)
    except Exception:
        return None


client = get_openai_client()


# -----------------------------
# Header
# -----------------------------
st.title("DOXA Detector")

with st.container(border=True):
    st.subheader("Analyser la fiabilité d’un texte")
    st.write(
        "DOXA Detector aide à comprendre si un texte repose sur des faits solides "
        "ou sur une rhétorique persuasive."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 1️⃣ Coller un texte")
        st.write("Copiez un article ou un extrait dans la zone d’analyse.")

    with col2:
        st.markdown("### 2️⃣ Analyser")
        st.write("L’application examine les sources, les affirmations et la nuance.")

    with col3:
        st.markdown("### 3️⃣ Comprendre")
        st.write("Obtenez un score de crédibilité et une analyse des affirmations.")

    st.caption(
        "Cet outil n’affirme pas si un texte est vrai ou faux : "
        "il aide simplement à mieux comprendre la solidité de l’information."
    )


# -----------------------------
# Modèle de cognition
# -----------------------------
class Cognition:
    def __init__(self, gnosis: float, nous: float, doxa: float):
        self.G = self.clamp(gnosis)
        self.N = self.clamp(nous)
        self.D = self.clamp(doxa)
        self.M = self.compute_mecroyance()

    @staticmethod
    def clamp(value: float, min_val: float = 0.0, max_val: float = 10.0) -> float:
        return max(min_val, min(max_val, value))

    def compute_mecroyance(self) -> float:
        return (self.G + self.N) - self.D

    def interpret(self) -> str:
        m = self.M
        if m < 0:
            return T["zone_closure"]
        if 0 <= m <= 10:
            return T["zone_stability"]
        if 10 < m <= 17:
            return T["zone_lucidity"]
        if 17 < m < 19:
            return T["zone_rare"]
        if 19 <= m < 20:
            return T["zone_pansapience"]
        if m == 20:
            return T["zone_asymptote"]
        return T["out_of_spectrum"]


# -----------------------------
# Exemple
# -----------------------------
SAMPLE_ARTICLE = (
    "L'intelligence artificielle va remplacer 80% des emplois d'ici 2030, selon une étude choc publiée hier par le cabinet GlobalTech. "
    "Le rapport de 45 pages affirme que les secteurs de la finance et de la santé seront les plus touchés. "
    "\"C'est une révolution sans précédent\", déclare Jean Dupont, expert en robotique. "
    "Cependant, certains économistes comme Marie Curie restent prudents : \"Il faut nuancer ces chiffres, car de nouveaux métiers vont apparaître.\" "
    "L'étude précise que 12 millions de postes pourraient être créés en Europe. "
    "Malgré cela, l'inquiétude grandit chez les salariés qui craignent pour leur avenir. "
    "Il est absolument certain que nous allons vers une crise sociale majeure si rien n'est fait immédiatement."
)


# -----------------------------
# Helpers
# -----------------------------
def clamp(n: float, minn: float, maxn: float) -> float:
    return max(min(maxn, n), minn)


@st.cache_data(show_spinner=False, ttl=3600)
def extract_article_from_url(url: str) -> str:
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception:
        return ""


@st.cache_data(show_spinner=False, ttl=1800)
def search_articles_by_keyword(keyword: str, max_results: int = 10) -> List[Dict]:
    articles = []
    seen_urls = set()

    api_key = st.secrets.get("NEWS_API_KEY")
    from_date_iso = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

    # -----------------------------
    # 1) Priorité : NewsAPI
    # -----------------------------
    if api_key:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": keyword,
            "language": "fr",
            "sortBy": "publishedAt",
            "pageSize": max_results * 3,
            "apiKey": api_key,
        }

        try:
            response = requests.get(url, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                for art in data.get("articles", []):
                    article_url = art.get("url")
                    title = art.get("title", "Sans titre")
                    source = art.get("source", {}).get("name", "Source inconnue")
                    published_at = art.get("publishedAt", "")

                    if not article_url or article_url in seen_urls:
                        continue

                    seen_urls.add(article_url)

                    articles.append({
                        "title": title,
                        "url": article_url,
                        "source": source,
                        "published_at": published_at,
                    })

                    if len(articles) >= max_results:
                        return articles

        except Exception as e:
            st.warning(f"Erreur NewsAPI : {e}")

    # -----------------------------
    # 2) Fallback DDGS
    # -----------------------------
    try:
        with DDGS() as ddgs:
            query = f"{keyword} actualité France"
            results = list(ddgs.text(query, max_results=max_results * 5))

            for r in results:
                url = r.get("href", "")
                title = r.get("title", "Sans titre")

                if not url or url in seen_urls:
                    continue

                seen_urls.add(url)

                articles.append({
                    "title": title,
                    "url": url,
                    "source": url.split("/")[2] if "://" in url else url,
                    "published_at": "",
                })

                if len(articles) >= max_results:
                    break

    except Exception as e:
        st.warning(f"Erreur DDGS : {e}")

    return articles


    api_key = st.secrets.get("NEWS_API_KEY")

    if api_key:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": keyword,
            "language": "fr",
            "sortBy": "relevancy",
            "pageSize": max_results * 2,
            "apiKey": api_key,
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                for art in data.get("articles", []):
                    article_url = art.get("url")
                    title = art.get("title")
                    source = art.get("source", {}).get("name", "Source inconnue")

                    if not article_url or article_url in seen_urls:
                        continue

                    seen_urls.add(article_url)
                    articles.append({
                        "title": title,
                        "url": article_url,
                        "source": source,
                    })

                    if len(articles) >= max_results:
                        return articles
            else:
                st.warning(f"Erreur HTTP NewsAPI : {response.status_code}")
        except Exception as e:
            st.warning(f"Erreur NewsAPI : {e}")

    trusted_domains = [
        "lemonde.fr", "lefigaro.fr", "liberation.fr", "francetvinfo.fr",
        "lexpress.fr", "lepoint.fr", "nouvelobs.com", "la-croix.com",
        "lesechos.fr", "latribune.fr", "mediapart.fr", "arte.tv",
        "bbc.com", "reuters.com", "apnews.com", "nytimes.com",
        "theguardian.com", "bloomberg.com", "dw.com", "aljazeera.com",
        "nature.com", "science.org", "who.int", "un.org", "worldbank.org",
        "elpais.com", "elmundo.es", "corriere.it", "spiegel.de", "zeit.de",
    ]

    results: List[Dict] = []

    try:
        with DDGS() as ddgs:
            query = f"{keyword} actualité article analyse étude rapport"
            ddg_results = list(ddgs.text(query, max_results=max_results * 5))

            for r in ddg_results:
                url = r.get("href", "")
                title = r.get("title", "Sans titre")

                if not url or url in seen_urls:
                    continue

                if not any(domain in url for domain in trusted_domains):
                    continue

                seen_urls.add(url)
                results.append(
                    {
                        "title": title,
                        "url": url,
                        "source": url.split("/")[2] if "://" in url else url,
                    }
                )

                if len(results) >= max_results:
                    break

    except Exception as e:
        st.warning(f"Erreur de recherche : {e}")

    return results


@dataclass
class Claim:
    text: str
    has_number: bool
    has_date: bool
    has_named_entity: bool
    has_source_cue: bool
    absolutism: int
    emotional_charge: int
    verifiability: float
    risk: float
    status: str


SOURCE_CUES = [
    "selon", "affirme", "déclare", "rapport", "étude", "expert",
    "source", "dit", "écrit", "publié", "annonce", "confirme", "révèle",
]

ABSOLUTIST_WORDS = [
    "toujours", "jamais", "absolument", "certain", "certaine",
    "prouvé", "prouvée", "incontestable", "tous", "aucun",
]

EMOTIONAL_WORDS = [
    "choc", "incroyable", "terrible", "peur", "menace",
    "scandale", "révolution", "urgent", "catastrophe", "crise",
]

NUANCE_MARKERS = [
    "cependant", "pourtant", "néanmoins", "toutefois", "mais",
    "nuancer", "prudence", "possible", "peut-être", "semble",
]


def analyze_claim(sentence: str) -> Claim:
    has_number = bool(re.search(r"\d+", sentence))
    has_date = bool(
        re.search(
            r"\d{4}|janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre",
            sentence,
            re.I,
        )
    )
    has_named_entity = bool(re.search(r"[A-Z][a-z]+ [A-Z][a-z]+|[A-Z]{2,}", sentence))
    has_source_cue = any(cue in sentence.lower() for cue in SOURCE_CUES)

    absolutism = sum(1 for word in ABSOLUTIST_WORDS if word in sentence.lower())
    emotional_charge = sum(1 for word in EMOTIONAL_WORDS if word in sentence.lower())

    v_score = clamp((has_number * 5) + (has_date * 5) + (has_named_entity * 5) + (has_source_cue * 5), 0, 20)
    r_score = clamp((absolutism * 7) + (emotional_charge * 7), 0, 20)

    if v_score < 5:
        status = T["very_fragile"]
    elif v_score < 12:
        status = T["to_verify"]
    else:
        status = T["rather_verifiable"]

    return Claim(
        text=sentence,
        has_number=has_number,
        has_date=has_date,
        has_named_entity=has_named_entity,
        has_source_cue=has_source_cue,
        absolutism=absolutism,
        emotional_charge=emotional_charge,
        verifiability=v_score,
        risk=r_score,
        status=status,
    )


def analyze_article(text: str) -> Dict:
    words = text.split()
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 10]
    article_length = len(words)

    source_markers = len(re.findall(r"|".join(re.escape(c) for c in SOURCE_CUES), text.lower()))
    citation_like = len(re.findall(r'"|\'|«|»', text))
    nuance_markers = len(re.findall(r"|".join(re.escape(c) for c in NUANCE_MARKERS), text.lower()))

    G = clamp(source_markers * 1.5 + citation_like * 0.5, 0, 10)
    N = clamp(nuance_markers * 2 + (article_length / 100), 0, 10)

    certainty = len(re.findall(r"certain|absolument|prouvé|évident|incontestable", text.lower()))
    emotional = len(re.findall(r"|".join(re.escape(w) for w in EMOTIONAL_WORDS), text.lower()))

    D = clamp(certainty * 2 + emotional * 1.5, 0, 10)
    M = round((G + N) - D, 1)
    V = clamp(G * 0.8 + N * 0.2, 0, 10)
    R = clamp(D * 0.7 + (emotional * 1.2), 0, 10)
    improved = round((G + N + V) - (D + R), 1)

    claims = [analyze_claim(s) for s in sentences[:15]]
    avg_claim_verifiability = sum(c.verifiability for c in claims) / len(claims) if claims else 0
    avg_claim_risk = sum(c.risk for c in claims) / len(claims) if claims else 0
    source_quality = clamp(source_markers * 3 - (emotional * 2), 0, 20)

    red_flags = []
    if D > 8:
        red_flags.append("Doxa saturée")
    if emotional > 5:
        red_flags.append("Pathos excessif")
    if G < 2:
        red_flags.append("Désert documentaire")
    if article_length < 50:
        red_flags.append("Format indigent")

    hard_fact_score_raw = (
        (0.18 * G + 0.12 * N + 0.20 * V + 0.22 * source_quality + 0.18 * avg_claim_verifiability)
        - (0.16 * D + 0.12 * R + 0.18 * avg_claim_risk + 0.9 * len(red_flags))
    )
    hard_fact_score = round(clamp(hard_fact_score_raw + 8, 0, 20), 1)

    if hard_fact_score < 6:
        verdict = T["low_credibility"]
    elif hard_fact_score < 10:
        verdict = T["prudent_credibility"]
    elif hard_fact_score < 15:
        verdict = T["rather_credible"]
    else:
        verdict = T["strong_credibility"]

    strengths = []
    if source_markers >= 2:
        strengths.append(T["presence_of_source_markers"])
    if citation_like >= 2:
        strengths.append(T["verifiability_clues"])
    if nuance_markers >= 2:
        strengths.append(T["text_contains_nuances"])
    if source_quality >= 12:
        strengths.append(T["text_evokes_robust_sources"])
    if any(c.status == T["rather_verifiable"] for c in claims):
        strengths.append(T["some_claims_verifiable"])

    weaknesses = []
    if certainty >= 3:
        weaknesses.append(T["overly_assertive_language"])
    if emotional >= 2:
        weaknesses.append(T["notable_emotional_sensational_charge"])
    if source_markers == 0 and citation_like == 0:
        weaknesses.append(T["almost_total_absence_of_verifiable_elements"])
    if article_length < 80:
        weaknesses.append(T["text_too_short"])
    weaknesses.extend(red_flags)
    if sum(1 for c in claims if c.status == T["very_fragile"]) >= 2:
        weaknesses.append(T["multiple_claims_very_fragile"])

    ME = (2 * D) - (G + N)

    return {
        "words": len(words),
        "sentences": len(sentences),
        "G": G,
        "N": N,
        "D": D,
        "M": M,
        "ME": ME,
        "V": V,
        "R": R,
        "improved": improved,
        "source_quality": source_quality,
        "avg_claim_risk": avg_claim_risk,
        "avg_claim_verifiability": avg_claim_verifiability,
        "hard_fact_score": hard_fact_score,
        "verdict": verdict,
        "profil_solidite": verdict,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "claims": claims,
        "red_flags": red_flags,
    }


@st.cache_data(show_spinner=False, ttl=1800)
def analyze_multiple_articles(keyword: str, max_results: int = 10) -> List[Dict]:
    articles = search_articles_by_keyword(keyword, max_results)
    results = []
    for art in articles:
        try:
            full_text = extract_article_from_url(art["url"])
            if len(full_text) > 120:
                analysis = analyze_article(full_text)
                results.append(
                    {
                        "Source": art["source"],
                        "Titre": art["title"],
                        "Score classique": analysis["M"],
                        "Hard Fact Score": analysis["hard_fact_score"],
                        "Verdict": analysis["verdict"],
                        "URL": art["url"],
                    }
                )
        except Exception:
            continue
    return results


@st.cache_data(show_spinner=False, ttl=1800)
def fetch_text_for_textarea(url: str) -> str:
    try:
        text = extract_article_from_url(url)
        return (text or "").strip()
    except Exception:
        return ""


# -----------------------------
# Corroboration
# -----------------------------
def extract_key_sentences_for_corroboration(text: str, max_sentences: int = 5) -> List[str]:
    sentences = [s.strip() for s in re.split(r"[.!?]+", text) if len(s.strip()) > 40]
    scored = []
    for s in sentences:
        score = 0
        if re.search(r"\d+", s):
            score += 2
        if re.search(r"\d{4}|janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre", s, re.I):
            score += 2
        if re.search(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+|[A-Z]{2,}", s):
            score += 2
        if any(word in s.lower() for word in [
            "selon", "affirme", "déclare", "rapport", "étude",
            "expert", "source", "publié", "annonce", "confirme", "révèle"
        ]):
            score += 1
        if any(word in s.lower() for word in [
            "absolument", "certain", "jamais", "toujours",
            "incontestable", "choc", "scandale", "révolution", "urgent"
        ]):
            score += 1
        scored.append((score, s))
    scored.sort(reverse=True, key=lambda x: x[0])
    return [s for _, s in scored[:max_sentences]]


def build_search_query_from_claim(claim: str) -> str:
    claim = re.sub(r"[^\w\s%\-]", " ", claim)
    claim = re.sub(r"\s+", " ", claim).strip()
    words = claim.split()
    important_words = [w for w in words if len(w) > 3][:12]
    return " ".join(important_words)


def extract_claim_features(claim: str) -> Dict:
    numbers = re.findall(r"\d+(?:[.,]\d+)?%?", claim)
    years = re.findall(r"\b(?:19|20)\d{2}\b", claim)
    proper_names = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+|[A-Z]{2,}", claim)
    words = re.findall(r"\b\w+\b", claim.lower())
    stopwords = {
        "les", "des", "une", "dans", "avec", "pour", "être", "sont", "mais",
        "plus", "comme", "nous", "vous", "sur", "par", "est", "ont", "aux",
        "du", "de", "la", "le", "un", "et", "ou", "en", "à", "au", "ce",
        "ces", "ses", "son", "sa", "qui", "que", "quoi", "dont", "ainsi", "alors",
    }
    keywords = [w for w in words if len(w) > 4 and w not in stopwords]
    return {
        "numbers": list(set(numbers)),
        "years": list(set(years)),
        "proper_names": list(set(proper_names)),
        "keywords": list(dict.fromkeys(keywords))[:12],
    }


def score_match_between_claim_and_result(claim: str, result_text: str) -> Dict:
    features = extract_claim_features(claim)
    rt = result_text.lower()
    number_hits = sum(1 for n in features["numbers"] if n.lower() in rt)
    year_hits = sum(1 for y in features["years"] if y.lower() in rt)
    proper_name_hits = sum(1 for p in features["proper_names"] if p.lower() in rt)
    keyword_hits = sum(1 for k in features["keywords"] if k.lower() in rt)

    score = 0.0
    score += number_hits * 3
    score += year_hits * 2
    score += proper_name_hits * 3
    score += min(keyword_hits, 5) * 1.2

    contradiction_markers = [
        "faux", "trompeur", "incorrect", "inexact",
        "démenti", "réfuté", "aucune preuve",
    ]
    contradiction_signal = any(marker in rt for marker in contradiction_markers)

    return {
        "score": round(score, 1),
        "number_hits": number_hits,
        "year_hits": year_hits,
        "proper_name_hits": proper_name_hits,
        "keyword_hits": keyword_hits,
        "contradiction_signal": contradiction_signal,
    }


def classify_corroboration(matches: List[Dict]) -> str:
    if not matches:
        return "insufficient"

    best_score = max(m["match_score"]["score"] for m in matches)
    contradiction_count = sum(1 for m in matches if m["match_score"]["contradiction_signal"])
    strong_matches = sum(1 for m in matches if m["match_score"]["score"] >= 8)
    medium_matches = sum(1 for m in matches if 4 <= m["match_score"]["score"] < 8)

    if strong_matches >= 2 and contradiction_count == 0:
        return "corroborated"
    if best_score >= 8 and contradiction_count >= 1:
        return "mixed"
    if medium_matches >= 1 or best_score >= 4:
        return "mixed"
    return "not_corroborated"


def display_corroboration_verdict(code: str) -> str:
    if code == "corroborated":
        return f"🟢 {T['corroborated']}"
    if code == "mixed":
        return f"🟠 {T['mixed']}"
    if code == "not_corroborated":
        return f"🔴 {T['not_corroborated']}"
    return f"⚪ {T['insufficiently_documented']}"


def corroborate_claims(text: str, max_claims: int = 5, max_results_per_claim: int = 3) -> List[Dict]:
    claims = extract_key_sentences_for_corroboration(text, max_sentences=max_claims)
    corroboration_results = []

    trusted_domains = [
        "reuters.com", "apnews.com", "bbc.com", "nytimes.com", "theguardian.com",
        "lemonde.fr", "lefigaro.fr", "liberation.fr", "francetvinfo.fr", "lesechos.fr",
        "who.int", "un.org", "worldbank.org", "nature.com", "science.org",
        "elpais.com", "elmundo.es", "dw.com", "spiegel.de",
    ]

    try:
        with DDGS() as ddgs:
            for claim in claims:
                query = build_search_query_from_claim(claim)
                search_results = list(ddgs.text(query, max_results=max_results_per_claim * 5))
                filtered = []
                for r in search_results:
                    url = r.get("href", "")
                    title = r.get("title", "")
                    body = r.get("body", "")
                    combined_text = f"{title} {body}"
                    if any(domain in url for domain in trusted_domains):
                        match_score = score_match_between_claim_and_result(claim, combined_text)
                        filtered.append(
                            {
                                "title": title,
                                "url": url,
                                "snippet": body,
                                "match_score": match_score,
                            }
                        )
                filtered = sorted(filtered, key=lambda x: x["match_score"]["score"], reverse=True)[:max_results_per_claim]
                verdict = classify_corroboration(filtered)
                corroboration_results.append(
                    {
                        "claim": claim,
                        "query": query,
                        "matches": filtered,
                        "verdict": verdict,
                    }
                )
    except Exception as e:
        st.warning(f"Erreur de corroboration : {e}")

    return corroboration_results


# -----------------------------
# IA helpers
# -----------------------------
@st.cache_data(show_spinner=False)
def generate_ai_summary(article_text: str, result: Dict, max_chars: int = 7000) -> str:
    if client is None:
        return ""

    short_text = article_text[:max_chars]
    claims_preview = []
    for c in result.get("claims", [])[:8]:
        claims_preview.append(
            {
                "affirmation": c.text,
                "statut": c.status,
                "verifiabilite": c.verifiability,
                "risque": c.risk,
                "has_number": c.has_number,
                "has_date": c.has_date,
                "has_named_entity": c.has_named_entity,
                "has_source_cue": c.has_source_cue,
            }
        )

    prompt = f"""
Tu es un assistant de lecture critique rigoureux.

Ta tâche :
1. Résumer le profil global de crédibilité du texte.
2. Expliquer la différence entre plausibilité structurelle et robustesse factuelle.
3. Identifier les 3 principales forces.
4. Identifier les 3 principales fragilités.
5. Terminer par un verdict prudent.

Contraintes :
- Sois clair, concis et concret.
- N’invente aucun fait.
- N’affirme pas avec certitude qu’un texte est vrai ou faux sans justification solide.
- Appuie-toi sur les métriques heuristiques ci-dessous.

Analyse heuristique :
{json.dumps({
    'G': result.get('G'),
    'N': result.get('N'),
    'D': result.get('D'),
    'M': result.get('M'),
    'V': result.get('V'),
    'R': result.get('R'),
    'hard_fact_score': result.get('hard_fact_score'),
    'verdict': result.get('verdict'),
    'strengths': result.get('strengths', []),
    'weaknesses': result.get('weaknesses', []),
    'claims': claims_preview,
    'red_flags': result.get('red_flags', []),
}, ensure_ascii=False, indent=2)}

Texte à analyser :
{short_text}
"""

    try:
        response = client.responses.create(model="gpt-4o", input=prompt)
        return response.output_text.strip()
    except Exception as e:
        return f"Erreur IA : {e}"


# -----------------------------
# Réglages
# -----------------------------
with st.expander(T["settings"], expanded=False):
    use_sample = st.button(T["load_example"])
    show_method = st.toggle(T["show_method"], value=True)
    st.divider()
    st.subheader(T["hard_fact_score_scale"])
    st.markdown(
        f"- **0–5** : {T['scale_0_5']}\n"
        f"- **6–9** : {T['scale_6_9']}\n"
        f"- **10–14** : {T['scale_10_14']}\n"
        f"- **15–20** : {T['scale_15_20']}"
    )

if "article" not in st.session_state:
    st.session_state.article = SAMPLE_ARTICLE
if "article_source" not in st.session_state:
    st.session_state.article_source = "paste"
if "loaded_url" not in st.session_state:
    st.session_state.loaded_url = ""
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "last_article" not in st.session_state:
    st.session_state.last_article = ""
if "multi_results" not in st.session_state:
    st.session_state.multi_results = []
if "last_keyword" not in st.session_state:
    st.session_state.last_keyword = ""

if use_sample:
    st.session_state.article = SAMPLE_ARTICLE
    st.session_state.article_source = "paste"
    st.session_state.loaded_url = ""


# -----------------------------
# Analyse multi-articles
# -----------------------------
st.subheader(T["topic_section"])
keyword = st.text_input(T["topic"], placeholder=T["topic_placeholder"])

if st.button(T["analyze_topic"], key="analyze_topic"):
    if keyword.strip():
        st.info(T["searching"])
        st.session_state.multi_results = analyze_multiple_articles(keyword.strip(), max_results=10)
        st.session_state.last_keyword = keyword.strip()
    else:
        st.session_state.multi_results = []
        st.warning(T["enter_keyword_first"])

if st.session_state.get("multi_results"):
    df_multi = pd.DataFrame(st.session_state.multi_results).sort_values("Hard Fact Score", ascending=False)

    st.success(f"{len(df_multi)} {T['articles_analyzed']}")

    c1, c2 = st.columns(2)
    c1.metric(T["analyzed_articles"], len(df_multi))
    c2.metric(T["avg_hard_fact"], round(df_multi["Hard Fact Score"].mean(), 1))
    st.metric(T["avg_classic_score"], round(df_multi["Score classique"].mean(), 1))

    ecart_type_hf = df_multi["Hard Fact Score"].std()
    indice_doxa = "high" if ecart_type_hf < 1.5 else ("medium" if ecart_type_hf < 3 else "low")
    st.metric(T["topic_doxa_index"], T[indice_doxa])

    st.subheader(T["credibility_score_dispersion"])
    df_plot = df_multi.copy()
    df_plot["Article"] = [f"{T['article_label']} {i+1}" for i in range(len(df_plot))]
    st.bar_chart(df_plot.set_index("Article")["Hard Fact Score"])
    st.dataframe(df_multi, use_container_width=True, hide_index=True)

    st.markdown("### Actions sur les articles trouvés")

    for i, row in df_multi.reset_index(drop=True).iterrows():
        with st.container(border=True):
            st.markdown(f"### {row['Titre']}")
            st.caption(f"{row['Source']}")

            score = row["Hard Fact Score"]
            if score <= 6:
                color, label = "🔴", "Fragile"
            elif score <= 11:
                color, label = "🟠", "Douteux"
            elif score <= 15:
                color, label = "🟡", "Plausible"
            else:
                color, label = "🟢", "Robuste"

            st.markdown(f"**{color} Score de crédibilité : {score:.1f}/20 — {label}**")
            st.progress(score / 20)

            col1, col2 = st.columns(2)
            with col1:
                st.link_button("🌐 Ouvrir l'article", row["URL"], use_container_width=True)
            with col2:
                if st.button(f"📥 Charger pour analyse", key=f"load_article_{i}"):
                    loaded_text = fetch_text_for_textarea(row["URL"])
                    if loaded_text:
                        st.session_state.article = loaded_text
                        st.session_state.article_source = "url"
                        st.session_state.loaded_url = row["URL"]
                        st.success("Article chargé dans la zone de texte.")
                        st.rerun()
                    else:
                        st.warning("Impossible d'extraire le texte.")
elif st.session_state.get("last_keyword"):
    st.warning(T["no_exploitable_articles_found"])


# -----------------------------
# Chargement URL
# -----------------------------
with st.form("url_form"):
    url = st.text_input(T["url"])
    load_url_submitted = st.form_submit_button(T["load_url"])

if load_url_submitted:
    if url:
        texte = extract_article_from_url(url)
        if texte:
            st.session_state.article = texte
            st.session_state.article_source = "url"
            st.session_state.loaded_url = url
            st.success(T["article_loaded_from_url"])
            st.rerun()
        else:
            st.error(T["unable_to_retrieve_text"])
    else:
        st.warning(T["paste_url_first"])


# -----------------------------
# Zone d’analyse
# -----------------------------
previous_article = st.session_state.article

st.markdown("### Zone d’analyse")

with st.container(border=True):
    st.caption("Collez un texte, chargez une URL, ou dictez directement.")

    if MICRO_AVAILABLE:
        spoken_text = speech_to_text(
            language="fr",
            start_prompt="🎙️ Dicter",
            stop_prompt="⏹️ Stop",
            just_once=True,
            use_container_width=True,
            key="speech_to_text_article"
        )

        if spoken_text:
            st.session_state.article = spoken_text
            st.session_state.article_source = "paste"
            st.success("Texte dicté reçu.")
            st.rerun()
    else:
        st.info("Microphone indisponible sur cette version.")

    with st.form("article_form"):
        article = st.text_area(
            T["paste"],
            key="article",
            height=220,
            label_visibility="collapsed",
            placeholder=T["paste"]
        )
        analyze_submitted = st.form_submit_button(T["analyze"], use_container_width=True)

if article.strip() != previous_article.strip():
    st.session_state.article_source = "paste"

source_label = T["manual_paste"] if st.session_state.get("article_source") == "paste" else T["loaded_url_source"]
st.caption(f"{T['text_source']} : {source_label}")

if st.session_state.get("loaded_url"):
    st.caption(f"URL : {st.session_state.loaded_url}")


# -----------------------------
# Analyse principale
# -----------------------------
if analyze_submitted:
    st.session_state.last_result = analyze_article(article)
    st.session_state.last_article = article

result = st.session_state.last_result
article_for_analysis = st.session_state.last_article

if result:
    col1, col2, col3 = st.columns(3)
    col1.metric(T["classic_score"], result["M"], help=T["help_classic_score"])
    col2.metric(T["improved_score"], result["improved"], help=T["help_improved_score"])
    col3.metric(T["hard_fact_score"], result["hard_fact_score"], help=T["help_hard_fact_score"])

    score = result["hard_fact_score"]
    if score <= 6:
        couleur, etiquette, message = "🔴", T["fragile"], T["fragile_message"]
    elif score <= 11:
        couleur, etiquette, message = "🟠", T["doubtful"], T["doubtful_message"]
    elif score <= 15:
        couleur, etiquette, message = "🟡", T["plausible"], T["plausible_message"]
    else:
        couleur, etiquette, message = "🟢", T["robust"], T["robust_message"]

    st.subheader(f"{couleur} {T['credibility_gauge']} : {etiquette}")
    st.progress(score / 20)
    st.caption(f"{T['score']} : {score}/20 — {message}")
    st.caption("Sur cette échelle, un texte véritablement crédible se situe généralement dans la zone robuste.")

    st.subheader("Diagnostic cognitif")
    life_score = round((result["hard_fact_score"] / 20) * 100, 1)
    mecroyance_bar = max(0.0, min(1.0, (result["M"] + 10) / 30))

    col1, col2 = st.columns(2)
    with col1:
        st.write("Vitalité cognitive")
        st.progress(life_score / 100)
        st.caption(f"{life_score}%")
    with col2:
        st.write("Indice de mécroyance")
        st.progress(mecroyance_bar)
        st.caption(f"M = {result['M']}")

    st.subheader(f"{T['verdict']} : {result['verdict']}")
    st.subheader(T["summary"])

    m1, m2 = st.columns(2)
    m1.metric("G — gnōsis", result["G"])
    m2.metric("N — nous", result["N"])
    m3, m4 = st.columns(2)
    m3.metric("D — doxa", result["D"])
    m4.metric("V — vérifiabilité", result["V"])
    m5, m6 = st.columns(2)
    m5.metric("QS", result["source_quality"])
    m6.metric("RC", round(result["avg_claim_risk"], 1))
    m7, m8 = st.columns(2)
    m7.metric("VC", round(result["avg_claim_verifiability"], 1))
    m8.metric("F", len(result["red_flags"]))

    st.divider()
    st.subheader("Triangle cognitif G-N-D")
    st.caption("Le texte est placé dans l’espace de la cognition : savoir articulé, compréhension intégrée, et certitude assertive.")
    fig_triangle = plot_cognitive_triangle_3d(result["G"], result["N"], result["D"])
    st.pyplot(fig_triangle, use_container_width=True)

    st.subheader("Métriques cognitives")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Indice de mécroyance (M)", round(result["M"], 2))
    with col2:
        st.metric("Indice de mensonge (ME)", round(result["ME"], 2))

    delta_mm = round(result["M"] - result["ME"], 2)
    st.caption(f"Écart cognitif (M − ME) : {delta_mm}")

    if result["M"] > result["ME"] + 1:
        dominant_pattern = "Structure dominante : mécroyance"
    elif result["ME"] > result["M"] + 1:
        dominant_pattern = "Structure dominante : mensonge stratégique"
    else:
        dominant_pattern = "Structure dominante : mixte ou ambiguë"

    st.subheader("Structure cognitive dominante")
    st.write(dominant_pattern)

    if result["ME"] > result["M"] and result["ME"] > 0:
        cognitive_type = "Mensonge stratégique possible"
    elif result["M"] < 0:
        cognitive_type = "Forte mécroyance / clôture cognitive"
    else:
        cognitive_type = "Cognition probablement sincère mais désalignée"

    st.subheader("Interprétation cognitive")
    st.write(cognitive_type)

    if result["M"] - result["ME"] > 3:
        diagnosis = "Structure de mécroyance forte"
    elif result["M"] > result["ME"]:
        diagnosis = "Structure de mécroyance modérée"
    elif abs(result["M"] - result["ME"]) <= 1:
        diagnosis = "Structure cognitive ambiguë"
    else:
        diagnosis = "Tromperie stratégique possible"

    st.subheader("Diagnostic cognitif")
    st.write(diagnosis)

    conflict = abs(result["M"] - result["ME"])
    conflict_bar = min(conflict / 10, 1)

    st.write("Tension cognitive (mécroyance vs mensonge)")
    st.caption(
        "Cette barre indique si le discours ressemble plutôt à une erreur sincère "
        "(mécroyance) ou à une possible manipulation. "
        "Plus la barre est élevée, plus l’écart entre erreur sincère et mensonge probable est marqué."
    )
    st.progress(conflict_bar)
    st.caption("Erreur sincère ⟵⟶ Manipulation probable")

    with st.expander(T["strengths_detected"], expanded=True):
        if result["strengths"]:
            for item in result["strengths"]:
                st.success(item)
        else:
            st.info(T["few_strong_signals"])

    with st.expander(T["weaknesses_detected"], expanded=True):
        if result["weaknesses"]:
            for item in result["weaknesses"]:
                st.error(item)
        else:
            st.success(T["no_major_weakness"])

    st.divider()
    st.subheader("Structure cognitive du texte analysé")
    st.info(T["llm_intro"])

    cog = Cognition(result["G"], result["N"], result["D"])
    overconfidence = result["D"] - (result["G"] + result["N"])
    calibration = result["D"] / (result["G"] + result["N"]) if (result["G"] + result["N"]) > 0 else 10
    revisability = (result["G"] + result["N"] + result["V"]) - result["D"]
    closure = (result["D"] * (1 + len(result["red_flags"]) / 5)) / (result["G"] + result["N"]) if (result["G"] + result["N"]) > 0 else 10

    c1, c2 = st.columns(2)
    c1.metric(T["overconfidence"], round(overconfidence, 2))
    c2.metric(T["calibration"], round(calibration, 2))
    c3, c4 = st.columns(2)
    c3.metric(T["revisability"], round(revisability, 2))
    c4.metric(T["cognitive_closure"], round(closure, 2))
    st.markdown(f"**{T['interpretation']} :** {cog.interpret()}")

    st.subheader(T["hard_fact_checking_by_claim"])
    claims_df = pd.DataFrame(
        [
            {
                T["claim"]: c.text,
                T["status"]: c.status,
                f"{T['verifiability']} /20": c.verifiability,
                f"{T['risk']} /20": c.risk,
                T["number"]: T["yes"] if c.has_number else T["no"],
                T["date"]: T["yes"] if c.has_date else T["no"],
                T["named_entity"]: T["yes"] if c.has_named_entity else T["no"],
                T["attributed_source"]: T["yes"] if c.has_source_cue else T["no"],
            }
            for c in result["claims"]
        ]
    )

    if not claims_df.empty:
        st.dataframe(claims_df, use_container_width=True, hide_index=True)
    else:
        st.info(T["paste_longer_text"])

    st.divider()
    st.subheader(T["ai_module"])
    st.caption(T["ai_module_caption"])

    if client is None:
        st.warning(T["ai_unavailable"])
    else:
        if st.button(T["generate_ai_analysis"], key="generate_ai_analysis"):
            with st.spinner("Analyse IA en cours..."):
                ai_summary = generate_ai_summary(article_for_analysis, result)
            st.subheader(T["ai_analysis_result"])
            st.markdown(ai_summary)

    if st.session_state.get("article_source") == "paste":
        st.divider()
        st.subheader(T["external_corroboration_module"])
        st.caption(T["external_corroboration_caption"])
        with st.spinner(T["corroboration_in_progress"]):
            corroboration = corroborate_claims(article_for_analysis, max_claims=5, max_results_per_claim=3)
        if corroboration:
            for i, item in enumerate(corroboration, start=1):
                title_preview = item["claim"][:140] + ("..." if len(item["claim"]) > 140 else "")
                with st.expander(f"{T['claim']} {i} : {title_preview}", expanded=(i == 1)):
                    st.markdown(f"**{T['corroboration_verdict']} :** {display_corroboration_verdict(item['verdict'])}")
                    st.markdown(f"**{T['generated_query']} :** `{item['query']}`")
                    if item["matches"]:
                        for match in item["matches"]:
                            st.markdown(f"**[{match['title']}]({match['url']})**")
                            st.markdown(
                                f"- **{T['match_score']}** : {match['match_score']['score']}\n"
                                f"- **{T['contradiction_signal']}** : {T['detected'] if match['match_score']['contradiction_signal'] else T['not_detected']}"
                            )
                            if match["snippet"]:
                                st.caption(match["snippet"])
                    else:
                        st.warning(T["no_strong_sources_found"])
        else:
            st.info(T["no_corroboration_found"])
else:
    st.info(T["paste_text_or_load_url"])


# -----------------------------
# Méthode
# -----------------------------
if show_method:
    st.subheader(T["method"])
    st.markdown(
        f"### {T['original_formula']}\n"
        f"`M = (G + N) − D`\n"
        f"- {T['articulated_knowledge_density']}\n"
        f"- {T['integration']}\n"
        f"- {T['assertive_rigidity']}\n\n"
        f"### {T['llm_metrics']}\n"
        f"- **{T['overconfidence']}** : `D - (G + N)`\n"
        f"- **{T['calibration']}** : `D / (G + N)`\n"
        f"- **{T['revisability']}** : `(G + N + V) - D`\n"
        f"- **{T['cognitive_closure']}** : `(D * S) / (G + N)`\n\n"
        f"{T['disclaimer']}"
    )


# -----------------------------
# Laboratoire interactif
# -----------------------------
st.divider()
st.subheader("Laboratoire interactif de la mécroyance")
st.caption(
    "Expérimentez la formule cognitive : M = (G + N) − D. "
    "Modifiez les paramètres pour observer l’évolution des stades cognitifs."
)

g_game = st.slider("G — gnōsis (savoir articulé)", 0.0, 10.0, 5.0, 0.5)
n_game = st.slider("N — nous (intégration vécue)", 0.0, 10.0, 5.0, 0.5)
d_game = st.slider("D — doxa (certitude / saturation)", 0.0, 10.0, 5.0, 0.5)

m_game = round((g_game + n_game) - d_game, 1)

st.markdown(
    f"""
    <div style="
        background:#f1f5f9;
        border-radius:14px;
        padding:18px;
        margin-top:10px;
        border:1px solid #dbe3ec;
        text-align:center;
        font-size:1.3rem;
        font-weight:700;
    ">
        M = ({g_game:.1f} + {n_game:.1f}) − {d_game:.1f} =
        <span style="color:#0b6e4f;">{m_game:.1f}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if m_game < 0:
    stage = "Fermeture cognitive"
    explanation = "La certitude dépasse la compréhension : la pensée se verrouille."
    percent = 10
elif m_game <= 4:
    stage = "Enfance cognitive"
    explanation = "Structure cognitive naissante, encore fragile."
    percent = 25
elif m_game <= 10:
    stage = "Adolescence cognitive"
    explanation = "Cognition stable mais encore agitée."
    percent = 50
elif m_game <= 17:
    stage = "Maturité cognitive"
    explanation = "Équilibre entre savoir, expérience et doute."
    percent = 75
elif m_game < 19:
    stage = "Sagesse structurelle"
    explanation = "État rare d’équilibre cognitif."
    percent = 90
else:
    stage = "Asymptote de vérité"
    explanation = "Horizon théorique de cohérence maximale."
    percent = 100

st.markdown(f"**Stade actuel : {stage}**")
st.progress(percent / 100)
st.caption(f"M = {m_game} — {explanation}")

st.markdown("### Évolution cognitive")

stages = [
    ("Fermeture", -10, 0),
    ("Enfance", 0, 4.1),
    ("Adolescence", 4.1, 10.1),
    ("Maturité", 10.1, 17.1),
    ("Sagesse", 17.1, 19.1),
    ("Asymptote", 19.1, 21),
]

cols = st.columns(len(stages))
for i, (name, low, high) in enumerate(stages):
    active = low <= m_game < high
    with cols[i]:
        if active:
            st.success(name)
        else:
            st.info(name)

st.caption("Lorsque G et N augmentent sans inflation de D, la cognition gagne en revisabilité.")
