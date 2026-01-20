#!/usr/bin/env python3
"""
Generate comprehensive chart data for the dashboard
"""

import pandas as pd
import numpy as np
from collections import defaultdict
import json

# Load data
players_df = pd.read_csv('data/public_players_export_2026-01-19_214745.csv')
matches_df = pd.read_csv('data/public_matches_export_2026-01-19_214740.csv')
participants_df = pd.read_csv('data/public_match_participants_export_2026-01-19_214731.csv')

participants_df['created_at'] = pd.to_datetime(participants_df['created_at'], format='mixed')
participants_df['hour'] = participants_df['created_at'].dt.hour
participants_df['weekday'] = participants_df['created_at'].dt.day_name()
participants_df['date'] = participants_df['created_at'].dt.date

player_lookup = players_df.set_index('id')['display_name'].to_dict()

chart_data = {}

# ============================================================
# 1. ALL PLAYER STATS (for tables)
# ============================================================
print("Generating player stats...")
all_players = []
for player_id in participants_df['player'].unique():
    if player_id not in player_lookup:
        continue
    data = participants_df[participants_df['player'] == player_id]
    games = len(data)
    if games < 5:
        continue

    wins = data['has_won'].sum()
    kos = data['total_kos'].sum()
    falls = data['total_falls'].sum()
    sds = data['total_sds'].sum()

    # Momentum
    sorted_data = data.sort_values('created_at')
    prev_won = None
    after_win = []
    after_loss = []
    for _, row in sorted_data.iterrows():
        if prev_won is not None:
            if prev_won:
                after_win.append(row['has_won'])
            else:
                after_loss.append(row['has_won'])
        prev_won = row['has_won']

    momentum = 0
    if len(after_win) >= 5 and len(after_loss) >= 5:
        momentum = (np.mean(after_win) - np.mean(after_loss)) * 100

    all_players.append({
        'name': player_lookup[player_id],
        'games': int(games),
        'wins': int(wins),
        'losses': int(games - wins),
        'winRate': round(wins / games * 100, 1),
        'kos': int(kos),
        'falls': int(falls),
        'sds': int(sds),
        'kd': round(kos / max(falls, 1), 2),
        'sdRate': round(sds / games, 3),
        'momentum': round(momentum, 1),
        'charsPlayed': int(data['smash_character'].nunique())
    })

all_players = sorted(all_players, key=lambda x: x['games'], reverse=True)
chart_data['allPlayers'] = all_players

# ============================================================
# 2. WIN RATE DISTRIBUTION
# ============================================================
print("Generating win rate distribution...")
win_rates = [p['winRate'] for p in all_players if p['games'] >= 20]
bins = list(range(0, 101, 10))
hist, _ = np.histogram(win_rates, bins=bins)
chart_data['winRateDistribution'] = {
    'labels': [f'{b}-{b+10}%' for b in bins[:-1]],
    'data': hist.tolist(),
    'players': all_players
}

# ============================================================
# 3. HOURLY ACTIVITY & WIN RATES
# ============================================================
print("Generating hourly data...")
hourly_stats = []
for hour in range(24):
    hour_data = participants_df[participants_df['hour'] == hour]
    games = len(hour_data)
    if games > 0:
        wr = hour_data['has_won'].mean() * 100
    else:
        wr = 50
    hourly_stats.append({
        'hour': hour,
        'games': int(games),
        'winRate': round(wr, 1)
    })

chart_data['hourlyActivity'] = {
    'labels': [f'{h}:00' for h in range(24)],
    'games': [h['games'] for h in hourly_stats],
    'winRates': [h['winRate'] for h in hourly_stats]
}

# ============================================================
# 4. DAILY ACTIVITY
# ============================================================
print("Generating daily data...")
day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
daily_stats = []
for day in day_order:
    day_data = participants_df[participants_df['weekday'] == day]
    games = len(day_data)
    daily_stats.append({
        'day': day[:3],
        'games': int(games)
    })

chart_data['dailyActivity'] = {
    'labels': [d['day'] for d in daily_stats],
    'data': [d['games'] for d in daily_stats]
}

# ============================================================
# 5. MONTHLY ACTIVITY
# ============================================================
print("Generating monthly data...")
participants_df['month'] = participants_df['created_at'].dt.to_period('M')
monthly = participants_df.groupby('month').size()
chart_data['monthlyActivity'] = {
    'labels': [str(m) for m in monthly.index],
    'data': monthly.tolist()
}

# ============================================================
# 6. ALL CHARACTER STATS
# ============================================================
print("Generating character stats...")
all_chars = []
for char in participants_df['smash_character'].unique():
    char_data = participants_df[participants_df['smash_character'] == char]
    plays = len(char_data)
    if plays < 5:
        continue
    wins = char_data['has_won'].sum()
    all_chars.append({
        'name': char,
        'plays': int(plays),
        'wins': int(wins),
        'winRate': round(wins / plays * 100, 1),
        'uniquePlayers': int(char_data['player'].nunique())
    })

all_chars = sorted(all_chars, key=lambda x: x['plays'], reverse=True)
chart_data['allCharacters'] = all_chars

# Top 20 for chart
chart_data['topCharacters'] = {
    'labels': [c['name'] for c in all_chars[:20]],
    'plays': [c['plays'] for c in all_chars[:20]],
    'winRates': [c['winRate'] for c in all_chars[:20]]
}

# ============================================================
# 7. MOMENTUM BY PLAYER
# ============================================================
print("Generating momentum data...")
momentum_data = [p for p in all_players if p['games'] >= 30 and p['momentum'] != 0]
momentum_data = sorted(momentum_data, key=lambda x: x['momentum'], reverse=True)
chart_data['momentumByPlayer'] = {
    'labels': [p['name'] for p in momentum_data],
    'data': [p['momentum'] for p in momentum_data]
}

