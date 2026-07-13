import html
import math
import re
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser
import requests
import trafilatura


# =========================================================
# 기본 설정
# =========================================================

KST = timezone(timedelta(hours=9))

SEARCH_KEYWORDS = [
    "한국 국제개발협력",
    "한국 ODA",
    "KOICA",
    "KCOC 국제개발협력",
    "개발협력 NGO",
    "해외봉사단",
    "인도적 지원",
    "OECD DAC 한국",
]

MAX_ARTICLES_PER_KEYWORD = 5
MAX_TOTAL_ARTICLES = 24
MAX_ARTICLES_PER_SECTION = 7

REQUEST_TIMEOUT = 15
REQUEST_DELAY = 0.3
MAX_ARTICLE_TEXT_LENGTH = 15000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}


# =========================================================
# 분류 규칙
# =========================================================

CATEGORY_RULES = {
    "정책·ODA": [
        "oda",
        "공적개발원조",
        "국제개발협력",
        "개발협력",
        "koica",
        "코이카",
        "oecd",
        "dac",
        "외교부",
        "국무조정실",
        "무상원조",
        "유상원조",
        "개발재원",
        "협력사업",
    ],
    "NGO·시민사회": [
        "ngo",
        "시민사회",
        "kcoc",
        "비정부기구",
        "비영리",
        "민간단체",
        "국제구호",
        "시민단체",
        "책무성",
        "사회혁신",
    ],
    "해외봉사": [
        "해외봉사",
        "봉사단",
        "volunteer",
        "wfk",
        "월드프렌즈",
        "peace corps",
        "청년인턴",
        "글로벌인재",
        "인재양성",
    ],
    "인도적 지원": [
        "인도적 지원",
        "인도주의",
        "긴급구호",
        "난민",
        "재난",
        "분쟁",
        "기아",
        "식량위기",
        "구호",
        "재건",
    ],
}


ORGANIZATION_RULES = {
    "KOICA": [
        "koica",
        "코이카",
        "한국국제협력단",
    ],
    "KCOC": [
        "kcoc",
        "국제개발협력민간협의회",
    ],
    "OECD DAC": [
        "oecd",
        "dac",
    ],
    "외교부": [
        "외교부",
    ],
    "국무조정실": [
        "국무조정실",
    ],
    "World Bank": [
        "world bank",
        "세계은행",
    ],
    "UNDP": [
        "undp",
        "유엔개발계획",
    ],
    "UNICEF": [
        "unicef",
        "유니세프",
    ],
    "WHO": [
        "who",
        "세계보건기구",
    ],
    "USAID": [
        "usaid",
    ],
    "JICA": [
        "jica",
        "일본국제협력기구",
    ],
    "ADB": [
        "adb",
        "아시아개발은행",
    ],
    "Peace Corps": [
        "peace corps",
        "평화봉사단",
    ],
}


COUNTRY_RULES = {
    "대한민국": [
        "한국",
        "대한민국",
        "코리아",
    ],
    "캄보디아": [
        "캄보디아",
        "cambodia",
    ],
    "르완다": [
        "르완다",
        "rwanda",
    ],
    "우간다": [
        "우간다",
        "uganda",
    ],
    "페루": [
        "페루",
        "peru",
    ],
    "케냐": [
        "케냐",
        "kenya",
    ],
    "에티오피아": [
        "에티오피아",
        "ethiopia",
    ],
    "라오스": [
        "라오스",
        "laos",
    ],
    "베트남": [
        "베트남",
        "vietnam",
    ],
    "필리핀": [
        "필리핀",
        "philippines",
    ],
    "몽골": [
        "몽골",
        "mongolia",
    ],
    "네팔": [
        "네팔",
        "nepal",
    ],
    "방글라데시": [
        "방글라데시",
        "bangladesh",
    ],
    "스리랑카": [
        "스리랑카",
        "sri lanka",
    ],
    "인도네시아": [
        "인도네시아",
        "indonesia",
    ],
    "탄자니아": [
        "탄자니아",
        "tanzania",
    ],
    "가나": [
        "가나",
        "ghana",
    ],
    "세네갈": [
        "세네갈",
        "senegal",
    ],
    "모로코": [
        "모로코",
        "morocco",
    ],
    "요르단": [
        "요르단",
        "jordan",
    ],
    "우크라이나": [
        "우크라이나",
        "ukraine",
    ],
    "팔레스타인": [
        "팔레스타인",
        "palestine",
        "가자",
        "gaza",
    ],
}


