"""
Challenge Reports and Visualizations
Generates leaderboards and graphical reports for challenges
"""

import logging
import os
from datetime import datetime, timedelta
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from PIL import Image, ImageDraw, ImageFont

from src.database.challenges_operations import (
    get_challenge_by_id, get_challenge_participants, get_user_rank_in_challenge
)
from src.database.user_operations import get_user_by_id
from src.utils.challenge_points import get_challenge_points_summary, CHALLENGE_POINTS_CONFIG

logger = logging.getLogger(__name__)

class ChallengeReports:
    """Generate challenge reports and visualizations"""
    
    def __init__(self):
        self.img_dir = "reports"
        os.makedirs(self.img_dir, exist_ok=True)
    
    def generate_leaderboard_image(self, challenge_id, limit=10):
        """Generate leaderboard visualization"""
        try:
            challenge = get_challenge_by_id(challenge_id)
            if not challenge:
                return None
            
            participants = get_challenge_participants(challenge_id, limit=limit)
            
            # Create image
            width = 800
            height = 50 + (len(participants) * 60) + 50
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            # Load font
            try:
                title_font = ImageFont.truetype("arial.ttf", 28)
                rank_font = ImageFont.truetype("arial.ttf", 20)
                name_font = ImageFont.truetype("arial.ttf", 16)
            except:
                title_font = ImageFont.load_default()
                rank_font = ImageFont.load_default()
                name_font = ImageFont.load_default()
            
            # Draw title
            draw.text((width//2 - 100, 10), f"🏆 {challenge['name']} Leaderboard", 
                     fill='black', font=title_font)
            
            # Draw participants
            y_pos = 60
            medals = ["🥇", "🥈", "🥉"]
            colors = [(255, 215, 0), (192, 192, 192), (205, 127, 50)]  # Gold, Silver, Bronze
            
            for idx, participant in enumerate(participants):
                medal = medals[idx] if idx < 3 else f"{idx+1}."
                bg_color = colors[idx] if idx < 3 else (240, 240, 240)
                
                # Draw background
                draw.rectangle([(10, y_pos), (width-10, y_pos+50)], fill=bg_color)
                
                # Draw rank
                draw.text((20, y_pos+10), medal, fill='black', font=rank_font)
                
                # Draw name and points
                name = participant.get('user_name', 'Unknown')[:20]
                points = participant.get('total_points', 0)
                text = f"{name} - {points} pts"
                
                draw.text((100, y_pos+12), text, fill='black', font=name_font)
                
                y_pos += 60
            
            # Save image
            filepath = f"{self.img_dir}/leaderboard_{challenge_id}.png"
            img.save(filepath)
            
            logger.info(f"Generated leaderboard image for challenge {challenge_id}")
            return filepath
        
        except Exception as e:
            logger.error(f"Error generating leaderboard: {e}")
            return None
    
    def generate_activity_breakdown(self, user_id, challenge_id):
        """Generate activity breakdown chart"""
        try:
            challenge = get_challenge_by_id(challenge_id)
            if not challenge:
                return None
            
            points_summary = get_challenge_points_summary(user_id, challenge_id)
            
            if not points_summary:
                return None
            
            # Prepare data
            activities = ['Check-ins', 'Water', 'Weight', 'Habits', 'Shakes']
            points = [
                points_summary.get('checkins', 0),
                points_summary.get('water', 0),
                points_summary.get('weight', 0),
                points_summary.get('habits', 0),
                points_summary.get('shakes', 0),
            ]
            
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
            
            # Create figure
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Create bar chart
            bars = ax.bar(activities, points, color=colors, edgecolor='black', linewidth=2)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{int(height)}',
                       ha='center', va='bottom', fontsize=12, fontweight='bold')
            
            ax.set_ylabel('Points', fontsize=12, fontweight='bold')
            ax.set_title(f'Activity Breakdown - {challenge["name"]}', 
                        fontsize=14, fontweight='bold')
            ax.set_ylim(0, max(points) * 1.2 if points else 100)
            
            # Save to BytesIO
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            buf.seek(0)
            plt.close()
            
            # Save file
            filepath = f"{self.img_dir}/activity_{user_id}_{challenge_id}.png"
            with open(filepath, 'wb') as f:
                f.write(buf.getvalue())
            
            logger.info(f"Generated activity breakdown for user {user_id}")
            return filepath
        
        except Exception as e:
            logger.error(f"Error generating activity chart: {e}")
            return None
    
    def generate_weight_journey(self, user_id, challenge_id):
        """Generate weight journey chart"""
        try:
            challenge = get_challenge_by_id(challenge_id)
            if not challenge:
                return None
            
            points_summary = get_challenge_points_summary(user_id, challenge_id)
            
            if not points_summary or 'weight_history' not in points_summary:
                return None
            
            weight_data = points_summary['weight_history']
            
            if len(weight_data) < 2:
                return None
            
            dates = [d['date'] for d in weight_data]
            weights = [d['weight'] for d in weight_data]
            
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Plot line chart
            ax.plot(range(len(dates)), weights, marker='o', linewidth=2, 
                   markersize=8, color='#FF6B6B')
            
            # Add start and end markers
            ax.scatter([0], [weights[0]], s=200, marker='o', color='green', 
                      label='Start', zorder=5)
            ax.scatter([len(weights)-1], [weights[-1]], s=200, marker='o', 
                      color='red', label='Current', zorder=5)
            
            # Calculate and display change
            weight_change = weights[-1] - weights[0]
            change_label = f"Total Change: {weight_change:.1f} kg"
            if weight_change < 0:
                change_label += " ✅ (Loss)"
            else:
                change_label += " ⚠️ (Gain)"
            
            ax.text(0.5, 0.95, change_label, transform=ax.transAxes,
                   ha='center', va='top', fontsize=12, fontweight='bold',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            ax.set_xlabel('Days', fontsize=12, fontweight='bold')
            ax.set_ylabel('Weight (kg)', fontsize=12, fontweight='bold')
            ax.set_title(f'Weight Journey - {challenge["name"]}', 
                        fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Save to BytesIO
            buf = BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
            buf.seek(0)
            plt.close()
            
            # Save file
            filepath = f"{self.img_dir}/weight_{user_id}_{challenge_id}.png"
            with open(filepath, 'wb') as f:
                f.write(buf.getvalue())
            
            logger.info(f"Generated weight journey for user {user_id}")
            return filepath
        
        except Exception as e:
            logger.error(f"Error generating weight chart: {e}")
            return None
    
    def generate_participation_stats(self, challenge_id):
        """Generate challenge participation statistics"""
        try:
            challenge = get_challenge_by_id(challenge_id)
            if not challenge:
                return None
            
            participants = get_challenge_participants(challenge_id, limit=None)
            
            if not participants:
                return None
            
            # Prepare data
            total_participants = len(participants)
            total_points = sum(p.get('total_points', 0) for p in participants)
            avg_points = total_points / total_participants if total_participants > 0 else 0
            
            # Create summary image
            width = 600
            height = 400
            img = Image.new('RGB', (width, height), color='white')
            draw = ImageDraw.Draw(img)
            
            try:
                title_font = ImageFont.truetype("arial.ttf", 24)
                stat_font = ImageFont.truetype("arial.ttf", 18)
            except:
                title_font = ImageFont.load_default()
                stat_font = ImageFont.load_default()
            
            # Draw title
            draw.text((width//2 - 120, 20), "📊 Challenge Statistics", 
                     fill='black', font=title_font)
            
            # Draw stats
            stats = [
                f"👥 Total Participants: {total_participants}",
                f"⭐ Average Points: {avg_points:.0f}",
                f"🏆 Total Points Earned: {total_points}",
                f"📅 Challenge: {challenge['name']}",
                f"📍 Status: {challenge['status'].upper()}",
            ]
            
            y_pos = 100
            for stat in stats:
                draw.text((50, y_pos), stat, fill='black', font=stat_font)
                y_pos += 50
            
            # Save image
            filepath = f"{self.img_dir}/stats_{challenge_id}.png"
            img.save(filepath)
            
            logger.info(f"Generated participation stats for challenge {challenge_id}")
            return filepath
        
        except Exception as e:
            logger.error(f"Error generating stats: {e}")
            return None
    
    def generate_daily_summary(self, challenge_id):
        """Generate daily leaderboard summary"""
        try:
            challenge = get_challenge_by_id(challenge_id)
            if not challenge:
                return None
            
            participants = get_challenge_participants(challenge_id, limit=5)
            
            message = f"""📊 *{challenge['name']} - Daily Update*

📅 {datetime.now().strftime('%B %d, %Y')}

🏆 *Top 5 Performers:*
"""
            
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            
            for idx, participant in enumerate(participants):
                medal = medals[idx]
                name = participant.get('user_name', 'Unknown')[:15]
                points = participant.get('total_points', 0)
                message += f"\n{medal} {name} ({points} pts)"
            
            message += f"""

📈 *Stats:*
• Total Participants: {len(participants)}
• Average Points: {sum(p.get('total_points', 0) for p in participants) / len(participants) if participants else 0:.0f}
• Status: ACTIVE
• Next Update: 10:00 PM

💪 *Keep pushing!* 🎯"""
            
            return message
        
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return None

# Initialize reports generator
reports = ChallengeReports()

async def send_leaderboard_photo(update, challenge_id):
    """Send leaderboard as photo"""
    filepath = reports.generate_leaderboard_image(challenge_id)
    
    if filepath and os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            await update.message.reply_photo(f, caption="🏆 Challenge Leaderboard")
    else:
        await update.message.reply_text("❌ Could not generate leaderboard image")

async def send_activity_breakdown(update, user_id, challenge_id):
    """Send activity breakdown chart"""
    filepath = reports.generate_activity_breakdown(user_id, challenge_id)
    
    if filepath and os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            await update.message.reply_photo(f, caption="📊 Activity Breakdown")
    else:
        await update.message.reply_text("❌ Could not generate activity chart")

async def send_weight_journey(update, user_id, challenge_id):
    """Send weight journey chart"""
    filepath = reports.generate_weight_journey(user_id, challenge_id)
    
    if filepath and os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            await update.message.reply_photo(f, caption="⚖️ Weight Journey")
    else:
        await update.message.reply_text("❌ Could not generate weight chart")

async def send_stats_summary(update, challenge_id):
    """Send statistics summary"""
    filepath = reports.generate_participation_stats(challenge_id)
    
    if filepath and os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            await update.message.reply_photo(f, caption="📊 Challenge Statistics")
    else:
        await update.message.reply_text("❌ Could not generate statistics")
