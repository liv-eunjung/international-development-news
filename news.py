from __future__ import annotations

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
    "국제개발협력",
    "공적개발원조 ODA",
    "KOICA",
    "KCOC",
    "국제개발 NGO",
    "해외봉사단",
    "인도적 지원",
    "개발협력 시민사회",
]

MAX_ARTICLES_PER_KEYWORD = 5
MAX_TOTAL_ARTICLES = 24
MAX_ARTICLES_PER_SECTION = 8
MAX_ARTICLE_TEXT_LENGTH = 12000
REQUEST_TIMEOUT = 12

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
    "수단": ["수단", "sudan"],
    "미얀마": ["미얀마", "myanmar"],
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
    "수단": "🇸🇩",
    "미얀마": "🇲🇲",
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
def format_published_date(published: str) -> str:
    """Google News RSS 게시일을 YYYY.MM.DD 형식으로 변환합니다."""

    if not published:
        return "게시일 미확인"

    try:
        parsed = datetime.strptime(
            published,
            "%a, %d %b %Y %H:%M:%S %Z",
        )

        parsed = parsed.replace(
            tzinfo=timezone.utc
        ).astimezone(KST)

        return parsed.strftime(
            "%Y.%m.%d"
        )

    except ValueError:
        pass

    # 일부 RSS에서 timezone 표기가 다른 경우 대비
    try:
        parsed = datetime.strptime(
            published,
            "%a, %d %b %Y %H:%M:%S %z",
        )

        parsed = parsed.astimezone(
            KST
        )

        return parsed.strftime(
            "%Y.%m.%d"
        )

    except ValueError:
        return "게시일 미확인"


def collect_news() -> list[dict[str, str]]:
    articles = []
    seen_titles = set()

    for keyword in SEARCH_KEYWORDS:
        feed = feedparser.parse(
            google_news_rss_url(keyword)
        )

        keyword_count = 0

        for entry in feed.entries:
            title = clean_text(
                entry.get("title", "")
            )

            link = entry.get(
                "link",
                "",
            ).strip()

            source_data = entry.get(
                "source",
                {},
            )

            source = clean_text(
                source_data.get(
                    "title",
                    "출처 미확인",
                )
            )

            description = clean_text(
                entry.get(
                    "summary",
                    "",
                )
            )

            if not title or not link:
                continue

            normalized = normalize_title(
                title
            )

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
                    "published": clean_text(
                        entry.get(
                            "published",
                            "",
                        )
                    ),
                }
            )

            seen_titles.add(
                normalized
            )

            keyword_count += 1

            if keyword_count >= MAX_ARTICLES_PER_KEYWORD:
                break

            if len(articles) >= MAX_TOTAL_ARTICLES:
                return articles

    return articles


def fetch_article_text(
    url: str,
) -> tuple[str, str]:

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

        extracted = clean_text(
            extracted
        )

        return (
            final_url,
            extracted[
                :MAX_ARTICLE_TEXT_LENGTH
            ],
        )

    except Exception as error:
        print(
            f"본문 추출 실패: "
            f"{type(error).__name__}"
        )

        return url, ""


def split_sentences(
    text: str,
) -> list[str]:

    text = clean_text(text)

    sentences = re.split(
        r"(?<=[.!?。！？])\s+",
        text,
    )

    result = []

    for sentence in sentences:
        sentence = sentence.strip()

        if len(sentence) < 25:
            continue

        result.append(
            sentence
        )

    return result


def tokenize(
    text: str,
) -> list[str]:

    words = re.findall(
        r"[가-힣]{2,}|[A-Za-z]{3,}",
        text.lower(),
    )

    return [
        word
        for word in words
        if word not in STOPWORDS
    ]


def summary_is_duplicate_of_title(
    summary: str,
    title: str,
) -> bool:

    summary_key = normalize_title(
        summary
    )

    title_key = normalize_title(
        title
    )

    if not summary_key:
        return False

    if summary_key == title_key:
        return True

    shorter = min(
        len(summary_key),
        len(title_key),
    )

    longer = max(
        len(summary_key),
        len(title_key),
    )

    if longer == 0:
        return False

    if shorter / longer >= 0.85:
        if summary_key in title_key:
            return True

        if title_key in summary_key:
            return True

    return False