COUNTRY_FLAGS = {
    "대한민국": "🇰🇷",
    "캄보디아": "🇰🇭",
    "르완다": "🇷🇼",
    "우간다": "🇺🇬",
    "페루": "🇵🇪",
    "케냐": "🇰🇪",
    "에티오피아": "🇪🇹",
    "라오스": "🇱🇦",
    "베트남": "🇻🇳",
    "필리핀": "🇵🇭",
    "몽골": "🇲🇳",
    "네팔": "🇳🇵",
    "방글라데시": "🇧🇩",
    "스리랑카": "🇱🇰",
    "인도네시아": "🇮🇩",
    "탄자니아": "🇹🇿",
    "가나": "🇬🇭",
    "세네갈": "🇸🇳",
    "모로코": "🇲🇦",
    "요르단": "🇯🇴",
    "우크라이나": "🇺🇦",
    "팔레스타인": "🇵🇸",
}


KEYWORD_CANDIDATES = [
    "KOICA",
    "KCOC",
    "ODA",
    "OECD DAC",
    "USAID",
    "JICA",
    "World Bank",
    "UNDP",
    "UNICEF",
    "SDGs",
    "기후변화",
    "해외봉사",
    "봉사단",
    "NGO",
    "시민사회",
    "인도적 지원",
    "교육",
    "보건",
    "농업",
    "디지털",
    "청년",
    "난민",
]


STOPWORDS = {
    "기자",
    "뉴스",
    "관련",
    "대한",
    "통해",
    "위해",
    "이번",
    "있는",
    "있다",
    "한다",
    "했다",
    "밝혔다",
    "예정이다",
    "또한",
    "그리고",
    "하지만",
    "에서",
    "으로",
    "하는",
    "했다는",
    "것으로",
    "대해",
}


# =========================================================
# 기본 유틸리티
# =========================================================

def clean_text(value: str) -> str:
    """HTML 엔티티, 태그, 줄바꿈 및 반복 공백을 정리합니다."""
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\xa0", " ")
    value = value.replace("\n", " ")
    value = value.replace("\r", " ")
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def normalize_title(title: str) -> str:
    """중복 판정을 위한 기사 제목 정규화."""
    normalized = clean_text(title).lower()

    # 제목 뒤 언론사 표시 제거
    normalized = re.sub(
        r"\s*[-–—]\s*[^-–—]+$",
        "",
        normalized,
    )

    normalized = re.sub(
        r"[^가-힣a-z0-9]",
        "",
        normalized,
    )

    return normalized


def contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()

    return any(
        keyword.lower() in lowered
        for keyword in keywords
    )


def google_news_rss_url(keyword: str) -> str:
    encoded_keyword = quote(keyword)

    return (
        "https://news.google.com/rss/search"
        f"?q={encoded_keyword}"
        "&hl=ko"
        "&gl=KR"
        "&ceid=KR:ko"
    )


# =========================================================
# RSS 뉴스 수집
# =========================================================

def collect_news() -> list[dict[str, str]]:
    articles: list[dict[str, str]] = []
    seen_titles: set[str] = set()

    for keyword in SEARCH_KEYWORDS:
        feed_url = google_news_rss_url(keyword)
        feed = feedparser.parse(feed_url)

        keyword_count = 0

        for entry in feed.entries:
            title = clean_text(
                entry.get("title", "")
            )
            link = clean_text(
                entry.get("link", "")
            )
            description = clean_text(
                entry.get("summary", "")
            )

            source_data = entry.get("source", {})
            source = clean_text(
                source_data.get(
                    "title",
                    "출처 미확인",
                )
            )

            published = clean_text(
                entry.get("published", "")
            )

            if not title or not link:
                continue

            normalized = normalize_title(title)

            if not normalized:
                continue

            if normalized in seen_titles:
                continue

            articles.append(
                {
                    "title": title,
                    "link": link,
                    "source": source,
                    "description": description,
                    "search_keyword": keyword,
                    "published": published,
                }
            )

            seen_titles.add(normalized)
            keyword_count += 1

            if keyword_count >= MAX_ARTICLES_PER_KEYWORD:
                break

            if len(articles) >= MAX_TOTAL_ARTICLES:
                return articles

    return articles


