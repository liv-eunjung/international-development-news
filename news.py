import html
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser
from openai import OpenAI


KST = timezone(timedelta(hours=9))

SEARCH_KEYWORDS = [
    "국제개발협력",
    "한국 ODA",
    "KOICA",
    "KCOC 국제개발협력",
    "개발협력 NGO",
    "해외봉사단",
    "인도적 지원",
    "OECD DAC 한국",
]

MAX_ARTICLES_PER_KEYWORD = 4
MAX_TOTAL_ARTICLES = 24

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


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
    return (
        value.replace("\n", " ")
        .replace("\r", " ")
        .strip()
    )


def collect_news() -> list[dict[str, str]]:
    """Google News RSS에서 기사를 수집하고 중복을 제거합니다."""
    articles: list[dict[str, str]] = []
    seen_titles: set[str] = set()

    for keyword in SEARCH_KEYWORDS:
        feed = feedparser.parse(google_news_rss_url(keyword))
        keyword_count = 0

        for entry in feed.entries:
            title = clean_text(entry.get("title", "제목 없음"))
            link = entry.get("link", "").strip()

            source_data = entry.get("source", {})
            source = clean_text(
                source_data.get("title", "출처 미확인")
            )

            if not title or not link:
                continue

            normalized_title = title.lower()

            if normalized_title in seen_titles:
                continue

            articles.append(
                {
                    "keyword": keyword,
                    "title": title,
                    "link": link,
                    "source": source,
                    "published": entry.get("published", ""),
                }
            )

            seen_titles.add(normalized_title)
            keyword_count += 1

            if keyword_count >= MAX_ARTICLES_PER_KEYWORD:
                break

            if len(articles) >= MAX_TOTAL_ARTICLES:
                return articles

    return articles


def analyze_news(articles: list[dict[str, str]]) -> dict:
    """수집한 기사 제목과 출처를 분야별로 분석합니다."""
    article_text = "\n".join(
        [
            (
                f"{index + 1}. [{article['keyword']}] "
                f"{article['title']} / 출처: {article['source']}"
            )
            for index, article in enumerate(articles)
        ]
    )

    prompt = f"""
다음은 한국 국제개발협력 관련 최신 뉴스 제목과 출처 목록이다.

{article_text}

기사 제목과 출처에 명시된 정보만을 근거로 분석하라.
본문에서 확인되지 않은 수치, 정책, 영향은 추정하거나 단정하지 마라.
유사한 내용은 통합하고 한국 국제개발협력 실무자가 이해하기 쉽게
간결한 개조식 문장으로 작성하라.

다음 JSON 형식으로만 답하라.

{{
  "headline": "오늘의 국제개발협력 동향을 요약한 한 문장",
  "overall_summary": [
    "전체 주요 동향 1",
    "전체 주요 동향 2",
    "전체 주요 동향 3"
  ],
  "sections": [
    {{
      "category": "정책·ODA",
      "summary": [
        "주요 분석 1",
        "주요 분석 2",
        "주요 분석 3"
      ],
      "implication": "한국 국제개발협력 업무 관련 시사점"
    }},
    {{
      "category": "NGO·시민사회",
      "summary": [
        "주요 분석 1",
        "주요 분석 2",
        "주요 분석 3"
      ],
      "implication": "NGO 및 시민사회 관련 시사점"
    }},
    {{
      "category": "해외봉사·인재양성",
      "summary": [
        "주요 분석 1",
        "주요 분석 2",
        "주요 분석 3"
      ],
      "implication": "해외봉사단과 인재양성 관련 시사점"
    }},
    {{
      "category": "인도적 지원·글로벌 이슈",
      "summary": [
        "주요 분석 1",
        "주요 분석 2",
        "주요 분석 3"
      ],
      "implication": "사업 운영 및 안전관리 관련 시사점"
    }}
  ]
}}
"""

    response = client.responses.create(
        model="gpt-5-mini",
        input=prompt,
    )

    output = response.output_text.strip()

    if output.startswith("```json"):
        output = (
            output.removeprefix("```json")
            .removesuffix("```")
            .strip()
        )
    elif output.startswith("```"):
        output = (
            output.removeprefix("```")
            .removesuffix("```")
            .strip()
        )

    return json.loads(output)


def render_analysis_sections(sections: list[dict]) -> str:
    """분야별 분석 내용을 흰 배경용 HTML로 생성합니다."""
    icons = {
        "정책·ODA": "🏛️",
        "NGO·시민사회": "🤝",
        "해외봉사·인재양성": "🌍",
        "인도적 지원·글로벌 이슈": "🚨",
    }

    rendered_sections = []

    for section in sections:
        category_raw = section.get("category", "기타")
        category = html.escape(category_raw)
        icon = icons.get(category_raw, "📌")

        summary_items = "".join(
            f"<li>{html.escape(item)}</li>"
            for item in section.get("summary", [])
        )

        implication = html.escape(
            section.get("implication", "분석된 시사점이 없습니다.")
        )

        rendered_sections.append(
            f"""
            <section class="analysis-section">
                <h2>{icon} {category}</h2>

                <ul class="analysis-list">
                    {summary_items}
                </ul>

                <div class="implication">
                    <strong>업무 시사점</strong>
                    <p>{implication}</p>
                </div>
            </section>
            """
        )

    return "\n".join(rendered_sections)


