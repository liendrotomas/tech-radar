def print_report(results: dict):
    articles = results.get("articles", [])
    filtered = results.get("filtered", [])
    opportunities = results.get("opportunities", [])

    print("\n" + "=" * 60)
    print("🧠 TECH RADAR REPORT")
    print("=" * 60)

    print(f"\n📥 Articles fetched: {len(articles)}")
    print(f"🧹 After filtering: {len(filtered)}")
    print(f"🚀 Opportunities: {len(opportunities)}")

    print("\n" + "-" * 60)
    print("🔥 TOP OPPORTUNITIES")
    print("-" * 60)

    for i, opp in enumerate(opportunities, 1):
        print(f"\n{i}. {opp['original'].get('name', 'N/A')}")
        print(f"   Score: {opp.get('score', 'N/A')}")
        print(f"   Why now: {opp['original'].get('why_now', '')[:120]}")
        print(f"   Wedge: {opp['original'].get('wedge', '')[:120]}")
        print(f"   Risk: {opp['original'].get('risk', '')[:120]}")

    print("\n" + "=" * 60 + "\n")