# =========================================================
# 기사 본문 추출
# =========================================================

def fetch_article_text(url: str) -> tuple[str, str]:
    """
    기사 URL에 접속하여 최종 URL과 본문 텍스트를 반환합니다.
    실패하면 원래 URL과 빈 문자열을 반환합니다.
    """

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()

        final_url = response.url

        extracted = trafilatura.extract(
            response.text,
            url=final_url,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            favor_recall=True,
        )

        if not extracted:
            return final_url, ""

        extracted = clean_text(extracted)

        if len(extracted) < 100:
            return final_url, ""

        return (
            final_url,
            extracted[:MAX_ARTICLE_TEXT_LENGTH],
        )

    except Exception as error:
        print(
            "본문 추출 실패: "
            f"{type(error).__name__} / {url}"
        )

        return url, ""


# =========================================================
# 추출형 요약
# =========================================================

def split_sentences(text: str) -> list[str]:
    text = clean_text(text)

    if not text:
        return []

    sentences = re.split(
        r"(?<=[.!?。！？])\s+|"
        r"(?<=[가-힣]다\.)\s+",
        text,
    )

    results: list[str] = []

    for sentence in sentences:
        sentence = clean_text(sentence)

        if len(sentence) < 25:
            continue

        if sentence in results:
            continue

        results.append(sentence)

    return results


def tokenize(text: str) -> list[str]:
    words = re.findall(
        r"[가-힣]{2,}|[A-Za-z]{3,}",
        text.lower(),
    )

    return [
        word
        for word in words
        if word not in STOPWORDS
    ]


def shorten_sentence(
    sentence: str,
    max_length: int = 260,
) -> str:
    """
    지나치게 긴 문장은 가독성을 위해 적절한 위치에서 줄입니다.
    CSS 표시 오류가 아니라 문장 자체가 매우 긴 경우에만 적용합니다.
    """

    sentence = clean_text(sentence)

    if len(sentence) <= max_length:
        return sentence

    cut_position = sentence.rfind(
        " ",
        0,
        max_length,
    )

    if cut_position < max_length * 0.6:
        cut_position = max_length

    return sentence[:cut_position].rstrip() + "…"


def summarize_text(
    title: str,
    article_text: str,
    fallback: str,
    sentence_count: int = 3,
) -> list[str]:
    """
    기사 본문 문장 가운데 중요도가 높은 문장을 선별합니다.
    AI 생성 요약이 아니라 기사에 실제로 포함된 문장을 사용합니다.
    """

    source_text = clean_text(
        article_text or fallback
    )

    if not source_text:
        return [
            "기사 본문을 자동으로 추출하지 못했습니다. "
            "세부 내용은 하단 원문기사에서 확인해 주세요."
        ]

    if normalize_title(source_text) == normalize_title(title):
        return [
            "기사 본문을 자동으로 추출하지 못했습니다. "
            "세부 내용은 하단 원문기사에서 확인해 주세요."
        ]

    sentences = split_sentences(source_text)

    if not sentences:
        return [
            shorten_sentence(source_text)
        ]

    all_words = tokenize(
        f"{title} {source_text}"
    )

    if not all_words:
        return [
            shorten_sentence(sentence)
            for sentence in sentences[:sentence_count]
        ]

    frequencies = Counter(all_words)
    max_frequency = max(frequencies.values())

    normalized_frequencies = {
        word: count / max_frequency
        for word, count in frequencies.items()
    }

    title_words = set(tokenize(title))
    scored_sentences: list[
        tuple[int, float, str]
    ] = []

    for index, sentence in enumerate(sentences):
        words = tokenize(sentence)

        if not words:
            continue

        frequency_score = sum(
            normalized_frequencies.get(word, 0)
            for word in words
        ) / math.sqrt(len(words))

        title_score = sum(
            1
            for word in words
            if word in title_words
        )

        # 기사의 앞부분에 있는 문장에 소폭 가점
        position_score = max(
            0.0,
            1.0 - index * 0.04,
        )

        # 지나치게 짧거나 긴 문장에 감점
        length_score = 1.0

        if len(sentence) < 45:
            length_score = 0.7
        elif len(sentence) > 350:
            length_score = 0.8

        total_score = (
            frequency_score
            + title_score * 0.8
            + position_score * 0.35
        ) * length_score

        scored_sentences.append(
            (
                index,
                total_score,
                sentence,
            )
        )

    if not scored_sentences:
        return [
            shorten_sentence(sentence)
            for sentence in sentences[:sentence_count]
        ]

    selected = sorted(
        scored_sentences,
        key=lambda item: item[1],
        reverse=True,
    )[:sentence_count]

    # 기사 원래 문장 순서대로 정렬
    selected = sorted(
        selected,
        key=lambda item: item[0],
    )

    summaries = [
        shorten_sentence(sentence)
        for _, _, sentence in selected
    ]

    return summaries