def render_article_links(articles: list[dict[str, str]]) -> str:
    """기사 원문 링크를 하단 목록으로 생성합니다."""
    article_items = []

    for index, article in enumerate(articles, start=1):
        title = html.escape(article["title"])
        link = html.escape(article["link"], quote=True)
        source = html.escape(article["source"])
        keyword = html.escape(article["keyword"])

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
                    출처: {source} · 검색 분야: {keyword}
                </div>
            </li>
            """
        )

    return "\n".join(article_items)


def create_html(
    articles: list[dict[str, str]],
    analysis: dict,
) -> str:
    """흰 배경의 뉴스 분석 웹페이지를 생성합니다."""
    now = datetime.now(KST)

    headline = html.escape(
        analysis.get(
            "headline",
            "한국 국제개발협력 동향을 정리했습니다.",
        )
    )

    overall_summary_items = "".join(
        f"<li>{html.escape(item)}</li>"
        for item in analysis.get("overall_summary", [])
    )

    sections_html = render_analysis_sections(
        analysis.get("sections", [])
    )

    article_links_html = render_article_links(articles)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width, initial-scale=1.0"
    >

    <title>한국 국제개발협력 동향 브리핑</title>

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

        .page-header {{
            padding-bottom: 28px;
            border-bottom: 2px solid #222222;
        }}

        .page-header h1 {{
            margin: 0 0 10px;
            font-size: 34px;
            line-height: 1.35;
        }}

        .updated {{
            margin-bottom: 22px;
            color: #666666;
            font-size: 14px;
        }}

        .headline {{
            padding: 18px 20px;
            background: #f4f6f8;
            border-left: 5px solid #2457a6;
            font-size: 18px;
            font-weight: 700;
        }}

        .overall-summary {{
            margin-top: 34px;
            padding-bottom: 28px;
            border-bottom: 1px solid #dddddd;
        }}

        .overall-summary h2 {{
            margin-top: 0;
            margin-bottom: 14px;
            font-size: 23px;
        }}

        .overall-summary li {{
            margin-bottom: 8px;
        }}

        .analysis-section {{
            padding: 30px 0;
            border-bottom: 1px solid #dddddd;
        }}

        .analysis-section h2 {{
            margin: 0 0 16px;
            font-size: 23px;
            color: #173f73;
        }}

        .analysis-list {{
            margin: 0;
            padding-left: 24px;
        }}

        .analysis-list li {{
            margin-bottom: 10px;
        }}

        .implication {{
            margin-top: 20px;
            padding: 16px 18px;
            background: #f7f8fa;
            border: 1px solid #e2e5e9;
        }}

        .implication strong {{
            color: #173f73;
        }}

        .implication p {{
            margin: 7px 0 0;
        }}

        .sources {{
            margin-top: 46px;
        }}

        .sources h2 {{
            padding-bottom: 12px;
            border-bottom: 2px solid #222222;
            font-size: 25px;
        }}

        .sources ol {{
            padding-left: 27px;
        }}

        .sources li {{
            margin-bottom: 18px;
            padding-left: 4px;
        }}

        .sources a {{
            color: #1456a0;
            font-weight: 600;
            text-decoration: none;
        }}

        .sources a:hover {{
            text-decoration: underline;
        }}

        .article-meta {{
            margin-top: 4px;
            color: #777777;
            font-size: 13px;
        }}

        .notice {{
            margin-top: 40px;
            padding-top: 18px;
            border-top: 1px solid #dddddd;
            color: #777777;
            font-size: 13px;
        }}

        @media (max-width: 640px) {{
            .container {{
                padding: 28px 18px 60px;
            }}

            .page-header h1 {{
                font-size: 27px;
            }}

            .headline {{
                font-size: 16px;
            }}

            .analysis-section h2 {{
                font-size: 21px;
            }}
        }}
    </style>
</head>

<body>
    <main class="container">
        <header class="page-header">
            <h1>한국 국제개발협력 동향 브리핑</h1>

            <div class="updated">
                최근 업데이트:
                {now:%Y년 %m월 %d일 %H:%M} KST
            </div>

            <div class="headline">
                {headline}
            </div>
        </header>

        <section class="overall-summary">
            <h2>주요 동향 요약</h2>

            <ul>
                {overall_summary_items}
            </ul>
        </section>

        {sections_html}

        <section class="sources">
            <h2>뉴스 원문 링크</h2>

            <ol>
                {article_links_html}
            </ol>
        </section>

        <p class="notice">
            본 페이지의 분석은 수집된 뉴스 제목과 출처를 기반으로
            자동 생성됩니다. 세부 내용과 사실관계는 기사 원문 및
            관계기관의 공식 발표자료를 확인하시기 바랍니다.
        </p>
    </main>
</body>
</html>
"""


def create_readme(
    articles: list[dict[str, str]],
    analysis: dict,
) -> str:
    """GitHub 저장소 첫 화면에 표시할 간단한 README를 만듭니다."""
    now = datetime.now(KST)

    lines = [
        "# 한국 국제개발협력 동향 브리핑",
        "",
        f"> 최근 업데이트: {now:%Y-%m-%d %H:%M} KST",
        "",
        analysis.get("headline", ""),
        "",
        "## 주요 동향",
        "",
    ]

    for item in analysis.get("overall_summary", []):
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "## 뉴스 원문",
            "",
        ]
    )

    for article in articles:
        lines.append(
            f"- [{article['title']}]({article['link']})"
            f" — {article['source']}"
        )

    return "\n".join(lines)


def main() -> None:
    articles = collect_news()

    if not articles:
        raise RuntimeError(
            "수집된 뉴스가 없습니다. RSS 주소와 검색어를 확인하세요."
        )

    analysis = analyze_news(articles)

    page_html = create_html(articles, analysis)
    readme_content = create_readme(articles, analysis)

    with open("index.html", "w", encoding="utf-8") as file:
        file.write(page_html)

    with open("README.md", "w", encoding="utf-8") as file:
        file.write(readme_content)

    print(f"뉴스 {len(articles)}건 수집 완료")
    print("index.html과 README.md 생성 완료")


if __name__ == "__main__":
    main()
