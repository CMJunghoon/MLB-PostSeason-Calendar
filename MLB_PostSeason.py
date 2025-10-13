#!/usr/bin/env python3
"""
MLB 2025 포스트시즌 ICS 자동 업데이트 스크립트
실시간으로 경기 결과를 가져와서 ICS 파일을 업데이트합니다.
"""

import statsapi
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional
import pytz
import json

class MLBPostseasonUpdater:
    def __init__(self, output_file: str = "mlb_postseason_2025.ics"):
        self.output_file = output_file
        self.postseason_start = datetime(2025, 9, 30)
        self.postseason_end = datetime(2025, 11, 2)
        self.et_tz = pytz.timezone('US/Eastern')
        self.utc_tz = pytz.UTC
        
        # 포스트시즌 게임 타입
        # F = Wild Card, D = Division Series, L = League Championship, W = World Series
        self.postseason_game_types = ['F', 'D', 'L', 'W']
        
    def get_postseason_schedule(self) -> List[Dict]:
        """포스트시즌 전체 일정을 가져옵니다."""
        games = []
        
        # 날짜별로 일정 조회
        current_date = self.postseason_start
        while current_date <= self.postseason_end:
            date_str = current_date.strftime('%m/%d/%Y')
            try:
                # statsapi.schedule() 사용 - 포스트시즌 게임 필터링
                schedule = statsapi.schedule(
                    start_date=date_str,
                    end_date=date_str
                )
                
                # 포스트시즌 경기만 필터링
                for game in schedule:
                    game_type = game.get('game_type', '')
                    
                    # 포스트시즌 게임 타입 확인
                    if game_type in self.postseason_game_types:
                        # 시간 정보 로깅
                        print(f"\n=== Game Time Debug ===")
                        print(f"Game: {game.get('away_name')} @ {game.get('home_name')}")
                        print(f"game_datetime: {game.get('game_datetime')}")
                        print(f"game_date: {game.get('game_date')}")
                        print(f"game_type: {game_type}")
                        print("=" * 50)
                        
                        games.append(game)
                        
            except Exception as e:
                print(f"Error fetching schedule for {date_str}: {e}")
            
            current_date += timedelta(days=1)
        
        return games
    
    def get_alternative_schedule(self) -> List[Dict]:
        """API 직접 호출로 일정을 가져옵니다 (대체 방법)."""
        games = []
        
        try:
            # 현재 시즌 정보 가져오기
            season = statsapi.get('season', {'sportId': 1, 'seasonId': 2025})
            
            # 직접 API 호출
            start_date = self.postseason_start.strftime('%Y-%m-%d')
            end_date = self.postseason_end.strftime('%Y-%m-%d')
            
            params = {
                'sportId': 1,  # MLB
                'startDate': start_date,
                'endDate': end_date,
                'gameType': 'F,D,L,W',  # Wild Card, Division, League Championship, World Series
            }
            
            schedule_data = statsapi.get('schedule', params)
            
            if 'dates' in schedule_data:
                for date_entry in schedule_data['dates']:
                    for game in date_entry.get('games', []):
                        # 게임 정보 파싱
                        game_info = self.parse_game_data(game)
                        if game_info:
                            games.append(game_info)
                            print(f"Found: {game_info.get('away_name')} @ {game_info.get('home_name')}")
            
        except Exception as e:
            print(f"Error in alternative schedule fetch: {e}")
        
        return games
    
    def parse_game_data(self, game_data: Dict) -> Optional[Dict]:
        """API 응답에서 게임 정보를 파싱합니다."""
        try:
            # 시간 정보 로깅
            print(f"\n=== API Game Time Debug ===")
            print(f"Game: {game_data.get('teams', {}).get('away', {}).get('team', {}).get('name', 'TBD')} @ {game_data.get('teams', {}).get('home', {}).get('team', {}).get('name', 'TBD')}")
            print(f"gameDate: {game_data.get('gameDate')}")
            print(f"officialDate: {game_data.get('officialDate')}")
            print("=" * 50)
            
            game_info = {
                'game_id': game_data.get('gamePk', ''),
                'game_type': game_data.get('gameType', ''),
                'game_date': game_data.get('gameDate', ''),
                'game_datetime': game_data.get('gameDate', ''),  # 통일성을 위해 추가
                'status': game_data.get('status', {}).get('detailedState', 'Scheduled'),
                'away_name': game_data.get('teams', {}).get('away', {}).get('team', {}).get('name', 'TBD'),
                'home_name': game_data.get('teams', {}).get('home', {}).get('team', {}).get('name', 'TBD'),
                'away_score': game_data.get('teams', {}).get('away', {}).get('score', 0),
                'home_score': game_data.get('teams', {}).get('home', {}).get('score', 0),
                'venue_name': game_data.get('venue', {}).get('name', 'TBD'),
                'series_description': game_data.get('seriesDescription', ''),
                'series_game_number': game_data.get('seriesGameNumber', 1),
                'game_number': game_data.get('gameNumber', 1),
            }
            
            # inning 정보
            if 'linescore' in game_data:
                inning = game_data['linescore'].get('currentInning', '')
                inning_state = game_data['linescore'].get('inningState', '')
                if inning:
                    game_info['inning'] = f"{inning_state} {inning}"
            
            return game_info
            
        except Exception as e:
            print(f"Error parsing game data: {e}")
            return None
    
    def format_game_time(self, game_datetime: str, away_team: str = '', home_team: str = '') -> tuple:
        """게임 시간을 UTC로 변환합니다. (현지 시간 기준)"""
        try:
            dt = None
            
            # 상대팀이 결정되지 않은 경우 (TBD) 기본 시간 사용
            if (not game_datetime or any(keyword in away_team for keyword in ("TBD", "Winner", "Lower", "Higher")) or any(keyword in home_team for keyword in ("TBD", "Winner", "Lower", "Higher"))):
                # if game_datetime and 'T' not in game_datetime:
                    # 날짜만 있는 경우
                    utc_dt = datetime.strptime(game_datetime, "%Y-%m-%dT%H:%M:%SZ")
                    utc_dt = utc_dt.replace(tzinfo=pytz.UTC)

                    # 2. ET timezone
                    et_tz = pytz.timezone("US/Eastern")

                    # 3. ET 날짜로 변환 (시간 무시)
                    et_date = utc_dt.astimezone(et_tz).date()

                    # 4. 날짜 + 15:08 (ET)으로 새 datetime 생성
                    dt = et_tz.localize(datetime.combine(et_date, time(15, 8)))
                    print(f"\n>>> TBD team detected, using default time 3:08 PM ET")
                    print(f"    Date: {game_datetime} -> {dt}")
                # else:
                    # print(f"\n>>> No valid datetime for TBD game")
                    # return None, None
            else:
                print(f"\n>>> Parsing time: {game_datetime}")
                
                # 형식 1: ISO format with Z (2025-09-30T17:08:00Z)
                if 'Z' in game_datetime:
                    utc_dt = datetime.strptime(game_datetime, "%Y-%m-%dT%H:%M:%SZ")
                    utc_dt = utc_dt.replace(tzinfo=pytz.UTC)

                    # 처음 값이 33분인지 확인
                    if utc_dt.minute == 33:
                        # 동부 시간대 변환
                        # 2. ET timezone
                        et_tz = pytz.timezone("US/Eastern")

                        # 3. ET 날짜로 변환 (시간 무시)
                        et_date = utc_dt.astimezone(et_tz).date()

                        # 4. 날짜 + 15:08 (ET)으로 새 datetime 생성
                        dt = et_tz.localize(datetime.combine(et_date, time(15, 8)))
                        print(f"\n>>> TBD team detected, using default time 3:08 PM ET")
                        print(f"    Date: {game_datetime} -> {dt}")
                    else:
                        dt = datetime.fromisoformat(game_datetime.replace('Z', '+00:00'))
                    print(f"    Parsed as UTC: {dt}")
                # 형식 2: ISO format with timezone offset (2025-09-30T13:08:00-04:00)
                elif '+' in game_datetime or (game_datetime.count('-') > 2):
                    dt = datetime.fromisoformat(game_datetime)
                    print(f"    Parsed with timezone: {dt}")
                # 형식 3: ISO format without timezone (2025-09-30T17:08:00)
                elif 'T' in game_datetime:
                    dt = datetime.fromisoformat(game_datetime)
                    # timezone 정보가 없으면 UTC로 가정
                    if dt.tzinfo is None:
                        dt = pytz.utc.localize(dt)
                    print(f"    Parsed as UTC (no tz): {dt}")
                # 형식 4: 날짜만 있는 경우 (2025-09-30)
                else:
                    dt = datetime.strptime(game_datetime, '%Y-%m-%d')
                    dt = self.et_tz.localize(dt.replace(hour=15, minute=8))  # 3:08 PM ET
                    print(f"    Date only, set to 3:08 PM ET: {dt}")
            
            if dt is None:
                return None, None
            
            # UTC로 변환
            if dt.tzinfo != pytz.UTC:
                dt_utc = dt.astimezone(pytz.UTC)
                print(f"    Converted to UTC: {dt_utc}")
            else:
                dt_utc = dt
            
            # ICS 형식으로 변환
            start_time = dt_utc.strftime('%Y%m%dT%H%M%SZ')
            end_time = (dt_utc + timedelta(hours=3, minutes=30)).strftime('%Y%m%dT%H%M%SZ')
            
            # 한국 시간으로도 표시
            kst = pytz.timezone('Asia/Seoul')
            dt_kst = dt_utc.astimezone(kst)
            print(f"    UTC: {start_time} / KST: {dt_kst.strftime('%Y-%m-%d %H:%M %Z')}")
            
            return start_time, end_time
            
        except Exception as e:
            print(f"!!! Error parsing datetime '{game_datetime}': {e}")
            import traceback
            traceback.print_exc()
            return None, None
    
    def get_series_name(self, game_type: str, series_desc: str = '') -> str:
        """게임 타입에서 시리즈 이름을 생성합니다."""
        type_map = {
            'F': 'WC',
            'D': 'DS',
            'L': 'CS',
            'W': 'WS'
        }
        
        series_name = type_map.get(game_type, 'Postseason')
        
        # 리그 정보가 있으면 추가
        if series_desc:
            if 'American League' in series_desc or 'AL' in series_desc:
                if game_type == 'D':
                    return 'ALDS'
                elif game_type == 'L':
                    return 'ALCS'
            elif 'National League' in series_desc or 'NL' in series_desc:
                if game_type == 'D':
                    return 'NLDS'
                elif game_type == 'L':
                    return 'NLCS'
        
        if game_type == 'F':
            return 'WC'
        elif game_type == 'W':
            return 'WS'
        
        return series_name
    
    def create_event_summary(self, game: Dict) -> str:
        """이벤트 제목을 생성합니다."""
        away_team_full = game.get('away_name', 'TBD')
        home_team_full = game.get('home_name', 'TBD')
        
        away_team = self.get_team_location(away_team_full)
        home_team = self.get_team_location(home_team_full)

        game_type = game.get('game_type', '')
        series_desc = game.get('series_description', '')
        game_num = game.get('series_game_number', game.get('game_number', 1))
        series_name = self.get_series_name(game_type, series_desc)
        
        # 경기 상태 확인
        status = game.get('status', '')
        
        if status in ['Final', 'Game Over']:
            away_score = game.get('away_score', 0)
            home_score = game.get('home_score', 0)
            summary = f"✓ {series_name} {game_num}: {away_team} {away_score} @ {home_team} {home_score}"
        else:
            summary = f"{series_name} {game_num}: {away_team} @ {home_team}"
        
        return summary

    def get_team_location(self, full_team_name: str) -> str:
        """팀 전체 이름에서 지역명만 추출합니다."""
        # 특수 케이스 처리
        special_cases = {
            'Los Angeles Dodgers': 'LA Dodgers',
            'Los Angeles Angels': 'LA Angels',
            'New York Yankees': 'NY Yankees',
            'New York Mets': 'NY Mets',
            'Chicago White Sox': 'Chi White Sox',
            'Chicago Cubs': 'Chi Cubs',
            'San Francisco Giants': 'SF Giants',
            'San Diego Padres': 'San Diego',
            'Tampa Bay Rays': 'Tampa Bay',
        }
        
        # 특수 케이스에 있으면 바로 반환
        if full_team_name in special_cases:
            return special_cases[full_team_name]
        
        # 일반적인 경우: 첫 단어(들) 추출
        # "Boston Red Sox" -> "Boston"
        # "Toronto Blue Jays" -> "Toronto"
        # "St. Louis Cardinals" -> "St. Louis"
        
        words = full_team_name.split()
        
        # St. Louis 같은 경우 처리
        if len(words) > 1 and words[0].endswith('.'):
            return f"{words[0]} {words[1]}"

        if any(keyword in full_team_name for keyword in ("TBD", "Winner", "Lower", "Higher")):
            return full_team_name

        # 기본: 첫 번째 단어만 반환
        return words[0]
    
    def create_event_description(self, game: Dict) -> str:
        """이벤트 설명을 생성합니다."""
        series_desc = game.get('series_description', '')
        status = game.get('status', '')
        venue = game.get('venue_name', 'TBD')
        game_type = game.get('game_type', '')
        
        desc_lines = []
        if series_desc:
            desc_lines.append(f"Series: {series_desc}")
        desc_lines.append(f"Game Type: {game_type}")
        desc_lines.append(f"Status: {status}")
        desc_lines.append(f"Venue: {venue}")
        
        # 경기가 끝났으면 결과 추가
        if status in ['Final', 'Game Over']:
            away_score = game.get('away_score', 0)
            home_score = game.get('home_score', 0)
            away_name = game.get('away_name', 'Away')
            home_name = game.get('home_name', 'Home')
            desc_lines.append(f"\\nFinal Score:")
            desc_lines.append(f"{away_name}: {away_score}")
            desc_lines.append(f"{home_name}: {home_score}")
        
        return "\\n".join(desc_lines)
    
    def generate_ics_content(self, games: List[Dict]) -> str:
        """ICS 파일 내용을 생성합니다."""
        ics_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//MLB 2025 Postseason Auto-Updated//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:MLB 2025 Postseason",
            "X-WR-TIMEZONE:UTC",
            "X-PUBLISHED-TTL:PT1H"
        ]
        
        print(f"\n{'=' * 60}")
        print(f"Generating ICS for {len(games)} games")
        print(f"{'=' * 60}")
        
        for idx, game in enumerate(games, 1):
            game_datetime = game.get('game_datetime') or game.get('game_date')
            away_team = game.get('away_name', 'TBD')
            home_team = game.get('home_name', 'TBD')

            if not game_datetime:
                print(f"\nSkipping game {idx}: No datetime found")
                continue
            
            print(f"\n--- Game {idx}/{len(games)} ---")
            start_time, end_time = self.format_game_time(game_datetime, away_team, home_team)
            if not start_time:
                print(f"Skipping: Failed to parse time")
                continue
            
            game_id = game.get('game_id', '')
            summary = self.create_event_summary(game)
            description = self.create_event_description(game)
            location = game.get('venue_name', 'TBD')
            
            # 이벤트 생성
            ics_lines.extend([
                "",
                "BEGIN:VEVENT",
                f"UID:mlb-2025-{game_id}@mlb.com",
                f"DTSTAMP:{datetime.now(pytz.UTC).strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{start_time}",
                f"DTEND:{end_time}",
                f"SUMMARY:{summary}",
                f"LOCATION:{location}",
                f"DESCRIPTION:{description}",
                "STATUS:CONFIRMED",
                "END:VEVENT"
            ])
        
        ics_lines.extend(["", "END:VCALENDAR"])
        
        return "\n".join(ics_lines)
    
    def update_ics_file(self):
        """ICS 파일을 업데이트합니다."""
        print("Fetching MLB postseason schedule...")
        print("=" * 60)
        
        # 먼저 표준 방법 시도
        games = self.get_postseason_schedule()
        
        # 결과가 없으면 대체 방법 시도
        if not games:
            print("\nTrying alternative API method...")
            print("=" * 60)
            games = self.get_alternative_schedule()
        
        if not games:
            print("\n❌ No postseason games found!")
            print("Possible reasons:")
            print("  1. Games haven't been scheduled in the API yet")
            print("  2. API date range might need adjustment")
            print("  3. Network or API issues")
            return
        
        print(f"\n✓ Found {len(games)} postseason games")
        
        # 디버그: 첫 번째 게임의 시간 정보 출력
        if games:
            first_game = games[0]
            print(f"\nDebug - First game time info:")
            print(f"  Raw game_date: {first_game.get('game_date')}")
            start, end = self.format_game_time(first_game.get('game_date', ''))
            if start:
                print(f"  Converted start (UTC): {start}")
                # UTC 시간을 한국 시간으로 표시
                dt_utc = datetime.strptime(start, '%Y%m%dT%H%M%SZ')
                dt_utc = pytz.utc.localize(dt_utc)
                kst = pytz.timezone('Asia/Seoul')
                dt_kst = dt_utc.astimezone(kst)
                print(f"  In KST: {dt_kst.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        print("=" * 60)
        
        # ICS 파일 생성
        ics_content = self.generate_ics_content(games)
        
        # 파일 저장
        with open(self.output_file, 'w', encoding='utf-8') as f:
            f.write(ics_content)
        
        print(f"\n✓ ICS file updated: {self.output_file}")
        
        # 통계 출력
        completed = sum(1 for g in games if g.get('status') in ['Final', 'Game Over'])
        scheduled = sum(1 for g in games if g.get('status') not in ['Final', 'Game Over', 'Postponed'])
        
        print(f"\nStats:")
        print(f"  - Completed games: {completed}")
        print(f"  - Scheduled games: {scheduled}")
        print(f"  - Total games: {len(games)}")
    
    def get_live_games(self) -> List[Dict]:
        """현재 진행 중인 경기를 가져옵니다."""
        today = datetime.now().strftime('%m/%d/%Y')
        try:
            schedule = statsapi.schedule(start_date=today, end_date=today)
            
            live_games = []
            for game in schedule:
                game_type = game.get('game_type', '')
                status = game.get('status', '')
                
                if game_type in self.postseason_game_types and status in ['In Progress', 'Live']:
                    live_games.append(game)
            
            return live_games
        except:
            return []
    
    def watch_mode(self, interval: int = 300):
        """주기적으로 일정을 업데이트합니다 (초 단위)."""
        print(f"\n{'=' * 60}")
        print(f"Starting watch mode (updating every {interval} seconds)")
        print(f"Press Ctrl+C to stop")
        print(f"{'=' * 60}\n")
        
        try:
            while True:
                self.update_ics_file()
                
                # 진행 중인 경기 표시
                live_games = self.get_live_games()
                if live_games:
                    print("\n🔴 Live Games:")
                    for game in live_games:
                        away = game.get('away_name', 'TBD')
                        home = game.get('home_name', 'TBD')
                        away_score = game.get('away_score', 0)
                        home_score = game.get('home_score', 0)
                        inning = game.get('inning', '')
                        print(f"  {away} {away_score} @ {home} {home_score} {inning}")
                
                print(f"\nNext update in {interval} seconds...")
                print("=" * 60)
                
                import time
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n✓ Stopped by user")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description='MLB 2025 Postseason ICS Updater',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update once
  python mlb_postseason_updater.py
  
  # Watch mode (update every 5 minutes)
  python mlb_postseason_updater.py --watch
  
  # Watch mode with custom interval (2 minutes)
  python mlb_postseason_updater.py --watch --interval 120
        """
    )
    parser.add_argument(
        '-o', '--output',
        default='public/mlb_postseason_2025.ics',
        help='Output ICS file path (default: mlb_postseason_2025.ics)'
    )
    parser.add_argument(
        '-w', '--watch',
        action='store_true',
        help='Watch mode: continuously update the file'
    )
    parser.add_argument(
        '-i', '--interval',
        type=int,
        default=300,
        help='Update interval in seconds for watch mode (default: 300)'
    )
    
    args = parser.parse_args()
    
    updater = MLBPostseasonUpdater(output_file=args.output)
    
    if args.watch:
        updater.watch_mode(interval=args.interval)
    else:
        updater.update_ics_file()


if __name__ == "__main__":
    from datetime import datetime
    today = datetime.now()
    if not ((today.month == 9 and today.day >= 28) or (today.month == 10) or (today.month == 11 and today.day <= 3)):
        print("Not postseason period. Skipping deploy.")
        exit(0)

    main()
