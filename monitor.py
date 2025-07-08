"""
부산시청 보도자료 포털 - 핵심 모니터링 시스템
====================================================
PDF↔MD 파일 개수 일치 및 기본 검증만 수행

사용법:
    python monitor.py                    # 전체 검증
    python monitor.py --check-only       # 조용한 모드
    python monitor.py --json-output      # JSON 결과 파일 생성
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent))

try:
    from config import PDF_DIR, MD_DIR, get_env_info, validate_config
except ImportError as e:
    print(f"❌ 설정 모듈 import 실패: {e}")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

class SimpleMonitor:
    """간단한 모니터링 시스템 - 핵심 기능만"""
    
    def __init__(self):
        self.pdf_dir = PDF_DIR
        self.md_dir = MD_DIR
        self.issues = []
        self.stats = {}
    
    def check_file_consistency(self) -> Dict:
        """🔧 핵심: PDF와 MD 파일 개수 일치 확인"""
        logger.info("📊 파일 일관성 검사...")
        
        try:
            # 파일 개수 확인
            pdf_files = list(self.pdf_dir.glob("*.pdf")) if self.pdf_dir.exists() else []
            md_files = list(self.md_dir.glob("*.md")) if self.md_dir.exists() else []
            
            pdf_count = len(pdf_files)
            md_count = len(md_files)
            
            # 일관성 검사
            is_consistent = pdf_count == md_count
            success_rate = (md_count / pdf_count * 100) if pdf_count > 0 else 0
            
            result = {
                'pdf_count': pdf_count,
                'md_count': md_count,
                'is_consistent': is_consistent,
                'success_rate': success_rate
            }
            
            # 결과 평가
            if is_consistent:
                logger.info(f"✅ 파일 일관성 OK: PDF {pdf_count}개 = MD {md_count}개")
            else:
                missing = pdf_count - md_count
                self.issues.append(f"파일 불일치: PDF {pdf_count}개, MD {md_count}개 (차이: {missing}개)")
                logger.error(f"❌ 파일 불일치: PDF {pdf_count}개 ≠ MD {md_count}개")
            
            # 성공률 체크
            if success_rate < 90 and pdf_count > 0:
                self.issues.append(f"변환 성공률 낮음: {success_rate:.1f}%")
                logger.warning(f"⚠️ 변환 성공률: {success_rate:.1f}%")
            
            return result
            
        except Exception as e:
            error_msg = f"파일 검사 실패: {e}"
            self.issues.append(error_msg)
            logger.error(f"❌ {error_msg}")
            return {'error': str(e)}
    
    def check_recent_activity(self, hours: int = 24) -> Dict:
        """최근 활동 확인"""
        logger.info(f"🕐 최근 {hours}시간 활동 체크...")
        
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            recent_files = 0
            
            # 최근 수정된 파일 확인
            for directory in [self.pdf_dir, self.md_dir]:
                if directory.exists():
                    for file_path in directory.glob("*"):
                        if file_path.is_file():
                            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if mtime >= cutoff_time:
                                recent_files += 1
            
            has_activity = recent_files > 0
            
            if not has_activity:
                logger.warning(f"⚠️ 최근 {hours}시간 동안 새 파일 없음")
            else:
                logger.info(f"✅ 최근 활동: {recent_files}개 파일")
            
            return {
                'has_activity': has_activity,
                'recent_files': recent_files,
                'period_hours': hours
            }
            
        except Exception as e:
            logger.error(f"❌ 활동 체크 실패: {e}")
            return {'error': str(e)}
    
    def check_app_health(self) -> Dict:
        """Streamlit 앱 기본 접근성 체크"""
        streamlit_url = os.getenv("STREAMLIT_URL", "")
        
        if not streamlit_url:
            logger.info("📱 Streamlit URL 미설정 - 앱 체크 스킵")
            return {'skipped': True}
        
        logger.info("🌐 앱 접근성 체크...")
        
        try:
            response = requests.get(streamlit_url, timeout=15)
            is_healthy = response.status_code == 200
            
            if is_healthy:
                logger.info(f"✅ 앱 접근 가능: {response.status_code}")
            else:
                self.issues.append(f"앱 접근 불가: HTTP {response.status_code}")
                logger.error(f"❌ 앱 접근 불가: {response.status_code}")
            
            return {
                'url': streamlit_url,
                'status_code': response.status_code,
                'is_healthy': is_healthy,
                'response_time': response.elapsed.total_seconds()
            }
            
        except Exception as e:
            self.issues.append(f"앱 체크 실패: {e}")
            logger.error(f"❌ 앱 체크 실패: {e}")
            return {'error': str(e)}
    
    def check_basic_setup(self) -> Dict:
        """기본 설정 확인"""
        logger.info("⚙️ 기본 설정 체크...")
        
        try:
            # 디렉토리 존재 확인
            pdf_exists = self.pdf_dir.exists()
            md_exists = self.md_dir.exists()
            
            if not pdf_exists:
                self.issues.append("PDF 디렉토리 없음")
            if not md_exists:
                self.issues.append("MD 디렉토리 없음")
            
            # config 검증
            config_result = validate_config()
            
            return {
                'pdf_dir_exists': pdf_exists,
                'md_dir_exists': md_exists,
                'config_valid': config_result['valid'],
                'config_message': config_result['message']
            }
            
        except Exception as e:
            logger.error(f"❌ 설정 체크 실패: {e}")
            return {'error': str(e)}
    
    def run_monitoring(self) -> Dict:
        """전체 모니터링 실행"""
        logger.info("🚀 모니터링 시작")
        start_time = datetime.now()
        
        # 각 체크 실행
        self.stats['file_consistency'] = self.check_file_consistency()
        self.stats['recent_activity'] = self.check_recent_activity()
        self.stats['app_health'] = self.check_app_health()
        self.stats['basic_setup'] = self.check_basic_setup()
        
        # 전체 평가
        has_critical_issues = len(self.issues) > 0
        status = "FAIL" if has_critical_issues else "PASS"
        
        summary = {
            'status': status,
            'issues': self.issues,
            'issue_count': len(self.issues),
            'timestamp': start_time.isoformat(),
            'duration': (datetime.now() - start_time).total_seconds(),
            'stats': self.stats
        }
        
        # 결과 출력
        logger.info(f"📊 모니터링 완료: {status}")
        if self.issues:
            logger.error(f"❌ 발견된 문제: {len(self.issues)}개")
            for issue in self.issues:
                logger.error(f"   - {issue}")
        else:
            logger.info("✅ 모든 검사 통과")
        
        return summary
    
    def print_simple_report(self, summary: Dict):
        """간단한 리포트 출력"""
        print("\n" + "="*50)
        print("🏢 부산시청 보도자료 포털 모니터링")
        print("="*50)
        print(f"상태: {summary['status']}")
        print(f"시간: {summary['timestamp']}")
        print(f"소요시간: {summary['duration']:.1f}초")
        print()
        
        # 통계 출력
        stats = summary['stats']
        if 'file_consistency' in stats:
            fc = stats['file_consistency']
            if 'pdf_count' in fc:
                print(f"📁 PDF 파일: {fc['pdf_count']}개")
                print(f"📝 MD 파일: {fc['md_count']}개")
                print(f"📊 일관성: {'✅' if fc['is_consistent'] else '❌'}")
        
        # 문제점 출력
        if summary['issues']:
            print("\n🚨 발견된 문제:")
            for issue in summary['issues']:
                print(f"   - {issue}")
        else:
            print("\n✅ 모든 검사 정상")
        
        print("="*50)

def main():
    """메인 실행"""
    import argparse
    
    parser = argparse.ArgumentParser(description="부산시청 포털 모니터링")
    parser.add_argument('--check-only', action='store_true', help='조용한 모드')
    parser.add_argument('--json-output', action='store_true', help='JSON 결과 파일 생성')
    
    args = parser.parse_args()
    
    try:
        monitor = SimpleMonitor()
        summary = monitor.run_monitoring()
        
        # 리포트 출력
        if not args.check_only:
            monitor.print_simple_report(summary)
        
        # JSON 파일 생성
        if args.json_output:
            with open('monitoring_result.json', 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2, default=str)
            logger.info("📄 결과를 monitoring_result.json에 저장")
        
        # 종료 코드 설정
        if summary['status'] == 'FAIL':
            sys.exit(1)  # 문제 있음
        else:
            sys.exit(0)  # 정상
        
    except Exception as e:
        logger.error(f"❌ 모니터링 실행 실패: {e}")
        sys.exit(2)  # 시스템 오류

if __name__ == "__main__":
    main()