"""
Journal System - Main Entry Point
"""
import argparse
from datetime import datetime, timedelta
import pytz
from processors import TextProcessor, ContentMerger
from ai import AIProcessor
from storage import SheetsDatabase
from config import TIMEZONE, DATE_FORMAT


def process_day(target_date=None):
    """Process a single day's journal entries"""
    tz = pytz.timezone(TIMEZONE)
    if target_date is None:
        target_date = datetime.now(tz).date()

    date_str = target_date.strftime(DATE_FORMAT)

    print(f"\n{'='*60}")
    print(f"📔 JOURNAL PROCESSOR - {date_str}")
    print(f"{'='*60}")

    processor = TextProcessor()
    ai = AIProcessor()
    db = SheetsDatabase()

    # Step 1: Collect content
    print("\n📥 COLLECTING CONTENT...")
    sources = processor.process_all_sources(target_date)

    if not sources:
        print("\n⚠️  No content found for this date.")
        return None

    merged = ContentMerger.merge(sources)
    stats = ContentMerger.get_stats(sources)
    print(f"\n📊 Total: {stats['total_words']:,} words from {len(stats['sources_used'])} sources")

    # Step 2: AI Processing
    print("\n🤖 AI PROCESSING...")

    print("   Generating summary...")
    summary = ai.generate_daily_summary(merged)

    print("   Extracting tasks...")
    tasks = ai.extract_tasks(merged)

    print("   Analyzing insights...")
    insights = ai.extract_insights(merged)

    print("   Creating suggestions...")
    pending = [t['task'] for t in db.get_pending_tasks()]
    history = db.get_recent_entries(days=7)
    suggestions = ai.suggest_tasks(merged, pending, history)

    # Step 3: Save to Database
    print("\n💾 SAVING TO DATABASE...")

    entry = {
        "date": date_str,
        "raw_content": merged,
        "summary": summary,
        "mood": insights.get('mood', {}).get('primary', ''),
        "mood_confidence": insights.get('mood', {}).get('confidence', ''),
        "energy": insights.get('energy_level', ''),
        "themes": ', '.join(insights.get('themes', [])),
        "wins": ', '.join(insights.get('wins', [])),
        "challenges": ', '.join(insights.get('challenges', [])),
        "sources": ', '.join(stats['sources_used']),
        "word_count": stats['total_words']
    }
    db.save_daily_entry(entry)
    print("   ✓ Daily entry saved")

    # Save tasks
    task_records = []

    for t in tasks.get('completed', []):
        task_records.append({
            "date": date_str,
            "task": t.get('task', t) if isinstance(t, dict) else t,
            "status": "completed",
            "source": "extracted"
        })

    for t in tasks.get('pending', []):
        task_records.append({
            "date": date_str,
            "task": t.get('task', t) if isinstance(t, dict) else t,
            "status": "pending",
            "priority": t.get('priority', 'medium') if isinstance(t, dict) else 'medium',
            "source": "extracted"
        })

    for s in suggestions:
        task_records.append({
            "date": date_str,
            "task": s.get('task', ''),
            "status": "suggested",
            "priority": s.get('priority', 'medium'),
            "category": s.get('category', ''),
            "reason": s.get('reason', ''),
            "source": "ai_suggested"
        })

    if task_records:
        db.add_tasks_batch(task_records)
        print(f"   ✓ {len(task_records)} tasks saved")

    db.save_insights(date_str, insights)
    print("   ✓ Insights saved")

    # Step 4: Display Results
    print_results(date_str, summary, tasks, suggestions, insights)

    return {"date": date_str, "summary": summary, "tasks": tasks, "suggestions": suggestions, "insights": insights}