# =========================================================
# 기사 분류
# =========================================================

def classify_category(
    article: dict[str, object],
) -> str:
    text = " ".join(
        [
            str(article.get("title", "")),
            str(article.get("source", "")),
            str(article.get("description", "")),
            str(article.get("search_keyword", "")),
            str(article.get("article_text", ""))[:1500],
        ]
    ).lower()

    scores: dict[str, int] = {}

    for category, keywords in CATEGORY_RULES.items():
        scores[category] = sum(
            1
            for keyword in keywords
            if keyword.lower() in text
        )

    highest_category = max(
        scores,
        key=scores.get,
    )

    if scores[highest_category] == 0:
        return "정책·ODA"

    return highest_category


def detect_organization(
    article: dict[str, object],
) -> str:
    text = " ".join(
        [
            str(article.get("title", "")),
            str(article.get("source", "")),
            str(article.get("description", "")),
            str(article.get("article_text", ""))[:1000],
        ]
    )

    for organization, keywords in ORGANIZATION_RULES.items():
        if contains_any(text, keywords):
            return organization

    source = str(
        article.get(
            "source",
            "출처 미확인",
        )
    ).strip()

    if source and source != "출처 미확인":
        return source

    return "기타 기관"


def detect_countries(
    article: dict[str, object],
) -> list[str]:
    text = " ".join(
        [
            str(article.get("title", "")),
            str(article.get("description", "")),
            str(article.get("article_text", "")),
        ]
    ).lower()

    countries: list[str] = []

    for country, keywords in COUNTRY_RULES.items():
        matched = any(
            keyword.lower() in text
            for keyword in keywords
        )

        if matched:
            countries.append(country)

    return countries


def enrich_articles(
    articles: list[dict[str, str]],
) -> list[dict[str, object]]:
    enriched_articles: list[
        dict[str, object]
    ] = []

    total = len(articles)

    for index, article in enumerate(
        articles,
        start=1,
    ):
        print(
            f"기사 본문 수집 중 ({index}/{total}): "
            f"{article['title'][:55]}"
        )

        final_url, article_text = fetch_article_text(
            article["link"]
        )

        enriched: dict[str, object] = dict(article)
        enriched["link"] = final_url
        enriched["article_text"] = article_text

        enriched["summary"] = summarize_text(
            title=article["title"],
            article_text=article_text,
            fallback=article["description"],
            sentence_count=3,
        )

        enriched["category"] = classify_category(
            enriched
        )
        enriched["organization"] = (
            detect_organization(enriched)
        )
        enriched["countries"] = detect_countries(
            enriched
        )

        enriched_articles.append(enriched)

        time.sleep(REQUEST_DELAY)

    return enriched_articles


# =========================================================
# 키워드 분석
# =========================================================

def count_keywords(
    articles: list[dict[str, object]],
) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()

    for article in articles:
        text = " ".join(
            [
                str(article.get("title", "")),
                str(article.get("source", "")),
                str(article.get("description", "")),
                str(article.get("article_text", "")),
            ]
        ).lower()

        for keyword in KEYWORD_CANDIDATES:
            if keyword.lower() in text:
                counts[keyword] += 1

    return counts.most_common(10)


# =========================================================
# HTML 구성 요소
# =========================================================

