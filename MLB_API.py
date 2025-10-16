import requests
import statsapi
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional
import pytz
import json


class MLBPostseasonICSMaker:
    def __init__(self, output_file: str = "mlb_postseason_2025.ics"):
        self.output_file = output_file
        self.utc_tz = pytz.UTC

        # 포스트시즌 게임 타입
        # F = Wild Card, D = Division Series, L = League Championship, W = World Series
        self.postseason_game_types = ["F", "D", "L", "W"]

    def get_postseason_schedule(self) -> List[Dict]:
        # API URL
        url = "https://statsapi.mlb.com/api/v1/schedule"

        # 쿼리 파라미터
        params = {
            "startDate": "10/01/2025",
            "endDate": "11/02/2025",
            "sportId": 1,
            "hydrate": "team(league),decisions,probablePitcher,linescore,stats(group=[pitching],type=season,sportId=1),currentTeam",
        }

        try:
            # API 요청
            response = requests.get(url, params=params)

            # 응답 상태 코드 확인
            response.raise_for_status()

            # JSON 데이터 파싱
            data = response.json()
            # 날짜별 경기 정보 출력
            return data
        except requests.exceptions.RequestException as e:
            print(f"API 요청 중 오류 발생: {e}")
        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}")
        except Exception as e:
            print(f"예상치 못한 오류: {e}")
        return {}

    def get_series_name(self, game: Dict) -> str:
        """포스트시즌 게임의 시리즈명을 생성합니다."""
        # 딕셔너리 접근을 한 번만 수행하여 성능 최적화
        teams = game.get("teams", {})
        gamesInSeries = game.get("gamesInSeries", {})

        away_team = teams.get("away", {})
        home_team = teams.get("home", {})

        # 기본 정보 추출
        game_type = game.get("gameType", "")
        status_code = game.get("status", {}).get("statusCode", "")
        series_game_number = game.get("seriesGameNumber", 1)

        # 팀 정보 추출
        away_name = away_team.get("team", {}).get("abbreviation", "TBD")
        home_name = home_team.get("team", {}).get("abbreviation", "TBD")

        away_name_shortName = away_team.get("team", {}).get("shortName", "TBD")
        home_name_shortName = home_team.get("team", {}).get("shortName", "TBD")

        league = home_team.get("team", {}).get("league", {}).get("abbreviation", "")

        # 시리즈 기록 및 스코어
        away_wins = away_team.get("leagueRecord", {}).get("wins", 0)
        home_wins = home_team.get("leagueRecord", {}).get("wins", 0)
        away_score = away_team.get("score", "")
        home_score = home_team.get("score", "")

        # 시리즈 기록 문자열 생성 (리드 상태 및 승리 조건 포함)

        wins_needed = (gamesInSeries // 2) + 1  # 3전2승, 5전3승, 7전4승
        if away_wins > home_wins:
            if away_wins >= wins_needed:
                series_record = f"({away_wins}-{home_wins}) {away_name_shortName} Wins"
            else:
                series_record = f"({away_wins}-{home_wins}) {away_name_shortName} Leads"
        elif home_wins > away_wins:
            if home_wins >= wins_needed:
                series_record = f"({away_wins}-{home_wins}) {home_name_shortName} Wins"
            else:
                series_record = f"({away_wins}-{home_wins}) {home_name_shortName} Leads"
        else:
            series_record = f"({away_wins}-{home_wins})  Tied {away_name}-{home_name}"

        # 스코어 포함 여부에 따른 팀명-스코어 문자열 생성
        is_finished = "F" in status_code
        if is_finished:
            # team_score = f"{away_name} {away_score} - {home_name} {home_score}"
            team_score = ""
        else:
            team_score = f"{away_name_shortName} - {home_name_shortName}"

        # 게임 타입별 시리즈명 매핑
        series_type_map = {
            "F": "WC",  # Wild Card
            "D": "DS",  # Division Series
            "L": "CS",  # League Championship Series
            "W": "WS",  # World Series
        }

        # 시리즈 타입 결정
        series_type = None
        for game_type_char in game_type:
            if game_type_char in series_type_map:
                series_type = series_type_map[game_type_char]
                break

        if not series_type:
            return team_score

        # 시리즈명 생성
        if series_type == "WS":  # World Series는 리그 구분 없음
            series_prefix = f"{series_type}{series_game_number}"
        else:
            series_prefix = f"{league}{series_type}{series_game_number}"

        # 완료된 게임인 경우 시리즈 기록 포함
        if is_finished:
            return f"{series_prefix}{series_record} {team_score}"
        else:
            return f"{series_prefix} {team_score}"

    def get_game_date_time(self, game: Dict) -> tuple:
        status = game.get("status", {}).get("startTimeTBD", False)
        game_start_date = game.get("gameDate", "")  # 2025-10-24T07:33:00Z

        if status is True:
            # 시간이 확정되지 않은 경우, 다음 날짜 00:08:00Z로 설정

            # ISO 형식의 날짜를 파싱
            if game_start_date:
                try:
                    # UTC 시간으로 파싱
                    game_date = datetime.fromisoformat(
                        game_start_date.replace("Z", "+00:00")
                    )
                    # 다음 날로 변경하고 00:08:00Z로 설정
                    next_day = game_date + timedelta(days=1)
                    next_day_0800 = next_day.replace(
                        hour=0, minute=8, second=0, microsecond=0
                    )

                    # UTC로 변환하여 반환
                    utc_time = next_day_0800.astimezone(pytz.UTC)
                    formatted_start_time = utc_time.strftime("%Y%m%dT%H%M%SZ")

                    # 끝나는 시간 (시작 시간 + 3시간)
                    end_time = utc_time + timedelta(hours=3)
                    formatted_end_time = end_time.strftime("%Y%m%dT%H%M%SZ")

                    return formatted_start_time, formatted_end_time
                except Exception as e:
                    print(f"날짜 파싱 오류: {e}")
                    return "", ""
            else:
                return "", ""
        else:
            # 시간이 확정된 경우, 원래 시간 사용
            if game_start_date:
                try:
                    # ISO 형식의 날짜를 파싱하여 반환
                    game_date = datetime.fromisoformat(
                        game_start_date.replace("Z", "+00:00")
                    )
                    utc_time = game_date.astimezone(pytz.UTC)
                    formatted_start_time = utc_time.strftime("%Y%m%dT%H%M%SZ")

                    # 끝나는 시간 (시작 시간 + 3시간)
                    end_time = utc_time + timedelta(hours=3)
                    formatted_end_time = end_time.strftime("%Y%m%dT%H%M%SZ")

                    return formatted_start_time, formatted_end_time
                except Exception as e:
                    print(f"날짜 파싱 오류: {e}")
                    return "", ""
            else:
                return "", ""

    def get_description(self, game: Dict) -> str:
        teams = game.get("teams", {})
        gamesInSeries = game.get("gamesInSeries", {})

        away_team = teams.get("away", {})
        home_team = teams.get("home", {})

        # 기본 정보 추출
        game_type = game.get("gameType", "")
        status_code = game.get("status", {}).get("statusCode", "")
        # 팀 정보 추출

        away_name_shortName = away_team.get("team", {}).get("shortName", "TBD")
        home_name_shortName = home_team.get("team", {}).get("shortName", "TBD")

        away_score = away_team.get("score", "")
        home_score = home_team.get("score", "")

        is_finished = "F" in status_code
        if is_finished:
            return f"{away_name_shortName} {away_score} - {home_name_shortName} {home_score}"
        else:
            return f"{away_name_shortName} - {home_name_shortName}"

    def makeViewModel(self, game: Dict) -> Optional[Dict]:

        summary = self.get_series_name(game)
        start_time, end_time = self.get_game_date_time(game)
        description = self.get_description(game)
        game_info = {
            "game_PK": game.get("gamePk", ""),
            "game_start_time": start_time,
            "game_end_time": end_time,
            "description": description,
            "location": game.get("venue", {}).get("name", "TBD"),
            "summary": summary,
        }

        return game_info

    def generate_ics_content(self, games_data: Optional[Dict]) -> str:
        """ICS 파일 내용을 생성합니다."""
        ics_lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//MLB 2025 Postseason Auto-Updated//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            "X-WR-CALNAME:MLB 2025 Postseason",
            "X-WR-TIMEZONE:UTC",
            "X-PUBLISHED-TTL:PT1H",
        ]

        # 게임 데이터 처리
        for date_data in games_data.get("dates", []):
            for game in date_data.get("games", []):
                # 게임 정보를 ViewModel로 변환
                game_info = self.makeViewModel(game)

                if not game_info:
                    continue

                # 필수 정보 확인
                start_time = game_info.get("game_start_time", "")
                end_time = game_info.get("game_end_time", "")
                summary = game_info.get("summary", "")
                description = game_info.get("description", "")
                location = game_info.get("location", "TBD")
                game_pk = game_info.get("game_PK", "")

                # 시간 정보가 없으면 스킵
                if not start_time or not end_time:
                    print(f"Skipping: Failed to parse time for game {game_pk}")
                    continue

                # 이벤트 생성
                ics_lines.extend(
                    [
                        "",
                        "BEGIN:VEVENT",
                        f"UID:mlb-2025-{game_pk}@mlb.com",
                        f"DTSTAMP:{datetime.now(pytz.UTC).strftime('%Y%m%dT%H%M%SZ')}",
                        f"DTSTART:{start_time}",
                        f"DTEND:{end_time}",
                        f"SUMMARY:{summary}",
                        f"LOCATION:{location}",
                        f"DESCRIPTION:{description}",
                        "STATUS:CONFIRMED",
                        "END:VEVENT",
                    ]
                )

        ics_lines.extend(["", "END:VCALENDAR"])
        return "\n".join(ics_lines)

    def save_ics_file(self, games_data: Optional[Dict]) -> bool:
        """ICS 파일을 저장합니다."""
        try:
            ics_content = self.generate_ics_content(games_data)

            # 절대 경로로 변환
            import os

            absolute_path = os.path.abspath(self.output_file)

            # 파일 저장
            with open(self.output_file, "w", encoding="utf-8") as f:
                f.write(ics_content)

            print(f"ICS 파일이 성공적으로 저장되었습니다:")
            print(f"  파일명: {self.output_file}")
            print(f"  절대 경로: {absolute_path}")

            # 파일 존재 확인
            if os.path.exists(absolute_path):
                file_size = os.path.getsize(absolute_path)
                print(f"  파일 크기: {file_size} bytes")
            else:
                print("  ⚠️ 파일이 존재하지 않습니다!")

            return True

        except Exception as e:
            print(f"ICS 파일 저장 중 오류 발생: {e}")
            return False

    def get_boxscore(self, game_pk: int) -> Optional[Dict]:
        """특정 게임의 박스 스코어를 조회합니다."""
        try:
            # statsapi를 사용하여 박스 스코어 조회
            boxscore_data = statsapi.boxscore(game_pk)
            return boxscore_data
        except Exception as e:
            print(f"박스 스코어 조회 중 오류 발생 (Game PK: {game_pk}): {e}")
            return None


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="MLB 2025 Postseason ICS Updater",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="public/mlb_postseason_2025.ics",
        help="Output ICS file path (default: mlb_postseason_2025.ics)",
    )

    args = parser.parse_args()

    mlb = MLBPostseasonICSMaker(output_file=args.output)
    games = mlb.get_postseason_schedule()

    # ICS 파일 생성
    print(f"\n=== ICS 파일 생성 ===")
    if mlb.save_ics_file(games):
        print("✅ ICS 파일 생성 완료")
    else:
        print("❌ ICS 파일 생성 실패")


if __name__ == "__main__":
    main()
