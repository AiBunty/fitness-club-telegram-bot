"""
Report generation utilities for daily and on-demand reports
"""
import logging
import io
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from telegram import Bot
from src.database.reports_operations import (
    get_active_members, get_inactive_members, get_member_daily_activity,
    get_top_performers, get_inactive_users, get_expiring_soon_members,
    get_membership_stats
)

logger = logging.getLogger(__name__)


def generate_active_members_report(limit: Optional[int] = 20) -> str:
    """
    Generate formatted report of active members
    """
    members = get_active_members(limit=limit)
    
    if not members:
        return "📊 *Active Members Report*\n\n❌ No active members found."
    
    report = f"📊 *Active Members Report*\n"
    report += f"Total Active: {len(members)}\n"
    report += f"{'(Showing top ' + str(limit) + ')' if limit else ''}\n\n"
    
    for i, member in enumerate(members, 1):
        name = member['full_name'] or f"User {member['telegram_id']}"
        username = f"@{member['telegram_username']}" if member['telegram_username'] else "No username"
        expiry = member['fee_expiry_date'].strftime("%d/%m/%Y") if member['fee_expiry_date'] else "No expiry"
        days_left = (member['fee_expiry_date'] - datetime.now().date()).days if member['fee_expiry_date'] else 999
        
        report += f"{i}. {name}\n"
        report += f"   👤 {username}\n"
        report += f"   📅 Expires: {expiry}"
        if days_left < 999:
            report += f" ({days_left}d left)"
        report += f"\n   💰 Points: {member['total_points']}\n\n"
    
    return report


def generate_inactive_members_report(limit: Optional[int] = 20) -> str:
    """
    Generate formatted report of inactive members
    """
    members = get_inactive_members(limit=limit)
    
    if not members:
        return "📊 *Inactive Members Report*\n\n✅ No inactive members found."
    
    report = f"⚠️ *Inactive Members Report*\n"
    report += f"Total Inactive: {len(members)}\n"
    report += f"{'(Showing top ' + str(limit) + ')' if limit else ''}\n\n"
    
    for i, member in enumerate(members, 1):
        name = member['full_name'] or f"User {member['telegram_id']}"
        username = f"@{member['telegram_username']}" if member['telegram_username'] else "No username"
        status = member['fee_status'] or "unpaid"
        
        if member['fee_expiry_date'] and member['fee_expiry_date'] < datetime.now().date():
            days_expired = (datetime.now().date() - member['fee_expiry_date']).days
            expiry_info = f"Expired {days_expired}d ago"
        else:
            expiry_info = "Never paid"
        
        report += f"{i}. {name}\n"
        report += f"   👤 {username}\n"
        report += f"   ⚠️ Status: {status}\n"
        report += f"   📅 {expiry_info}\n\n"
    
    return report


def generate_expiring_soon_report(days: int = 7) -> str:
    """
    Generate report of members expiring within X days
    """
    members = get_expiring_soon_members(days=days)
    
    if not members:
        return f"📅 *Expiring Soon Report ({days} days)*\n\n✅ No memberships expiring soon."
    
    report = f"⏰ *Expiring Soon Report*\n"
    report += f"Expiring in next {days} days: {len(members)}\n\n"
    
    for i, member in enumerate(members, 1):
        name = member['full_name'] or f"User {member['telegram_id']}"
        username = f"@{member['telegram_username']}" if member['telegram_username'] else "No username"
        expiry = member['fee_expiry_date'].strftime("%d/%m/%Y")
        days_left = member['days_remaining']
        
        urgency = "🔴" if days_left <= 3 else "🟡" if days_left <= 7 else "🟢"
        
        report += f"{urgency} {i}. {name}\n"
        report += f"   👤 {username}\n"
        report += f"   📅 Expires: {expiry} ({days_left}d)\n"
        report += f"   📞 {member['phone']}\n\n"
    
    return report