def summarize_text(
    title: str,
    text: str,
    fallback: str,
    sentence_count: int = 3,
) -> list[str]:

    source_text = text or fallback

    sentences = split_sentences(
        source_text
    )

    if not sentences:
        return []

    all_words = tokenize(
        f"{title} {source_text}"
    )

    if not all_words:
        candidates = sentences[
            :sentence_count
        ]

    else:
        frequencies = Counter(
            all_words
        )

        max_frequency = max(
            frequencies.values()
        )

        normalized_frequencies = {
            word: count / max_frequency
            for word, count
            in frequencies.items()
        }

        title_words = set(
            tokenize(title)
        )

        scored_sentences = []

        for index, sentence in enumerate(
            sentences
        ):
            words = tokenize(
                sentence
            )

            if not words:
                continue

            frequency_score = sum(
                normalized_frequencies.get(
                    word,
                    0,
                )
                for word in words
            ) / math.sqrt(
                len(words)
            )

            title_score = sum(
                1
                for word in words
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
                (
                    index,
                    total_score,
                    sentence,
                )
            )

        selected = sorted(
            scored_sentences,
            key=lambda item: item[1],
            reverse=True,
        )[
            :sentence_count
        ]

        selected = sorted(
            selected,
            key=lambda item: item[0],
        )

        candidates = [
            sentence
            for _, _, sentence
            in selected
        ]

    cleaned = [
        sentence
        for sentence in candidates
        if not summary_is_duplicate_of_title(
            sentence,
            title,
        )
    ]

    return cleaned[
        :sentence_count
    ]


def contains_any(
    text: str,
    keywords: list[str],
) -> bool:

    lowered = text.lower()

    return any(
        keyword.lower() in lowered
        for keyword in keywords
    )


def classify_category(
    article: dict[str, str],
) -> str:

    text = (
        f"{article['title']} "
        f"{article['source']} "
        f"{article['description']} "
        f"{article['search_keyword']}"
    ).lower()

    scores = {
        category: sum(
            keyword.lower() in text
            for keyword in keywords
        )
        for category, keywords
        in CATEGORY_RULES.items()
    }

    best_score = max(
        scores.values(),
        default=0,
    )

    if best_score == 0:
        return "정책·ODA"

    priority = [
        "인도적 지원",
        "해외봉사",
        "NGO·시민사회",
        "정책·ODA",
    ]

    for category in priority:
        if scores.get(
            category,
            0,
        ) == best_score:
            return category

    return "정책·ODA"


def detect_organization(
    article: dict[str, str],
) -> str:

    text = (
        f"{article['title']} "
        f"{article['source']} "
        f"{article['description']}"
    )

    for organization, keywords in ORGANIZATION_RULES.items():
        if contains_any(
            text,
            keywords,
        ):
            return organization

    if article["source"] != "출처 미확인":
        return article["source"]

    return "기타 기관"


def detect_countries(
    article: dict[str, object],
) -> list[str]:

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
            countries.append(
                country
            )

    return countries


def enrich_articles(
    articles: list[dict[str, str]],
) -> list[dict[str, object]]:

    enriched = []

    for index, article in enumerate(
        articles,
        start=1,
    ):

        print(
            f"기사 처리 중 "
            f"({index}/{len(articles)}): "
            f"{article['title'][:50]}"
        )

        (
            final_url,
            article_text,
        ) = fetch_article_text(
            article["link"]
        )

        summary = summarize_text(
            title=article["title"],
            text=article_text,
            fallback=article["description"],
            sentence_count=3,
        )

        enriched_article = dict(
            article
        )

        enriched_article[
            "link"
        ] = final_url

        enriched_article[
            "article_text"
        ] = article_text

        enriched_article[
            "summary"
        ] = summary

        enriched_article[
            "category"
        ] = classify_category(
            article
        )

        enriched_article[
            "organization"
        ] = detect_organization(
            article
        )

        enriched_article[
            "countries"
        ] = detect_countries(
            enriched_article
        )

        enriched.append(
            enriched_article
        )

        time.sleep(
            0.2
        )

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
                counts[
                    keyword
                ] += 1

    return counts.most_common(
        10
    )


