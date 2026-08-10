from datetime import datetime, timedelta, timezone
from urllib.parse import quote

import feedparser


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


def google_news_rss_url(keyword: str) -> str:
    """Google News 한국어 검색 RSS 주소를 생성합니다."""
    encoded_keyword = quote(keyword)
    return (
        "https://news.google.com/rss/search"
        f"?q={encoded_keyword}"
        "&hl=ko"
        "&gl=KR"
        "&ceid=KR:ko"
    )


def clean_text(text: str) -> str:
    """마크다운 표시에 문제가 될 수 있는 문자를 정리합니다."""
    return (
        text.replace("|", "｜")
        .replace("\n", " ")
        .replace("\r", " ")
        .strip()
    )


def collect_news() -> dict[str, list[dict[str, str]]]:
    """키워드별 최신 뉴스를 수집하고 중복 기사를 제거합니다."""
    collected: dict[str, list[dict[str, str]]] = {}
    seen_links: set[str] = set()

    for keyword in SEARCH_KEYWORDS:
        feed = feedparser.parse(google_news_rss_url(keyword))
        articles: list[dict[str, str]] = []

        for entry in feed.entries:
            title = clean_text(entry.get("title", "제목 없음"))
            link = entry.get("link", "").strip()

            if not link or link in seen_links:
                continue

            published = entry.get("published", "발행일 미확인")
            source = entry.get("source", {})
            source_name = clean_text(source.get("title", "출처 미확인"))

            articles.append(
                {
                    "title": title,
                    "link": link,
                    "published": published,
                    "source": source_name,
                }
            )
            seen_links.add(link)

            if len(articles) >= MAX_ARTICLES_PER_KEYWORD:
                break

        collected[keyword] = articles

    return collected


def create_readme(news_data: dict[str, list[dict[str, str]]]) -> str:
    """수집 결과를 카테고리별 뉴스 목록으로 README에 표시합니다."""
    now = datetime.now(KST)

    lines = [
        "# 🌍 한국 국제개발협력 동향 뉴스",
        "",
        "한국 국제개발협력, ODA, NGO, 해외봉사 및 인도적 지원 관련 "
        "최신 뉴스를 자동으로 수집합니다.",
        "",
        f"> 최근 업데이트: **{now:%Y-%m-%d %H:%M} KST**",
        "",
        "---",
        "",
    ]

    total_articles = 0

    for keyword, articles in news_data.items():

        # 카테고리 제목
        lines.append(f"## ● {keyword}")
        lines.append("")

        if not articles:
            lines.append("수집된 기사가 없습니다.")
            lines.append("")
            continue

        for article in articles:

            title = article["title"]
            link = article["link"]
            source = article["source"]

            # 기사 제목 자체에 링크 연결
            lines.append(
                f"### [{title}]({link})"
            )

            # 출처 표시
            lines.append(
                f"<sub>출처: {source}</sub>"
            )

            lines.append("")
            total_articles += 1

        lines.append("---")
        lines.append("")

    lines.extend(
        [
            f"총 수집 기사: **{total_articles}건**",
            "",
            "※ 본 페이지는 Google News RSS 검색 결과를 자동으로 수집합니다. "
            "기사 제목을 클릭하면 해당 기사로 이동합니다.",
            "",
        ]
    )

    return "\n".join(lines)


def main() -> None:
    news_data = collect_news()
    readme_content = create_readme(news_data)

    with open("README.md", "w", encoding="utf-8") as file:
        file.write(readme_content)

    article_count = sum(len(articles) for articles in news_data.values())
    print(f"뉴스 {article_count}건을 수집했습니다.")
    print("README.md 파일을 업데이트했습니다.")


if __name__ == "__main__":
    main()