def generate_daily_activity_report(date: Optional[datetime] = None) -> str:
    """
    Generate comprehensive daily activity report
    """
    if not date:
        date = datetime.now()
    
    date_str = date.strftime("%d/%m/%Y")
    activities = get_member_daily_activity(date)
    
    if not activities:
        return f"📊 *Daily Activity Report - {date_str}*\n\n❌ No data available."
    
    # Filter active members and those with activity
    active_count = sum(1 for a in activities if a['activity_score'] > 0)
    total_members = len(activities)
    
    # Top performers (sorted by activity score)
    top_performers = sorted(activities, key=lambda x: x['activity_score'], reverse=True)[:20]
    
    # Members with no activity
    inactive_today = [a for a in activities if a['activity_score'] == 0][:20]
    
    report = f"📊 *Daily Activity Report*\n"
    report += f"📅 Date: {date_str}\n\n"
    report += f"👥 Total Members: {total_members}\n"
    report += f"✅ Active Today: {active_count}\n"
    report += f"❌ Inactive Today: {len(inactive_today)}\n\n"
    
    # Top 20 Performers
    report += "🏆 *Top 20 Active Members*\n\n"
    for i, member in enumerate(top_performers, 1):
        if member['activity_score'] == 0:
            break
        
        name = member['full_name'] or f"User {member['telegram_id']}"
        
        activities_list = []
        if member['attendance_count'] > 0:
            activities_list.append(f"✅ Attended")
        if member['weight_logs'] > 0:
            activities_list.append(f"⚖️ Weight")
        if member['water_cups'] > 0:
            activities_list.append(f"💧 {member['water_cups']} cups")
        if member['meal_logs'] > 0:
            activities_list.append(f"🍽️ {member['meal_logs']} meals")
        if member['habits_completed'] > 0:
            activities_list.append(f"✅ Habits")
        if member['shake_orders'] > 0:
            activities_list.append(f"🥛 Shake")
        
        report += f"{i}. {name}\n"
        report += f"   {', '.join(activities_list)}\n\n"
    
    # Last 20 Inactive
    if inactive_today:
        report += "⚠️ *Inactive Today (Last 20)*\n\n"
        for i, member in enumerate(inactive_today[:20], 1):
            name = member['full_name'] or f"User {member['telegram_id']}"
            status = "💳 Paid" if member['fee_status'] in ('paid', 'active') else "❌ Unpaid"
            
            report += f"{i}. {name} - {status}\n"
    
    return report


def generate_top_performers_report(days: int = 7) -> str:
    """
    Generate report of top performing members
    """
    performers = get_top_performers(days=days, limit=20)
    
    if not performers:
        return f"🏆 *Top Performers Report ({days} days)*\n\n❌ No data available."
    
    report = f"🏆 *Top 20 Performers*\n"
    report += f"Last {days} days\n\n"
    
    for i, member in enumerate(performers, 1):
        name = member['full_name'] or f"User {member['telegram_id']}"
        
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        
        report += f"{medal} {name}\n"
        report += f"   📊 Activity Days: {member['total_activity_days']}\n"
        report += f"   🏋️ Attendance: {member['attendance_days']}d\n"
        report += f"   ⚖️ Weight: {member['weight_log_days']}d\n"
        report += f"   💧 Water: {member['water_log_days']}d\n"
        report += f"   🍽️ Meals: {member['meal_log_days']}d\n"
        report += f"   ✅ Habits: {member['habit_log_days']}d\n"
        report += f"   💰 Points: {member['total_points']}\n\n"
    
    return report


def generate_inactive_users_report(days: int = 7) -> str:
    """
    Generate report of inactive users (no activity in X days)
    """
    inactive = get_inactive_users(days=days, limit=20)
    
    if not inactive:
        return f"📊 *Inactive Users Report ({days} days)*\n\n✅ All members are active!"
    
    report = f"⚠️ *Inactive Users*\n"
    report += f"No activity in last {days} days (Last 20)\n\n"
    
    for i, member in enumerate(inactive, 1):
        name = member['full_name'] or f"User {member['telegram_id']}"
        username = f"@{member['telegram_username']}" if member['telegram_username'] else "No username"
        days_inactive = member['days_inactive']
        status = "💳 Paid" if member['fee_status'] in ('paid', 'active') else "❌ Unpaid"
        
        report += f"{i}. {name}\n"
        report += f"   👤 {username}\n"
        report += f"   ⏰ Inactive: {days_inactive} days\n"
        report += f"   {status}\n\n"
    
    return report


def generate_membership_overview_report() -> str:
    """
    Generate comprehensive membership overview
    """
    stats = get_membership_stats()
    
    if not stats:
        return "📊 *Membership Overview*\n\n❌ Unable to fetch statistics."
    
    report = "📊 *Membership Overview*\n\n"
    report += f"👥 Total Members: {stats['total_members']}\n"
    report += f"✅ Active: {stats['active_members']}\n"
    report += f"❌ Inactive: {stats['inactive_members']}\n"
    report += f"⏰ Expiring Soon (7d): {stats['expiring_soon']}\n"
    report += f"🆕 New This Month: {stats['new_this_month']}\n"
    report += f"💰 Total Points: {stats['total_points_all']}\n\n"
    
    # Calculate percentages
    if stats['total_members'] > 0:
        active_pct = (stats['active_members'] / stats['total_members']) * 100
        inactive_pct = (stats['inactive_members'] / stats['total_members']) * 100
        
        report += f"📈 Active Rate: {active_pct:.1f}%\n"
        report += f"📉 Inactive Rate: {inactive_pct:.1f}%\n"
    
    return report


