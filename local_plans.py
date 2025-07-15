"""
부산시청 업무계획 처리 스크립트 - local_plans.py
==============================================
29개 업무계획 PDF → MD 일괄 변환 실행 스크립트

사용법:
    python local_plans.py                    # 전체 처리
    python local_plans.py --test             # 테스트 모드 (첫 3개만)
    python local_plans.py --check            # 상태 확인만
    python local_plans.py --validate         # 결과 검증만
    python local_plans.py --force            # 기존 MD 파일 무시하고 재처리
"""

import os
import sys
import logging
import argparse
import traceback
from pathlib import Path
from datetime import datetime
import time

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent))

try:
    from config import (
        PLANS_PDF_DIR, PLANS_MD_DIR, LOG_FILE,
        OPENAI_API_KEY, IS_LOCAL, IS_DEPLOYMENT
    )
    from plans_processor import PlansProcessor, get_processor_status
    from plans_summarizer import SimplePlansSummarizer
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    print("💡 해결방법: 프로젝트 루트 디렉토리에서 실행하세요")
    sys.exit(1)

# 로깅 설정
def setup_logging():
    """로깅 설정"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    handlers = [logging.StreamHandler(sys.stdout)]
    if LOG_FILE:
        handlers.append(logging.FileHandler(LOG_FILE, encoding='utf-8'))
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=handlers
    )

logger = logging.getLogger(__name__)

class LocalPlansManager:
    """로컬 업무계획 처리 매니저"""
    
    def __init__(self):
        """초기화"""
        self.processor = None
        self._initialize()
        logger.info("✅ LocalPlansManager 초기화 완료")
    
    def _initialize(self):
        """컴포넌트 초기화"""
        try:
            self.processor = PlansProcessor()
            logger.info("✅ 업무계획 프로세서 초기화 완료")
        except Exception as e:
            logger.error(f"❌ 초기화 실패: {e}")
            logger.error(f"상세 오류: {traceback.format_exc()}")
    
    def check_status(self) -> bool:
        """처리 전 상태 확인"""
        try:
            logger.info("🔍 업무계획 처리 환경 확인 중...")
            
            # 기본 상태 확인
            status = get_processor_status()
            
            logger.info("📊 환경 상태:")
            logger.info(f"  🏠 실행 환경: {'로컬' if IS_LOCAL else '배포'}")
            logger.info(f"  🔑 API 키: {'✅ 설정됨' if status.get('api_available') else '❌ 없음'}")
            logger.info(f"  📁 디렉토리: {'✅ 준비됨' if status.get('directories_ready') else '❌ 문제'}")
            logger.info(f"  📄 PDF 파일: {status.get('pdf_files_found', 0)}개 발견")
            logger.info(f"  📋 기존 MD: {status.get('existing_md_files', 0)}개 존재")
            
            # 필수 조건 확인
            issues = []
            
            if not status.get('api_available'):
                issues.append("OpenAI API 키가 설정되지 않음")
            
            if not status.get('directories_ready'):
                issues.append("필수 디렉토리가 준비되지 않음")
            
            if status.get('pdf_files_found', 0) == 0:
                issues.append(f"PDF 파일이 없음 (위치: {PLANS_PDF_DIR})")
            
            if issues:
                logger.warning("⚠️ 발견된 문제:")
                for issue in issues:
                    logger.warning(f"  - {issue}")
                return False
            
            logger.info("✅ 모든 조건이 준비되었습니다!")
            return True
            
        except Exception as e:
            logger.error(f"❌ 상태 확인 실패: {e}")
            return False
    
    def run_full_processing(self, force_reprocess: bool = False) -> bool:
        """전체 업무계획 처리 실행"""
        try:
            if not self.processor:
                logger.error("❌ 프로세서가 초기화되지 않았습니다")
                return False
            
            logger.info("🚀 업무계획 전체 처리 시작")
            
            # PDF 파일 스캔
            pdf_files = self.processor.scan_pdf_files()
            if not pdf_files:
                logger.error("❌ 처리할 PDF 파일이 없습니다")
                return False
            
            # 기존 MD 파일 확인
            if not force_reprocess:
                existing_md = self.processor.check_existing_md_files()
                if existing_md:
                    logger.warning(f"⚠️ 기존 MD 파일 {len(existing_md)}개 발견")
                    logger.warning("기존 파일을 덮어쓰려면 --force 옵션을 사용하세요")
                    
                    user_input = input("계속 진행하시겠습니까? (y/N): ").strip().lower()
                    if user_input != 'y':
                        logger.info("👋 사용자에 의해 취소되었습니다")
                        return False
            
            # 처리 실행
            start_time = time.time()
            generated_files = self.processor.run_processing(pdf_files)
            end_time = time.time()
            
            # 결과 요약
            processing_time = end_time - start_time
            minutes = int(processing_time // 60)
            seconds = int(processing_time % 60)
            
            self.processor.print_summary_report(generated_files)
            
            logger.info(f"⏱️ 총 처리 시간: {minutes}분 {seconds}초")
            logger.info(f"📊 성공률: {len(generated_files)}/{len(pdf_files)} ({(len(generated_files)/len(pdf_files)*100):.1f}%)")
            
            return len(generated_files) > 0
            
        except KeyboardInterrupt:
            logger.info("⏹️ 사용자에 의해 중단되었습니다")
            return False
        except Exception as e:
            logger.error(f"❌ 전체 처리 실패: {e}")
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return False
    
    def run_test_processing(self, test_count: int = 3) -> bool:
        """테스트 처리 (처음 몇 개만)"""
        try:
            if not self.processor:
                logger.error("❌ 프로세서가 초기화되지 않았습니다")
                return False
            
            logger.info(f"🧪 테스트 모드: 처음 {test_count}개 파일만 처리")
            
            # PDF 파일 스캔
            pdf_files = self.processor.scan_pdf_files()
            if not pdf_files:
                logger.error("❌ 처리할 PDF 파일이 없습니다")
                return False
            
            # 테스트용 파일 선택
            test_files = pdf_files[:test_count]
            logger.info(f"📋 테스트 대상:")
            for i, file_info in enumerate(test_files, 1):
                logger.info(f"  {i}. {file_info['department']} ({file_info['category']})")
            
            # 처리 실행
            generated_files = self.processor.run_processing(test_files)
            
            logger.info(f"🧪 테스트 결과: {len(generated_files)}/{len(test_files)}개 성공")
            
            return len(generated_files) > 0
            
        except Exception as e:
            logger.error(f"❌ 테스트 처리 실패: {e}")
            return False
    
    def validate_results(self) -> bool:
        """처리 결과 검증"""
        try:
            if not self.processor:
                logger.error("❌ 프로세서가 초기화되지 않았습니다")
                return False
            
            logger.info("🔍 처리 결과 검증 중...")
            
            validation_result = self.processor.validate_results()
            
            logger.info("📊 검증 결과:")
            logger.info(f"  📄 PDF 파일: {validation_result.get('pdf_count', 0)}개")
            logger.info(f"  📋 MD 파일: {validation_result.get('md_count', 0)}개")
            logger.info(f"  ✅ 성공률: {validation_result.get('success_rate', 0):.1f}%")
            
            if validation_result.get('missing_departments'):
                logger.warning("⚠️ 누락된 부서:")
                for dept in validation_result['missing_departments']:
                    logger.warning(f"  - {dept}")
            
            if validation_result.get('issues'):
                logger.warning("⚠️ 발견된 문제:")
                for issue in validation_result['issues']:
                    logger.warning(f"  - {issue}")
                return False
            
            logger.info("✅ 모든 검증을 통과했습니다!")
            return True
            
        except Exception as e:
            logger.error(f"❌ 결과 검증 실패: {e}")
            return False

def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(description="부산시청 업무계획 처리 스크립트")
    
    # 실행 모드
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--test', action='store_true', help='테스트 모드 (처음 3개만)')
    group.add_argument('--check', action='store_true', help='상태 확인만')
    group.add_argument('--validate', action='store_true', help='결과 검증만')
    
    # 옵션
    parser.add_argument('--force', action='store_true', help='기존 MD 파일 무시하고 재처리')
    parser.add_argument('--test-count', type=int, default=3, help='테스트 모드에서 처리할 파일 수')
    
    return parser.parse_args()

def print_welcome_message():
    """환영 메시지 출력"""
    print("="*60)
    print("🏛️ 부산시청 업무계획 처리 시스템")
    print("="*60)
    print(f"📅 실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 PDF 경로: {PLANS_PDF_DIR}")
    print(f"📋 MD 경로: {PLANS_MD_DIR}")
    print(f"🔑 API 상태: {'✅ 사용 가능' if OPENAI_API_KEY else '❌ 설정 필요'}")
    print("-"*60)

def print_completion_message(success: bool):
    """완료 메시지 출력"""
    print("-"*60)
    if success:
        print("🎉 업무계획 처리가 성공적으로 완료되었습니다!")
        print(f"📋 결과 확인: {PLANS_MD_DIR}")
        print("🌐 앱 실행: streamlit run app.py")
    else:
        print("❌ 업무계획 처리 중 오류가 발생했습니다.")
        print("💡 로그를 확인하여 문제를 해결해주세요.")
    print("="*60)

def main():
    """메인 실행 함수"""
    setup_logging()
    print_welcome_message()
    
    try:
        # 명령행 인수 파싱
        args = parse_arguments()
        
        # 매니저 초기화
        manager = LocalPlansManager()
        
        success = False
        
        if args.check:
            # 상태 확인만
            logger.info("🔍 시스템 상태 확인 모드")
            success = manager.check_status()
            
        elif args.validate:
            # 결과 검증만
            logger.info("📊 결과 검증 모드")
            success = manager.validate_results()
            
        elif args.test:
            # 테스트 모드
            logger.info(f"🧪 테스트 모드 (파일 {args.test_count}개)")
            if manager.check_status():
                success = manager.run_test_processing(args.test_count)
            
        else:
            # 전체 처리 모드
            logger.info("🚀 전체 처리 모드")
            if manager.check_status():
                success = manager.run_full_processing(args.force)
        
        print_completion_message(success)
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("⏹️ 사용자에 의해 중단되었습니다")
        print("\n👋 작업이 중단되었습니다.")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류: {e}")
        logger.error(f"상세 오류: {traceback.format_exc()}")
        print_completion_message(False)
        sys.exit(1)

if __name__ == "__main__":
    main()