def render_summary_items(
    summaries: object,
) -> str:
    if not isinstance(summaries, list):
        return (
            "<li>요약 내용을 생성하지 못했습니다.</li>"
        )

    items: list[str] = []

    for summary in summaries:
        cleaned = clean_text(str(summary))

        if not cleaned:
            continue

        items.append(
            f"<li>{html.escape(cleaned)}</li>"
        )

    if not items:
        return (
            "<li>요약 내용을 생성하지 못했습니다.</li>"
        )

    return "\n".join(items)


def render_category_sections(
    articles: list[dict[str, object]],
) -> str:
    categories = [
        "정책·ODA",
        "NGO·시민사회",
        "해외봉사",
        "인도적 지원",
    ]

    sections: list[str] = []

    for category in categories:
        matching_articles = [
            article
            for article in articles
            if article.get("category") == category
        ]

        matching_articles = matching_articles[
            :MAX_ARTICLES_PER_SECTION
        ]

        section_parts = [
            '<section class="brief-section">',
            (
                "<h2>■ "
                f"{html.escape(category)}"
                "</h2>"
            ),
        ]

        if not matching_articles:
            section_parts.append(
                '<p class="empty">'
                "관련 기사가 없습니다."
                "</p>"
            )

            section_parts.append("</section>")
            sections.append(
                "\n".join(section_parts)
            )
            continue

        grouped: dict[
            str,
            list[dict[str, object]],
        ] = defaultdict(list)

        for article in matching_articles:
            organization = str(
                article.get(
                    "organization",
                    "기타 기관",
                )
            )

            grouped[organization].append(article)

        for organization, org_articles in grouped.items():
            section_parts.append(
                "<h3>● "
                f"{html.escape(organization)}"
                "</h3>"
            )

            for article in org_articles:
                title = html.escape(
                    str(
                        article.get(
                            "title",
                            "제목 없음",
                        )
                    )
                )
                source = html.escape(
                    str(
                        article.get(
                            "source",
                            "출처 미확인",
                        )
                    )
                )
                summary_html = render_summary_items(
                    article.get("summary", [])
                )

                section_parts.append(
                    f"""
<article class="news-summary">
    <h4>{title}</h4>

    <ul>
        {summary_html}
    </ul>

    <div class="summary-source">
        출처: {source}
    </div>
</article>
"""
                )

        section_parts.append("</section>")

        sections.append(
            "\n".join(section_parts)
        )

    return "\n".join(sections)


def render_country_section(
    articles: list[dict[str, object]],
) -> str:
    country_articles: dict[
        str,
        list[dict[str, object]],
    ] = defaultdict(list)

    for article in articles:
        countries = article.get("countries", [])

        if not isinstance(countries, list):
            continue

        for country in countries:
            country_name = str(country).strip()

            if not country_name:
                continue

            country_articles[country_name].append(
                article
            )

    if not country_articles:
        return (
            '<p class="empty">'
            "확인된 국가명이 없습니다."
            "</p>"
        )

    sorted_countries = sorted(
        country_articles.items(),
        key=lambda item: len(item[1]),
        reverse=True,
    )

    country_blocks: list[str] = []

    for country, related_articles in sorted_countries:
        flag = COUNTRY_FLAGS.get(
            country,
            "🌍",
        )

        article_items: list[str] = []

        for article in related_articles:
            title = html.escape(
                str(
                    article.get(
                        "title",
                        "제목 없음",
                    )
                )
            )
            link = html.escape(
                str(
                    article.get(
                        "link",
                        "#",
                    )
                ),
                quote=True,
            )
            source = html.escape(
                str(
                    article.get(
                        "source",
                        "출처 미확인",
                    )
                )
            )
            category = html.escape(
                str(
                    article.get(
                        "category",
                        "기타",
                    )
                )
            )

            article_items.append(
                f"""
<li>
    <a
        href="{link}"
        target="_blank"
        rel="noopener noreferrer"
    >
        {title}
    </a>

    <div class="country-article-meta">
        {source} · {category}
    </div>
</li>
"""
            )

        article_list_html = "\n".join(
            article_items
        )

        country_blocks.append(
            f"""
<details class="country-item">
    <summary>
        <span>
            {flag} {html.escape(country)}
        </span>

        <strong>
            {len(related_articles)}건
        </strong>
    </summary>

    <ul class="country-article-list">
        {article_list_html}
    </ul>
</details>
"""
        )

    return "\n".join(country_blocks)