def generate_eod_report(date: Optional[datetime] = None) -> str:
    """
    Generate comprehensive End-of-Day report
    """
    if not date:
        date = datetime.now()
    
    date_str = date.strftime("%d/%m/%Y")
    
    report = f"🌙 *END OF DAY REPORT*\n"
    report += f"📅 {date_str}\n"
    report += f"{'='*30}\n\n"
    
    # Membership Overview
    stats = get_membership_stats()
    report += "📊 *MEMBERSHIP OVERVIEW*\n"
    report += f"👥 Total: {stats['total_members']}\n"
    report += f"✅ Active: {stats['active_members']}\n"
    report += f"❌ Inactive: {stats['inactive_members']}\n"
    report += f"⏰ Expiring Soon: {stats['expiring_soon']}\n\n"
    
    # Daily Activity Summary
    activities = get_member_daily_activity(date)
    active_today = sum(1 for a in activities if a['activity_score'] > 0)
    
    report += "📈 *TODAY'S ACTIVITY*\n"
    report += f"✅ Active Members: {active_today}/{stats['active_members']}\n"
    
    total_attendance = sum(a['attendance_count'] for a in activities)
    total_weight_logs = sum(a['weight_logs'] for a in activities)
    total_water_cups = sum(a['water_cups'] for a in activities)
    total_meal_logs = sum(a['meal_logs'] for a in activities)
    total_habits = sum(a['habits_completed'] for a in activities)
    total_shakes = sum(a['shake_orders'] for a in activities)
    
    report += f"🏋️ Attendance: {total_attendance}\n"
    report += f"⚖️ Weight Logs: {total_weight_logs}\n"
    report += f"💧 Water Logs: {total_water_cups} cups\n"
    report += f"🍽️ Meal Logs: {total_meal_logs}\n"
    report += f"✅ Habits: {total_habits}\n"
    report += f"🥛 Shakes: {total_shakes}\n\n"
    
    # Top 5 Performers Today
    top_today = sorted(activities, key=lambda x: x['activity_score'], reverse=True)[:5]
    report += "🏆 *TOP 5 TODAY*\n"
    for i, member in enumerate(top_today, 1):
        if member['activity_score'] == 0:
            break
        name = member['full_name'] or f"User {member['telegram_id']}"
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        report += f"{medal} {name} (Score: {member['activity_score']})\n"
    
    report += "\n"
    
    # Expiring Soon Alert
    expiring = get_expiring_soon_members(days=7)
    if expiring:
        report += f"⚠️ *EXPIRING SOON ({len(expiring)})*\n"
        for member in expiring[:5]:
            name = member['full_name'] or f"User {member['telegram_id']}"
            days = member['days_remaining']
            report += f"• {name} - {days}d left\n"
        report += "\n"
    
    # Inactive Alert
    inactive_week = get_inactive_users(days=7, limit=5)
    if inactive_week:
        report += f"😴 *INACTIVE (7+ days) - {len(inactive_week)}*\n"
        for member in inactive_week[:5]:
            name = member['full_name'] or f"User {member['telegram_id']}"
            days = member['days_inactive']
            report += f"• {name} - {days}d inactive\n"
    
    report += f"\n{'='*30}\n"
    report += f"Report generated at {datetime.now().strftime('%H:%M:%S')}"
    
    return report


def export_members_to_csv(members: List[Dict[str, Any]], filename: str) -> io.BytesIO:
    """
    Export members list to CSV file
    """
    output = io.BytesIO()
    output.name = filename
    
    writer = csv.writer(io.TextIOWrapper(output, encoding='utf-8', newline=''))
    
    # Write header
    writer.writerow(['Name', 'Username', 'Telegram ID', 'Phone', 'Fee Status', 
                     'Paid Date', 'Expiry Date', 'Total Points'])
    
    # Write data
    for member in members:
        writer.writerow([
            member.get('full_name', ''),
            member.get('telegram_username', ''),
            member.get('telegram_id', ''),
            member.get('phone', ''),
            member.get('fee_status', ''),
            member.get('fee_paid_date', '').strftime('%Y-%m-%d') if member.get('fee_paid_date') else '',
            member.get('fee_expiry_date', '').strftime('%Y-%m-%d') if member.get('fee_expiry_date') else '',
            member.get('total_points', 0)
        ])
    
    output.seek(0)
    return output
