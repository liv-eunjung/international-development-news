import html
import math
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser
import requests
import trafilatura


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

# 기사 한 건당 최대 본문 길이
MAX_ARTICLE_TEXT_LENGTH = 10000

# 분야별 표시할 기사 수
MAX_ARTICLES_PER_SECTION = 6

REQUEST_TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0 Safari/537.36"
    )
}


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
    "KOICA": ["koica", "코이카", "한국국제협력단"],
    "KCOC": ["kcoc", "국제개발협력민간협의회"],
    "OECD DAC": ["oecd", "dac"],
    "외교부": ["외교부"],
    "국무조정실": ["국무조정실"],
    "World Bank": ["world bank", "세계은행"],
    "UNDP": ["undp", "유엔개발계획"],
    "UNICEF": ["unicef", "유니세프"],
    "WHO": ["who", "세계보건기구"],
    "USAID": ["usaid"],
    "JICA": ["jica", "일본국제협력기구"],
    "ADB": ["adb", "아시아개발은행"],
    "Peace Corps": ["peace corps", "평화봉사단"],
}


COUNTRY_RULES = {
    "대한민국": ["한국", "대한민국", "코리아"],
    "캄보디아": ["캄보디아", "cambodia"],
    "르완다": ["르완다", "rwanda"],
    "우간다": ["우간다", "uganda"],
    "페루": ["페루", "peru"],
    "케냐": ["케냐", "kenya"],
    "에티오피아": ["에티오피아", "ethiopia"],
    "라오스": ["라오스", "laos"],
    "베트남": ["베트남", "vietnam"],
    "필리핀": ["필리핀", "philippines"],
    "몽골": ["몽골", "mongolia"],
    "네팔": ["네팔", "nepal"],
    "방글라데시": ["방글라데시", "bangladesh"],
    "스리랑카": ["스리랑카", "sri lanka"],
    "인도네시아": ["인도네시아", "indonesia"],
    "탄자니아": ["탄자니아", "tanzania"],
    "가나": ["가나", "ghana"],
    "세네갈": ["세네갈", "senegal"],
    "모로코": ["모로코", "morocco"],
    "요르단": ["요르단", "jordan"],
    "우크라이나": ["우크라이나", "ukraine"],
    "팔레스타인": ["팔레스타인", "palestine", "가자"],
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
    "및",
    "등",
    "의",
    "가",
    "이",
    "은",
    "는",
    "을",
    "를",
    "에",
    "와",
    "과",
    "로",
    "으로",
    "에서",
    "한",
    "또한",
    "것으로",
    "밝혔다",
    "예정이다",
}


def google_news_rss_url(keyword: str) -> str:
    encoded_keyword = quote(keyword)

    return (
        "https://news.google.com/rss/search"
        f"?q={encoded_keyword}"
        "&hl=ko"
        "&gl=KR"
        "&ceid=KR:ko"
    )


def clean_text(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value or "")
    value = value.replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", value).strip()


def normalize_title(title: str) -> str:
    normalized = title.lower()
    normalized = re.sub(r"\s*-\s*[^-]+$", "", normalized)
    normalized = re.sub(r"[^가-힣a-z0-9]", "", normalized)
    return normalized


def collect_news() -> list[dict[str, str]]:
    articles: list[dict[str, str]] = []
    seen_titles: set[str] = set()

    for keyword in SEARCH_KEYWORDS:
        feed = feedparser.parse(google_news_rss_url(keyword))
        keyword_count = 0

        for entry in feed.entries:
            title = clean_text(entry.get("title", ""))
            link = entry.get("link", "").strip()

            source_data = entry.get("source", {})
            source = clean_text(
                source_data.get("title", "출처 미확인")
            )

            description = clean_text(
                entry.get("summary", "")
            )

            if not title or not link:
                continue

            normalized = normalize_title(title)

            if not normalized or normalized in seen_titles:
                continue

            articles.append(
                {
                    "title": title,
                    "link": link,
                    "source": source,
                    "description": description,
                    "search_keyword": keyword,
                    "published": clean_text(
                        entry.get("published", "")
                    ),
                }
            )

            seen_titles.add(normalized)
            keyword_count += 1

            if keyword_count >= MAX_ARTICLES_PER_KEYWORD:
                break

            if len(articles) >= MAX_TOTAL_ARTICLES:
                return articles

    return articles