def render_keyword_section(
    articles: list[dict[str, object]],
) -> str:
    keyword_counts = count_keywords(articles)

    if not keyword_counts:
        return (
            '<p class="empty">'
            "추출된 키워드가 없습니다."
            "</p>"
        )

    keyword_items: list[str] = []

    for keyword, count in keyword_counts:
        keyword_items.append(
            f"""
<span class="keyword">
    {html.escape(keyword)}
    <small>{count}</small>
</span>
"""
        )

    return "\n".join(keyword_items)


def render_original_articles(
    articles: list[dict[str, object]],
) -> str:
    article_items: list[str] = []

    for article in articles:
        title = html.escape(
            str(
                article.get(
                    "title",
                    "제목 없음",
                )
            )
        )
        link = html.escape(
            str(
                article.get(
                    "link",
                    "#",
                )
            ),
            quote=True,
        )
        source = html.escape(
            str(
                article.get(
                    "source",
                    "출처 미확인",
                )
            )
        )
        category = html.escape(
            str(
                article.get(
                    "category",
                    "기타",
                )
            )
        )

        article_items.append(
            f"""
<li>
    <a
        href="{link}"
        target="_blank"
        rel="noopener noreferrer"
    >
        {title}
    </a>

    <div class="article-meta">
        {source} · {category}
    </div>
</li>
"""
        )

    return "\n".join(article_items)


# =========================================================
# 전체 HTML 생성
# CSS는 아래 템플릿 문자열 안에만 존재합니다.
# =========================================================

