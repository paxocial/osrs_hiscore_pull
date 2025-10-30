"""Command line interface for the analytics engine."""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

from analytics.engine import AnalyticsEngine


def format_xp_rate(rate):
    """Format XP rate for display."""
    return f"{rate.skill_name}: +{rate.xp_gained:,} XP ({rate.xp_per_hour:,.0f} XP/hr, {rate.xp_per_day:,.0f} XP/day) - Level {rate.start_level} → {rate.end_level}"


def format_progression(progression):
    """Format skill progression for display."""
    return f"""
{progression.skill_name} Progression ({progression.time_span_days} days):
• XP Gained: {progression.xp_gained:,}
• Levels Gained: {progression.levels_gained}
• Average: {progression.avg_xp_per_day:,.0f} XP/day ({progression.avg_xp_per_hour:,.0f} XP/hr)
• Snapshots Analyzed: {len(progression.snapshots)}
"""


def format_milestone(milestone):
    """Format milestone for display."""
    return f"• {milestone.skill_name} reached {milestone.milestone_type} {milestone.milestone_value} on {milestone.achieved_at.strftime('%Y-%m-%d %H:%M')}"


def format_activity_trend(trend):
    """Format activity trend for display."""
    return f"""
{trend.activity_name}:
• Score Gained: {trend.total_score_gained:+,}
• Current Rank: {trend.current_rank:,} (Best: {trend.best_rank:,})
• Trend: {trend.trend_direction}
• Data Points: {len(trend.score_changes)}
"""


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="OSRS Analytics Engine CLI")
    parser.add_argument("account_name", help="Account name to analyze")
    parser.add_argument("--days", type=int, default=30, help="Number of days to analyze (default: 30)")
    parser.add_argument("--skill", help="Specific skill to analyze")
    parser.add_argument("--command", choices=["xp-rates", "progression", "milestones", "trends", "all"],
                       default="all", help="Analytics command to run (default: all)")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument("--db-path", help="Path to database file (default: data/analytics.db)")

    args = parser.parse_args()

    # Initialize analytics engine
    engine = AnalyticsEngine(Path(args.db_path) if args.db_path else None)

    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)

    results = {}

    try:
        if args.command in ["xp-rates", "all"]:
            print("📊 Calculating XP Rates...")
            xp_rates = engine.calculate_xp_rates(args.account_name, args.skill, start_date, end_date)
            results["xp_rates"] = xp_rates

            if args.json:
                print(json.dumps([vars(rate) for rate in xp_rates], indent=2, default=str))
            else:
                if xp_rates:
                    print(f"\n🔥 XP Rates for {args.account_name} (last {args.days} days):")
                    for rate in sorted(xp_rates, key=lambda r: r.xp_per_hour, reverse=True):
                        print(f"  {format_xp_rate(rate)}")
                else:
                    print("  No XP gains detected in the specified period.")

        if args.command in ["progression", "all"] and not args.skill:
            print("📈 Analyzing Skill Progression...")
            # Get top skills by total XP
            xp_rates = engine.calculate_xp_rates(args.account_name, None, start_date, end_date)
            top_skills = sorted(xp_rates, key=lambda r: r.xp_gained, reverse=True)[:5]

            results["progression"] = []
            for rate in top_skills:
                progression = engine.get_skill_progression(args.account_name, rate.skill_name, args.days)
                if progression:
                    results["progression"].append(progression)

            if args.json:
                print(json.dumps([vars(p) for p in results["progression"]], indent=2, default=str))
            else:
                if results["progression"]:
                    print(f"\n📈 Top Skill Progressions for {args.account_name}:")
                    for progression in results["progression"]:
                        print(format_progression(progression))
                else:
                    print("  No progression data available.")

        elif args.command in ["progression", "all"] and args.skill:
            print(f"📈 Analyzing {args.skill} Progression...")
            progression = engine.get_skill_progression(args.account_name, args.skill, args.days)
            results["progression"] = progression

            if args.json:
                print(json.dumps(vars(progression), indent=2, default=str) if progression else "null")
            else:
                if progression:
                    print(f"\n📈 {args.skill} Progression for {args.account_name}:")
                    print(format_progression(progression))
                else:
                    print(f"  No {args.skill} progression data available.")

        if args.command in ["milestones", "all"]:
            print("🏆 Finding Milestones...")
            milestones = engine.calculate_milestones(args.account_name, days=args.days)
            results["milestones"] = milestones

            if args.json:
                print(json.dumps([vars(m) for m in milestones], indent=2, default=str))
            else:
                if milestones:
                    print(f"\n🏆 Recent Milestones for {args.account_name}:")
                    for milestone in milestones[:10]:  # Show top 10
                        print(format_milestone(milestone))
                else:
                    print("  No milestones found in the specified period.")

        if args.command in ["trends", "all"]:
            print("📊 Analyzing Activity Trends...")
            trends = engine.get_activity_trends(args.account_name, args.days)
            results["trends"] = trends

            if args.json:
                print(json.dumps([vars(t) for t in trends], indent=2, default=str))
            else:
                # Show only activities with significant changes
                significant_trends = [t for t in trends if abs(t.total_score_gained) > 0]
                if significant_trends:
                    print(f"\n📊 Activity Trends for {args.account_name}:")
                    for trend in sorted(significant_trends, key=lambda t: abs(t.total_score_gained), reverse=True):
                        print(format_activity_trend(trend))
                else:
                    print("  No significant activity changes detected.")

        if not args.json:
            print(f"\n✨ Analytics complete for {args.account_name}!")
            print(f"📅 Period: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')} ({args.days} days)")

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())