def fetch_article_text(url: str) -> tuple[str, str]:
    """
    기사 URL에 접속해 최종 URL과 본문을 반환합니다.
    본문 추출 실패 시 빈 문자열을 반환합니다.
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
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            favor_precision=True,
        )

        if not extracted:
            return final_url, ""

        extracted = clean_text(extracted)

        return (
            final_url,
            extracted[:MAX_ARTICLE_TEXT_LENGTH],
        )

    except Exception as error:
        print(
            f"본문 추출 실패: {url} "
            f"({type(error).__name__})"
        )
        return url, ""


def split_sentences(text: str) -> list[str]:
    text = clean_text(text)

    sentences = re.split(
        r"(?<=[.!?。！？])\s+|(?<=다\.)\s+",
        text,
    )

    result = []

    for sentence in sentences:
        sentence = sentence.strip()

        if len(sentence) < 25:
            continue

        if len(sentence) > 300:
            sentence = sentence[:300].rstrip() + "…"

        result.append(sentence)

    return result


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


def summarize_text(
    title: str,
    text: str,
    fallback: str,
    sentence_count: int = 3,
) -> list[str]:
    """
    단어 출현 빈도를 기반으로 핵심 문장을 선별합니다.
    AI 생성 요약이 아니라 기사 본문 문장 중 중요 문장을 추출합니다.
    """
    source_text = text or fallback

    sentences = split_sentences(source_text)

    if not sentences:
        return [title]

    all_words = tokenize(
        f"{title} {source_text}"
    )

    if not all_words:
        return sentences[:sentence_count]

    frequencies = Counter(all_words)
    max_frequency = max(frequencies.values())

    normalized_frequencies = {
        word: count / max_frequency
        for word, count in frequencies.items()
    }

    title_words = set(tokenize(title))

    scored_sentences = []

    for index, sentence in enumerate(sentences):
        words = tokenize(sentence)

        if not words:
            continue

        frequency_score = sum(
            normalized_frequencies.get(word, 0)
            for word in words
        ) / math.sqrt(len(words))

        title_score = sum(
            1 for word in words
            if word in title_words
        )

        position_score = max(
            0,
            1 - index * 0.05,
        )

        total_score = (
            frequency_score
            + title_score * 0.7
            + position_score * 0.3
        )

        scored_sentences.append(
            (index, total_score, sentence)
        )

    selected = sorted(
        scored_sentences,
        key=lambda item: item[1],
        reverse=True,
    )[:sentence_count]

    selected = sorted(
        selected,
        key=lambda item: item[0],
    )

    summaries = [
        sentence
        for _, _, sentence in selected
    ]

    return summaries or sentences[:sentence_count]


def contains_any(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(
        keyword.lower() in lowered
        for keyword in keywords
    )


def classify_category(article: dict[str, str]) -> str:
    text = (
        f"{article['title']} "
        f"{article['source']} "
        f"{article['description']} "
        f"{article['search_keyword']}"
    )

    scores = {}

    for category, keywords in CATEGORY_RULES.items():
        scores[category] = sum(
            1
            for keyword in keywords
            if keyword.lower() in text.lower()
        )

    highest_category = max(scores, key=scores.get)

    if scores[highest_category] == 0:
        return "정책·ODA"

    return highest_category


def detect_organization(article: dict[str, str]) -> str:
    text = (
        f"{article['title']} "
        f"{article['source']} "
        f"{article['description']}"
    )

    for organization, keywords in ORGANIZATION_RULES.items():
        if contains_any(text, keywords):
            return organization

    if article["source"] != "출처 미확인":
        return article["source"]

    return "기타 기관"


def detect_countries(article: dict[str, str]) -> list[str]:
    text = (
        f"{article['title']} "
        f"{article['description']} "
        f"{article.get('article_text', '')}"
    ).lower()

    countries = []

    for country, keywords in COUNTRY_RULES.items():
        if any(
            keyword.lower() in text
            for keyword in keywords
        ):
            countries.append(country)

    return countries


def enrich_articles(
    articles: list[dict[str, str]],
) -> list[dict[str, object]]:
    enriched = []

    for index, article in enumerate(articles, start=1):
        print(
            f"기사 본문 수집 중 "
            f"({index}/{len(articles)}): "
            f"{article['title'][:40]}"
        )

        final_url, article_text = fetch_article_text(
            article["link"]
        )

        summary = summarize_text(
            title=article["title"],
            text=article_text,
            fallback=article["description"],
            sentence_count=3,
        )

        enriched_article = dict(article)
        enriched_article["link"] = final_url
        enriched_article["article_text"] = article_text
        enriched_article["summary"] = summary
        enriched_article["category"] = classify_category(
            article
        )
        enriched_article["organization"] = (
            detect_organization(article)
        )
        enriched_article["countries"] = detect_countries(
            enriched_article
        )

        enriched.append(enriched_article)

        # 언론사 서버에 과도한 요청을 보내지 않도록 잠시 대기
        time.sleep(0.4)

    return enriched


def count_keywords(
    articles: list[dict[str, object]],
) -> list[tuple[str, int]]:
    counts = Counter()

    for article in articles:
        text = (
            f"{article['title']} "
            f"{article['source']} "
            f"{article.get('article_text', '')}"
        ).lower()

        for keyword in KEYWORD_CANDIDATES:
            if keyword.lower() in text:
                counts[keyword] += 1

    return counts.most_common(10)


def render_category_sections(
    articles: list[dict[str, object]],
) -> str:
    categories = [
        "정책·ODA",
        "NGO·시민사회",
        "해외봉사",
        "인도적 지원",
    ]

    output = []

    for category in categories:
        category_articles = [
            article
            for article in articles
            if article["category"] == category
        ][:MAX_ARTICLES_PER_SECTION]

        output.append(
            f"""
            <section class="brief-section">
                <h2>■ {html.escape(category)}</h2>
            """
        )

        if not category_articles:
            output.append(
                '<p class="empty">'
                '관련 기사가 없습니다.'
                '</p>'
            )
        else:
            grouped = defaultdict(list)

            for article in category_articles:
                grouped[
                    str(article["organization"])
                ].append(article)

            for organization, org_articles in grouped.items():
                output.append(
                    f"<h3>● {html.escape(organization)}</h3>"
                )

                for article in org_articles:
                    title = html.escape(
                        str(article["title"])
                    )
                    source = html.escape(
                        str(article["source"])
                    )

                    summary_items = "".join(
                        f"<li>{html.escape(str(item))}</li>"
                        for item in article["summary"]
                    )

                    output.append(
                        f"""
                        <article class="news-summary">
                            <h4>{title}</h4>

                            <ul>
                                {summary_items}
                            </ul>

                            <div class="summary-source">
                                출처: {source}
                            </div>
                        </article>
                        """
                    )

        output.append("</section>")

    return "\n".join(output)


def render_country_section(
    articles: list[dict[str, object]],
) -> str:
    country_counts = Counter()

    for article in articles:
        for country in article["countries"]:
            country_counts[str(country)] += 1

    if not country_counts:
        return (
            '<p class="empty">'
            '확인된 국가명이 없습니다.'
            '</p>'
        )

    items = []

    for country, count in country_counts.most_common(12):
        flag = COUNTRY_FLAGS.get(country, "🌍")

        items.append(
            f"""
            <div class="country-item">
                <span>
                    {flag} {html.escape(country)}
                </span>
                <strong>{count}건</strong>
            </div>
            """
        )

    return "\n".join(items)


def render_keyword_section(
    articles: list[dict[str, object]],
) -> str:
    keyword_counts = count_keywords(articles)

    if not keyword_counts:
        return (
            '<p class="empty">'
            '추출된 키워드가 없습니다.'
            '</p>'
        )

    return "\n".join(
        f"""
        <span class="keyword">
            {html.escape(keyword)}
            <small>{count}</small>
        </span>
        """
        for keyword, count in keyword_counts
    )


def render_original_articles(
    articles: list[dict[str, object]],
) -> str:
    items = []

    for article in articles:
        title = html.escape(str(article["title"]))
        link = html.escape(
            str(article["link"]),
            quote=True,
        )
        source = html.escape(str(article["source"]))
        category = html.escape(
            str(article["category"])
        )

        items.append(
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

    return "\n".join(items)


def create_html(
    articles: list[dict[str, object]],
) -> str:
    now = datetime.now(KST)

    category_counts = Counter(
        str(article["category"])
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

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>한국 국제개발협력 Daily Brief</title>

    <style>
        * {{
            box-sizing: border-box;
        }}

        body {{
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
        }}

        .container {{
            max-width: 980px;
            margin: 0 auto;
            padding: 48px 24px 80px;
        }}

        h1 {{
            margin: 0 0 6px;
            font-size: 34px;
        }}

        .date {{
            color: #666666;
            margin-bottom: 32px;
        }}

        .divider {{
            margin: 32px 0;
            border: 0;
            border-top: 1px solid #bfc5cc;
        }}

        .summary {{
            padding: 22px 24px;
            background: #f7f8fa;
            border-left: 5px solid #2457a6;
        }}

        .summary h2 {{
            margin-top: 0;
            font-size: 22px;
        }}

        .summary ul {{
            margin-bottom: 0;
        }}

        .brief-section {{
            padding: 30px 0;
            border-bottom: 1px solid #dddddd;
        }}

        .brief-section h2 {{
            margin: 0 0 22px;
            color: #173f73;
            font-size: 23px;
        }}

        .brief-section h3 {{
            margin: 28px 0 12px;
            font-size: 19px;
        }}

        .news-summary {{
            margin-bottom: 24px;
            padding: 18px 20px;
            background: #fafafa;
            border: 1px solid #e0e3e7;
        }}

        .news-summary h4 {{
            margin: 0 0 12px;
            font-size: 17px;
            line-height: 1.55;
        }}

        .news-summary ul {{
            margin: 0;
            padding-left: 22px;
        }}

        .news-summary li {{
            margin-bottom: 8px;
        }}

        .summary-source {{
            margin-top: 12px;
            color: #777777;
            font-size: 13px;
        }}

        .country-grid {{
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(180px, 1fr));
            gap: 10px;
        }}

        .country-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px 12px;
            background: #f7f8fa;
            border: 1px solid #e0e3e7;
        }}

        .keywords {{
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }}

        .keyword {{
            display: inline-flex;
            gap: 6px;
            align-items: center;
            padding: 7px 11px;
            background: #eef3f8;
            border-radius: 20px;
            color: #173f73;
            font-weight: 600;
        }}

        .keyword small {{
            color: #777777;
        }}

        .articles {{
            margin-top: 42px;
        }}

        .articles h2 {{
            padding-bottom: 12px;
            border-bottom: 2px solid #222222;
        }}

        .articles li {{
            margin-bottom: 17px;
        }}

        .articles a {{
            color: #1456a0;
            font-weight: 600;
            text-decoration: none;
        }}

        .articles a:hover {{
            text-decoration: underline;
        }}

        .article-meta {{
            margin-top: 3px;
            color: #777777;
            font-size: 13px;
        }}

        .empty {{
            color: #777777;
        }}

        .notice {{
            margin-top: 35px;
            padding-top: 18px;
            border-top: 1px solid #dddddd;
            color: #777777;
            font-size: 13px;
        }}

        @media (max-width: 640px) {{
            .container {{
                padding: 28px 18px 60px;
            }}

            h1 {{
                font-size: 27px;
            }}

            .news-summary {{
                padding: 15px;
            }}
        }}
    </style>
</head>

<body>
    <main class="container">
        <header>
            <h1>한국 국제개발협력 Daily Brief</h1>
            <div class="date">
                {now:%Y.%m.%d}
            </div>
        </header>

        <hr class="divider">

        <section class="summary">
            <h2>오늘의 핵심</h2>

            <ul>
                <li>
                    국제개발협력 기사
                    {len(articles)}건
                </li>

                <li>
                    기사 본문 추출 성공
                    {extracted_count}건
                </li>

                <li>
                    정책·ODA 관련
                    {category_counts.get("정책·ODA", 0)}건
                </li>

                <li>
                    NGO 관련
                    {category_counts.get("NGO·시민사회", 0)}건
                </li>

                <li>
                    해외봉사 관련
                    {category_counts.get("해외봉사", 0)}건
                </li>

                <li>
                    인도적 지원 관련
                    {category_counts.get("인도적 지원", 0)}건
                </li>
            </ul>
        </section>

        <hr class="divider">

        {category_sections}

        <section class="brief-section">
            <h2>■ 국가별</h2>

            <div class="country-grid">
                {country_section}
            </div>
        </section>

        <section class="brief-section">
            <h2>■ 오늘 많이 나온 키워드</h2>

            <div class="keywords">
                {keyword_section}
            </div>
        </section>

        <section class="articles">
            <h2>원문기사</h2>

            <ol>
                {original_articles}
            </ol>
        </section>

        <p class="notice">
            본 브리핑은 기사 본문에서 핵심 문장을 자동 선별한
            추출형 요약입니다. 언론사 접근 제한이나 페이지 구조에
            따라 일부 기사는 RSS 설명 또는 기사 제목을 기준으로
            표시될 수 있습니다. 중요한 내용은 원문과 공식 발표를
            함께 확인하시기 바랍니다.
        </p>
    </main>
</body>
</html>
"""


def create_readme(
    articles: list[dict[str, object]],
) -> str:
    now = datetime.now(KST)

    lines = [
        "# 한국 국제개발협력 Daily Brief",
        "",
        f"> 최근 업데이트: "
        f"{now:%Y-%m-%d %H:%M} KST",
        "",
        "GitHub Pages에서 기사별 핵심 요약과 "
        "최신 브리핑을 확인할 수 있습니다.",
        "",
        f"- 전체 기사: {len(articles)}건",
        "",
    ]

    return "\n".join(lines)


def main() -> None:
    print("1. 뉴스 수집 시작")

    articles = collect_news()

    print(f"2. RSS 기사 {len(articles)}건 수집 완료")

    if not articles:
        raise RuntimeError(
            "수집된 뉴스가 없습니다. "
            "RSS 검색 결과를 확인하세요."
        )

    enriched_articles = enrich_articles(articles)

    print("3. 기사 본문 추출 및 요약 완료")

    page_html = create_html(enriched_articles)
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

    print("4. index.html과 README.md 생성 완료")


if __name__ == "__main__":
    main()