def create_html(
    articles: list[dict[str, object]],
) -> str:
    now = datetime.now(KST)

    category_counts = Counter(
        str(
            article.get(
                "category",
                "기타",
            )
        )
        for article in articles
    )

    extracted_count = sum(
        1
        for article in articles
        if article.get("article_text")
    )

    category_sections = render_category_sections(
        articles
    )
    country_section = render_country_section(
        articles
    )
    keyword_section = render_keyword_section(
        articles
    )
    original_articles = render_original_articles(
        articles
    )

    # f-string을 사용하지 않는 이유:
    # CSS의 { }가 Python 문법으로 해석되는 오류를 방지합니다.
    template = """<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>한국 국제개발협력 Daily Brief</title>

    <style>
        * {
            box-sizing: border-box;
        }

        html {
            scroll-behavior: smooth;
        }

        body {
            margin: 0;
            background: #ffffff;
            color: #222222;
            font-family:
                Pretendard,
                "Noto Sans KR",
                "Apple SD Gothic Neo",
                Arial,
                sans-serif;
            line-height: 1.75;
            word-break: keep-all;
        }

        .container {
            width: 100%;
            max-width: 1180px;
            margin: 0 auto;
            padding: 48px 24px 80px;
        }

        h1 {
            margin: 0 0 6px;
            font-size: 34px;
            line-height: 1.35;
        }

        .date {
            color: #666666;
            margin-bottom: 32px;
        }

        .divider {
            margin: 32px 0;
            border: 0;
            border-top: 1px solid #bfc5cc;
        }

        .summary {
            padding: 22px 24px;
            background: #f7f8fa;
            border-left: 5px solid #2457a6;
        }

        .summary h2 {
            margin-top: 0;
            font-size: 22px;
        }

        .summary ul {
            margin-bottom: 0;
        }

        .summary li {
            margin-bottom: 6px;
        }

        .brief-section {
            width: 100%;
            padding: 30px 0;
            border-bottom: 1px solid #dddddd;
        }

        .brief-section h2 {
            margin: 0 0 22px;
            color: #173f73;
            font-size: 23px;
        }

        .brief-section h3 {
            margin: 28px 0 12px;
            font-size: 19px;
        }

        .news-summary {
            width: 100%;
            max-width: 100%;
            margin-bottom: 24px;
            padding: 18px 20px;
            background: #fafafa;
            border: 1px solid #e0e3e7;
            overflow: visible;
        }

        .news-summary h4 {
            width: 100%;
            max-width: 100%;
            margin: 0 0 12px;
            font-size: 17px;
            line-height: 1.55;
            white-space: normal;
            overflow: visible;
            text-overflow: unset;
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        .news-summary ul {
            width: 100%;
            max-width: 100%;
            margin: 0;
            padding-left: 22px;
        }

        .news-summary li {
            width: 100%;
            max-width: 100%;
            margin-bottom: 9px;
            line-height: 1.8;
            white-space: normal;
            overflow: visible;
            text-overflow: unset;
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        .summary-source {
            margin-top: 12px;
            color: #777777;
            font-size: 13px;
        }

        .country-grid {
            display: grid;
            grid-template-columns: 1fr;
            gap: 10px;
        }

        .country-item {
            width: 100%;
            background: #f7f8fa;
            border: 1px solid #e0e3e7;
        }

        .country-item summary {
            display: grid;
            grid-template-columns: 1fr auto auto;
            align-items: center;
            gap: 12px;
            width: 100%;
            padding: 13px 15px;
            cursor: pointer;
            font-weight: 600;
            list-style: none;
        }

        .country-item summary::-webkit-details-marker {
            display: none;
        }

        .country-item summary::after {
            content: "＋";
            color: #2457a6;
            font-size: 18px;
        }

        .country-item[open] summary::after {
            content: "−";
        }

        .country-item[open] summary {
            background: #eef3f8;
        }

        .country-article-list {
            width: 100%;
            margin: 0;
            padding: 16px 24px 18px 44px;
            background: #ffffff;
            border-top: 1px solid #e0e3e7;
        }

        .country-article-list li {
            margin-bottom: 15px;
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        .country-article-list a {
            color: #1456a0;
            font-weight: 600;
            text-decoration: none;
        }

        .country-article-list a:hover {
            text-decoration: underline;
        }

        .country-article-meta {
            margin-top: 3px;
            color: #777777;
            font-size: 13px;
        }

        .keywords {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }

        .keyword {
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 7px 11px;
            background: #eef3f8;
            border-radius: 20px;
            color: #173f73;
            font-weight: 600;
        }

        .keyword small {
            color: #777777;
        }

        .articles {
            margin-top: 42px;
        }

        .articles h2 {
            padding-bottom: 12px;
            border-bottom: 2px solid #222222;
        }

        .articles li {
            margin-bottom: 17px;
            overflow-wrap: anywhere;
            word-break: break-word;
        }

        .articles a {
            color: #1456a0;
            font-weight: 600;
            text-decoration: none;
        }

        .articles a:hover {
            text-decoration: underline;
        }

        .article-meta {
            margin-top: 3px;
            color: #777777;
            font-size: 13px;
        }

        .empty {
            color: #777777;
        }

        .notice {
            margin-top: 35px;
            padding-top: 18px;
            border-top: 1px solid #dddddd;
            color: #777777;
            font-size: 13px;
        }

        @media (max-width: 640px) {
            .container {
                padding: 28px 16px 60px;
            }

            h1 {
                font-size: 27px;
            }

            .summary {
                padding: 18px;
            }

            .news-summary {
                padding: 15px;
            }

            .country-item summary {
                padding: 12px;
            }

            .country-article-list {
                padding: 14px 18px 16px 34px;
            }
        }
    </style>
</head>

<body>
    <main class="container">
        <header>
            <h1>한국 국제개발협력 Daily Brief</h1>

            <div class="date">
                __DATE__
            </div>
        </header>

        <hr class="divider">

        <section class="summary">
            <h2>오늘의 핵심</h2>

            <ul>
                <li>
                    국제개발협력 기사
                    <strong>__TOTAL_COUNT__건</strong>
                </li>

                <li>
                    기사 본문 추출 성공
                    <strong>__EXTRACTED_COUNT__건</strong>
                </li>

                <li>
                    정책·ODA 관련
                    <strong>__POLICY_COUNT__건</strong>
                </li>

                <li>
                    NGO 관련
                    <strong>__NGO_COUNT__건</strong>
                </li>

                <li>
                    해외봉사 관련
                    <strong>__VOLUNTEER_COUNT__건</strong>
                </li>

                <li>
                    인도적 지원 관련
                    <strong>__HUMANITARIAN_COUNT__건</strong>
                </li>
            </ul>
        </section>

        <hr class="divider">

        __CATEGORY_SECTIONS__

        <section class="brief-section">
            <h2>■ 국가별</h2>

            <p>
                국가명을 클릭하면 관련 기사목록이 펼쳐집니다.
            </p>

            <div class="country-grid">
                __COUNTRY_SECTION__
            </div>
        </section>

        <section class="brief-section">
            <h2>■ 오늘 많이 나온 키워드</h2>

            <div class="keywords">
                __KEYWORD_SECTION__
            </div>
        </section>

        <section class="articles">
            <h2>원문기사</h2>

            <ol>
                __ORIGINAL_ARTICLES__
            </ol>
        </section>

        <p class="notice">
            본 브리핑은 기사 본문에서 핵심 문장을 자동 선별한
            추출형 요약입니다. 언론사 접근 제한이나 페이지 구조에
            따라 일부 기사는 RSS 설명 또는 안내 문구로 표시될 수
            있습니다. 중요한 내용은 원문과 관계기관의 공식 발표를
            함께 확인하시기 바랍니다.
        </p>
    </main>
</body>
</html>
"""

    replacements = {
        "__DATE__": now.strftime("%Y.%m.%d"),
        "__TOTAL_COUNT__": str(len(articles)),
        "__EXTRACTED_COUNT__": str(extracted_count),
        "__POLICY_COUNT__": str(
            category_counts.get(
                "정책·ODA",
                0,
            )
        ),
        "__NGO_COUNT__": str(
            category_counts.get(
                "NGO·시민사회",
                0,
            )
        ),
        "__VOLUNTEER_COUNT__": str(
            category_counts.get(
                "해외봉사",
                0,
            )
        ),
        "__HUMANITARIAN_COUNT__": str(
            category_counts.get(
                "인도적 지원",
                0,
            )
        ),
        "__CATEGORY_SECTIONS__": category_sections,
        "__COUNTRY_SECTION__": country_section,
        "__KEYWORD_SECTION__": keyword_section,
        "__ORIGINAL_ARTICLES__": original_articles,
    }

    for placeholder, value in replacements.items():
        template = template.replace(
            placeholder,
            value,
        )

    return template