def render_article_card(
    article: dict[str, object],
) -> str:

    title = html.escape(
        str(
            article["title"]
        )
    )

    link = html.escape(
        str(
            article["link"]
        ),
        quote=True,
    )

    source = html.escape(
        str(
            article["source"]
        )
    )

    summary = article.get(
        "summary",
        [],
    )

    summary_html = ""

    if isinstance(
        summary,
        list,
    ) and summary:

        items = "".join(
            f"<li>{html.escape(str(item))}</li>"
            for item in summary
        )

        summary_html = (
            f"<ul>{items}</ul>"
        )

    # 핵심:
    # 기사 제목 자체가 클릭 가능한 링크입니다.
    return f"""
<article class="news-summary">

    <h4>
        <a
            class="article-title-link"
            href="{link}"
            target="_blank"
            rel="noopener noreferrer"
        >
            {title}
        </a>
    </h4>

    {summary_html}

    <div class="summary-source">
        출처: {source}
    </div>

</article>
"""


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
        ][
            :MAX_ARTICLES_PER_SECTION
        ]

        output.append(
            f"""
<section class="brief-section">

    <h2>
        ■ {html.escape(category)}
    </h2>
"""
        )

        if not category_articles:
            output.append(
                '<p class="empty">'
                '관련 기사가 없습니다.'
                '</p>'
            )

        else:
            grouped = defaultdict(
                list
            )

            for article in category_articles:
                grouped[
                    str(
                        article["organization"]
                    )
                ].append(
                    article
                )

            for organization, org_articles in grouped.items():

                output.append(
                    f"""
<h3>
    ● {html.escape(organization)}
</h3>
"""
                )

                for article in org_articles:
                    output.append(
                        render_article_card(
                            article
                        )
                    )

        output.append(
            "</section>"
        )

    return "\n".join(
        output
    )