def process_week(week_start=None):
    """Generate a weekly review"""
    tz = pytz.timezone(TIMEZONE)

    if week_start is None:
        today = datetime.now(tz).date()
        week_start = today - timedelta(days=today.weekday() + 7)

    week_end = week_start + timedelta(days=6)

    print(f"\n{'='*60}")
    print(f"📅 WEEKLY REVIEW: {week_start} to {week_end}")
    print(f"{'='*60}")

    ai = AIProcessor()
    db = SheetsDatabase()

    entries = db.get_entries_for_week(week_start)

    if not entries:
        print("\n⚠️  No entries found for this week.")
        return None

    print(f"\n📊 Found {len(entries)} daily entries")
    print("\n🤖 Generating weekly review...")

    review = ai.generate_weekly_review(entries)

    review['week_start'] = str(week_start)
    review['week_end'] = str(week_end)
    db.save_weekly_review(review)
    print("   ✓ Weekly review saved")

    print_weekly_results(review)
    return review


def print_results(date_str, summary, tasks, suggestions, insights):
    """Display formatted results"""
    print(f"\n{'='*60}")
    print(f"📋 DAILY SUMMARY - {date_str}")
    print(f"{'='*60}")

    print(f"\n{summary}")

    mood = insights.get('mood', {})
    print(f"\n🎭 Mood: {mood.get('primary', 'Unknown')} | ⚡ Energy: {insights.get('energy_level', '?')}/10")

    themes = insights.get('themes', [])
    if themes:
        print(f"🏷️  Themes: {', '.join(themes)}")

    completed = tasks.get('completed', [])
    if completed:
        print(f"\n✅ COMPLETED ({len(completed)}):")
        for t in completed:
            task_text = t.get('task', t) if isinstance(t, dict) else t
            print(f"   ✓ {task_text}")

    pending = tasks.get('pending', [])
    if pending:
        print(f"\n📌 PENDING ({len(pending)}):")
        for t in pending:
            task_text = t.get('task', t) if isinstance(t, dict) else t
            priority = t.get('priority', '') if isinstance(t, dict) else ''
            icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(priority, '⚪')
            print(f"   {icon} {task_text}")

    if suggestions:
        print(f"\n💡 SUGGESTED FOR TOMORROW ({len(suggestions)}):")
        for s in suggestions:
            icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(s.get('priority', ''), '⚪')
            print(f"   {icon} {s.get('task', '')}")
            if s.get('reason'):
                print(f"      └─ {s.get('reason')}")

    wins = insights.get('wins', [])
    if wins:
        print(f"\n🏆 WINS:")
        for w in wins:
            print(f"   ⭐ {w}")

    challenges = insights.get('challenges', [])
    if challenges:
        print(f"\n🎯 CHALLENGES:")
        for c in challenges:
            print(f"   • {c}")

    print(f"\n{'='*60}\n")


def print_weekly_results(review):
    """Display formatted weekly review"""
    print(f"\n📝 OVERVIEW:")
    print(f"   {review.get('overview', '')}")

    print(f"\n🏆 ACCOMPLISHMENTS:")
    for a in review.get('accomplishments', []):
        print(f"   ⭐ {a}")

    patterns = review.get('patterns', {})
    if patterns:
        print(f"\n📊 PATTERNS:")
        print(f"   Mood: {patterns.get('mood_trend', 'N/A')}")
        print(f"   Energy: {patterns.get('energy_trend', 'N/A')}")

    print(f"\n💡 NEXT WEEK:")
    for s in review.get('next_week_suggestions', []):
        sug = s.get('suggestion', s) if isinstance(s, dict) else s
        print(f"   → {sug}")

    print(f"\n⭐ HIGHLIGHT: {review.get('highlight_of_week', 'N/A')}")
    print(f"📌 WORD OF WEEK: {review.get('word_of_week', 'N/A')}")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Journal Processing System")
    parser.add_argument("--date", help="Process specific date (YYYY-MM-DD)")
    parser.add_argument("--week", action="store_true", help="Generate weekly review")
    parser.add_argument("--week-start", help="Week start date (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.week or args.week_start:
        week_start = None
        if args.week_start:
            week_start = datetime.strptime(args.week_start, "%Y-%m-%d").date()
        process_week(week_start)
    else:
        target_date = None
        if args.date:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        process_day(target_date)