# =========================================================
# README 생성
# =========================================================

def create_readme(
    articles: list[dict[str, object]],
) -> str:
    now = datetime.now(KST)

    return "\n".join(
        [
            "# 한국 국제개발협력 Daily Brief",
            "",
            (
                "> 최근 업데이트: "
                f"{now:%Y-%m-%d %H:%M} KST"
            ),
            "",
            (
                "GitHub Pages에서 기사별 핵심 요약, "
                "분야별 분류 및 국가별 기사목록을 "
                "확인할 수 있습니다."
            ),
            "",
            f"- 전체 기사: {len(articles)}건",
            "",
        ]
    )


# =========================================================
# 실행
# =========================================================

def main() -> None:
    try:
        print("1. 뉴스 수집 시작")

        articles = collect_news()

        print(
            f"2. RSS 기사 "
            f"{len(articles)}건 수집 완료"
        )

        if not articles:
            raise RuntimeError(
                "수집된 뉴스가 없습니다. "
                "RSS 검색 결과를 확인하세요."
            )

        enriched_articles = enrich_articles(
            articles
        )

        print(
            "3. 기사 본문 추출 및 요약 완료"
        )

        print("4. HTML 생성 시작")

        page_html = create_html(
            enriched_articles
        )

        print("5. README 생성 시작")

        readme_content = create_readme(
            enriched_articles
        )

        with open(
            "index.html",
            "w",
            encoding="utf-8",
        ) as file:
            file.write(page_html)

        with open(
            "README.md",
            "w",
            encoding="utf-8",
        ) as file:
            file.write(readme_content)

        print(
            "6. index.html 및 README.md 생성 완료"
        )

    except Exception as error:
        print("")
        print("=" * 60)
        print("작업 중 오류 발생")
        print(
            f"오류 종류: "
            f"{type(error).__name__}"
        )
        print(f"오류 내용: {error}")
        print("=" * 60)

        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()