# ============================================================
# 8. K/D RATIO BY PLAYER
# ============================================================
print("Generating K/D data...")
kd_data = sorted([p for p in all_players if p['games'] >= 30], key=lambda x: x['kd'], reverse=True)
chart_data['kdByPlayer'] = {
    'labels': [p['name'] for p in kd_data],
    'data': [p['kd'] for p in kd_data]
}

# ============================================================
# 9. GAMES PLAYED DISTRIBUTION
# ============================================================
print("Generating games distribution...")
games_counts = [p['games'] for p in all_players]
chart_data['gamesDistribution'] = {
    'labels': [p['name'] for p in all_players[:30]],
    'data': [p['games'] for p in all_players[:30]]
}

# ============================================================
# 10. HEAD TO HEAD MATRIX (top 10 players)
# ============================================================
print("Generating head-to-head data...")
top_10_names = [p['name'] for p in all_players[:10]]
top_10_ids = {v: k for k, v in player_lookup.items() if v in top_10_names}

h2h_matrix = {name: {name2: {'wins': 0, 'total': 0} for name2 in top_10_names} for name in top_10_names}

match_groups = participants_df.groupby('match_id')
for match_id, group in match_groups:
    if len(group) != 2:
        continue
    rows = list(group.itertuples())
    p1_id, p2_id = rows[0].player, rows[1].player
    p1_name = player_lookup.get(p1_id)
    p2_name = player_lookup.get(p2_id)

    if p1_name in top_10_names and p2_name in top_10_names:
        h2h_matrix[p1_name][p2_name]['total'] += 1
        h2h_matrix[p2_name][p1_name]['total'] += 1
        if rows[0].has_won:
            h2h_matrix[p1_name][p2_name]['wins'] += 1
        else:
            h2h_matrix[p2_name][p1_name]['wins'] += 1

# Convert to win rates
h2h_data = []
for p1 in top_10_names:
    row = []
    for p2 in top_10_names:
        if p1 == p2:
            row.append(None)
        elif h2h_matrix[p1][p2]['total'] > 0:
            wr = h2h_matrix[p1][p2]['wins'] / h2h_matrix[p1][p2]['total'] * 100
            row.append({
                'wr': round(wr, 1),
                'wins': h2h_matrix[p1][p2]['wins'],
                'total': h2h_matrix[p1][p2]['total']
            })
        else:
            row.append({'wr': 0, 'wins': 0, 'total': 0})
    h2h_data.append(row)

chart_data['headToHead'] = {
    'players': top_10_names,
    'matrix': h2h_data
}

# ============================================================
# 11. ACTIVITY HEATMAP (hour x day)
# ============================================================
print("Generating heatmap data...")
heatmap = []
for day in day_order:
    row = []
    for hour in range(24):
        count = len(participants_df[(participants_df['weekday'] == day) & (participants_df['hour'] == hour)])
        row.append(int(count))
    heatmap.append(row)

chart_data['activityHeatmap'] = {
    'days': [d[:3] for d in day_order],
    'hours': list(range(24)),
    'data': heatmap
}

# ============================================================
# 12. WIN STREAKS DISTRIBUTION
# ============================================================
print("Generating streak data...")
all_streaks = []
for player_id in participants_df['player'].unique():
    if player_id not in player_lookup:
        continue
    data = participants_df[participants_df['player'] == player_id].sort_values('created_at')
    current = 0
    for _, row in data.iterrows():
        if row['has_won']:
            current += 1
        else:
            if current > 0:
                all_streaks.append(current)
            current = 0
    if current > 0:
        all_streaks.append(current)

streak_counts = {}
for s in all_streaks:
    if s <= 10:
        key = str(s)
    else:
        key = '10+'
    streak_counts[key] = streak_counts.get(key, 0) + 1

chart_data['streakDistribution'] = {
    'labels': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '10+'],
    'data': [streak_counts.get(str(i), 0) for i in range(1, 11)] + [streak_counts.get('10+', 0)]
}

# ============================================================
# 13. SD RATE BY PLAYER
# ============================================================
print("Generating SD rate data...")
sd_data = sorted([p for p in all_players if p['games'] >= 30], key=lambda x: x['sdRate'], reverse=True)
chart_data['sdRateByPlayer'] = {
    'labels': [p['name'] for p in sd_data],
    'data': [p['sdRate'] for p in sd_data]
}

# ============================================================
# 14. CHARACTER DIVERSITY BY PLAYER
# ============================================================
print("Generating diversity data...")
diversity_data = sorted([p for p in all_players if p['games'] >= 30], key=lambda x: x['charsPlayed'], reverse=True)
chart_data['diversityByPlayer'] = {
    'labels': [p['name'] for p in diversity_data],
    'data': [p['charsPlayed'] for p in diversity_data]
}

# ============================================================
# 15. CUMULATIVE GAMES OVER TIME
# ============================================================
print("Generating timeline data...")
daily_games = participants_df.groupby('date').size().reset_index(name='games')
daily_games = daily_games.sort_values('date')
daily_games['cumulative'] = daily_games['games'].cumsum()

# Sample every 7 days for readability
sampled = daily_games.iloc[::7]
chart_data['cumulativeGames'] = {
    'labels': [str(d) for d in sampled['date'].tolist()],
    'data': sampled['cumulative'].tolist()
}

# ============================================================
# SAVE
# ============================================================
with open('chart_data.json', 'w') as f:
    json.dump(chart_data, f, indent=2, default=str)

print(f"\n✨ Chart data saved! Generated {len(chart_data)} datasets")
print(f"   - {len(all_players)} players")
print(f"   - {len(all_chars)} characters")