def render_country_section(
    articles: list[dict[str, object]],
) -> str:

    country_articles = defaultdict(
        list
    )

    for article in articles:

        countries = article.get(
            "countries",
            [],
        )

        if not isinstance(
            countries,
            list,
        ):
            continue

        for country in countries:
            country_articles[
                str(country)
            ].append(
                article
            )

    if not country_articles:
        return (
            '<p class="empty">'
            '확인된 국가명이 없습니다.'
            '</p>'
        )

    items = []

    sorted_countries = sorted(
        country_articles.items(),
        key=lambda item: (
            -len(item[1]),
            item[0],
        ),
    )[
        :12
    ]

    for country, country_news in sorted_countries:

        flag = COUNTRY_FLAGS.get(
            country,
            "",
        )

        article_items = []

        for article in country_news:

            title = html.escape(
                str(
                    article["title"]
                )
            )

            link = html.escape(
                str(
                    article["link"]
                ),
                quote=True,
            )

            source = html.escape(
                str(
                    article["source"]
                )
            )

            category = html.escape(
                str(
                    article["category"]
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

        items.append(
            f"""
<details class="country-item">

    <summary>

        <span>
            {flag} {html.escape(country)}
        </span>

        <strong>
            {len(country_news)}건
        </strong>

    </summary>

    <ul class="country-article-list">
        {''.join(article_items)}
    </ul>

</details>
"""
        )

    return "\n".join(
        items
    )


def render_keyword_section(
    articles: list[dict[str, object]],
) -> str:

    keyword_counts = count_keywords(
        articles
    )

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
    <small>
        {count}
    </small>
</span>
"""
        for keyword, count
        in keyword_counts
    )


# =========================================================
# 중요:
# CSS가 포함된 부분은 f-string이 아닙니다.
# 따라서 CSS의 { }를 {{ }}로 바꿀 필요가 없습니다.
# =========================================================

HTML_HEAD = """<!DOCTYPE html>

<html lang="ko">

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>
        한국 국제개발협력 Daily Brief
    </title>


    <style>

        * {
            box-sizing: border-box;
        }


        html {
            scroll-behavior: smooth;
        }


        body {

            margin: 0;

            background:
                #ffffff;

            color:
                #222222;

            font-family:
                Pretendard,
                "Noto Sans KR",
                "Apple SD Gothic Neo",
                Arial,
                sans-serif;

            line-height:
                1.75;

            word-break:
                keep-all;
        }


        .container {

            width:
                100%;

            max-width:
                1180px;

            margin:
                0 auto;

            padding:
                48px 24px 80px;
        }


        h1 {

            margin:
                0 0 6px;

            font-size:
                34px;

            line-height:
                1.35;
        }


        .date {

            color:
                #666666;

            margin-bottom:
                32px;
        }


        .divider {

            margin:
                32px 0;

            border:
                0;

            border-top:
                1px solid #bfc5cc;
        }


        .summary {

            padding:
                22px 24px;

            background:
                #f7f8fa;

            border-left:
                5px solid #2457a6;
        }


        .summary h2 {

            margin-top:
                0;

            font-size:
                22px;
        }


        .summary ul {

            margin-bottom:
                0;
        }


        .summary li {

            margin-bottom:
                6px;
        }


        .brief-section {

            width:
                100%;

            padding:
                30px 0;

            border-bottom:
                1px solid #dddddd;
        }


        .brief-section h2 {

            margin:
                0 0 22px;

            color:
                #173f73;

            font-size:
                23px;
        }


        .brief-section h3 {

            margin:
                28px 0 12px;

            font-size:
                19px;
        }


        .news-summary {

            width:
                100%;

            margin-bottom:
                24px;

            padding:
                18px 20px;

            background:
                #fafafa;

            border:
                1px solid #e0e3e7;
        }


        .news-summary h4 {

            width:
                100%;

            margin:
                0 0 12px;

            font-size:
                17px;

            line-height:
                1.55;

            overflow-wrap:
                anywhere;

            word-break:
                break-word;
        }


        .article-title-link {

            color:
                #222222;

            text-decoration:
                none;

            font-weight:
                700;
        }


        .article-title-link:hover {

            color:
                #1456a0;

            text-decoration:
                underline;
        }


        .news-summary ul {

            width:
                100%;

            margin:
                0;

            padding-left:
                22px;
        }


        .news-summary li {

            margin-bottom:
                9px;

            line-height:
                1.8;

            overflow-wrap:
                anywhere;

            word-break:
                break-word;
        }


        .summary-source {

            margin-top:
                12px;

            color:
                #777777;

            font-size:
                13px;
        }


        .country-grid {

            display:
                grid;

            grid-template-columns:
                1fr;

            gap:
                10px;
        }


        .country-item {

            width:
                100%;

            background:
                #f7f8fa;

            border:
                1px solid #e0e3e7;
        }


        .country-item summary {

            display:
                grid;

            grid-template-columns:
                1fr auto auto;

            align-items:
                center;

            gap:
                12px;

            width:
                100%;

            padding:
                13px 15px;

            cursor:
                pointer;

            font-weight:
                600;

            list-style:
                none;
        }


        .country-item summary::-webkit-details-marker {
            display: none;
        }


        .country-item summary::after {

            content:
                "＋";

            color:
                #2457a6;

            font-size:
                18px;
        }


        .country-item[open] summary::after {
            content: "−";
        }


        .country-item[open] summary {
            background: #eef3f8;
        }


        .country-article-list {

            width:
                100%;

            margin:
                0;

            padding:
                16px 24px 18px 44px;

            background:
                #ffffff;

            border-top:
                1px solid #e0e3e7;
        }


        .country-article-list li {

            margin-bottom:
                15px;

            overflow-wrap:
                anywhere;

            word-break:
                break-word;
        }


        .country-article-list a {

            color:
                #1456a0;

            font-weight:
                600;

            text-decoration:
                none;
        }


        .country-article-list a:hover {
            text-decoration: underline;
        }


        .country-article-meta {

            margin-top:
                3px;

            color:
                #777777;

            font-size:
                13px;
        }


        .keywords {

            display:
                flex;

            flex-wrap:
                wrap;

            gap:
                10px;
        }


        .keyword {

            display:
                inline-flex;

            align-items:
                center;

            gap:
                7px;

            padding:
                7px 11px;

            background:
                #eef3f8;

            border-radius:
                20px;

            color:
                #173f73;

            font-weight:
                600;
        }


        .keyword small {
            color: #777777;
        }


        .empty {
            color: #777777;
        }


        .notice {

            margin-top:
                35px;

            padding-top:
                18px;

            border-top:
                1px solid #dddddd;

            color:
                #777777;

            font-size:
                13px;
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
"""


HTML_FOOT = """

</main>

</body>

</html>
"""


def create_html(
    articles: list[dict[str, object]],
) -> str:

    now = datetime.now(
        KST
    )

    category_counts = Counter(
        str(
            article["category"]
        )
        for article in articles
    )

    extracted_count = sum(
        1
        for article in articles
        if article.get(
            "article_text"
        )
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

    body = f"""

<header>

    <h1>
        한국 국제개발협력 Daily Brief
    </h1>

    <div class="date">
        {now:%Y.%m.%d}
    </div>

</header>


<hr class="divider">


<section class="summary">

    <h2>
        오늘의 핵심
    </h2>

    <ul>

        <li>
            국제개발협력 기사
            <strong>
                {len(articles)}건
            </strong>
        </li>

        <li>
            기사 본문 추출 성공
            <strong>
                {extracted_count}건
            </strong>
        </li>

        <li>
            정책·ODA 관련
            <strong>
                {category_counts.get("정책·ODA", 0)}건
            </strong>
        </li>

        <li>
            NGO 관련
            <strong>
                {category_counts.get("NGO·시민사회", 0)}건
            </strong>
        </li>

        <li>
            해외봉사 관련
            <strong>
                {category_counts.get("해외봉사", 0)}건
            </strong>
        </li>

        <li>
            인도적 지원 관련
            <strong>
                {category_counts.get("인도적 지원", 0)}건
            </strong>
        </li>

    </ul>

</section>


<hr class="divider">


{category_sections}


<section class="brief-section">

    <h2>
        ■ 국가별
    </h2>

    <p>
        국가명을 클릭하면 관련 기사목록이 펼쳐집니다.
    </p>

    <div class="country-grid">

        {country_section}

    </div>

</section>


<section class="brief-section">

    <h2>
        ■ 오늘 많이 나온 키워드
    </h2>

    <div class="keywords">

        {keyword_section}

    </div>

</section>


<div class="notice">

    본 브리핑은 Google News RSS 검색 결과와
    기사 본문을 바탕으로 자동 생성됩니다.

    <strong>
        기사 제목을 클릭하면 해당 기사로 이동합니다.
    </strong>

</div>
"""

    # 별도 원문기사 목록은 생성하지 않음
    return (
        HTML_HEAD
        + body
        + HTML_FOOT
    )


def create_readme(
    articles: list[dict[str, object]],
) -> str:

    now = datetime.now(
        KST
    )

    lines = [
        "# 🌍 한국 국제개발협력 Daily Brief",
        "",
        "한국 국제개발협력, ODA, NGO, 해외봉사 및 "
        "인도적 지원 관련 최신 뉴스를 자동으로 수집합니다.",
        "",
        f"> 최근 업데이트: **{now:%Y-%m-%d %H:%M} KST**",
        "",
        f"총 수집 기사: **{len(articles)}건**",
        "",
        "GitHub Pages의 기사 제목을 클릭하면 "
        "해당 기사로 이동합니다.",
        "",
    ]

    return "\n".join(
        lines
    )


def main() -> None:

    print(
        "1. 뉴스 수집 시작"
    )

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
        "3. 기사 분석 완료"
    )

    page_html = create_html(
        enriched_articles
    )

    readme_content = create_readme(
        enriched_articles
    )

    with open(
        "index.html",
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            page_html
        )

    with open(
        "README.md",
        "w",
        encoding="utf-8",
    ) as file:

        file.write(
            readme_content
        )

    print(
        "4. index.html과 "
        "README.md 생성 완료"
    )


if __name__ == "__main__":
    main()
