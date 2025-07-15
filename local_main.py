"""
부산시청 보도자료 포털 - 로컬 통합 실행 스크립트
=================================================
크롤링 → 요약까지 원클릭 실행 (신규 PDF만 처리)

사용법:
    python local_main.py                    # 전체 실행
    python local_main.py --crawl-only       # 크롤링만
    python local_main.py --summarize-only   # 요약만
    python local_main.py --test             # 테스트 모드 (2페이지)
    python local_main.py --max-pages 5      # 최대 페이지 수 지정
"""

import os
import sys
import logging
import argparse
import traceback
from pathlib import Path
from typing import List, Dict, Optional

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent))

# 컴포넌트 import
try:
    from core.crawler import BusanNewsCrawler
    from core.summarizer import BusanNewsSummarizer
    from config import (
        LOG_FILE, PDF_DIR, MD_DIR,
        OPENAI_API_KEY, IS_LOCAL, IS_DEPLOYMENT
    )
except ImportError as e:
    print(f"❌ 모듈 import 실패: {e}")
    sys.exit(1)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class LocalPipelineManager:
    """로컬 파이프라인 매니저 (신규 PDF만 처리)"""
    
    def __init__(self):
        """초기화"""
        self.crawler = None
        self.summarizer = None
        
        # 디렉토리 생성
        self._create_directories()
        
        # 컴포넌트 초기화
        self._initialize_components()
    
    def _create_directories(self):
        """필요한 디렉토리 생성"""
        directories = [PDF_DIR, MD_DIR]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 디렉토리 확인: {directory}")
    
    def _initialize_components(self):
        """컴포넌트 초기화"""
        try:
            # 크롤러 초기화
            self.crawler = BusanNewsCrawler()
            logger.info("✅ 크롤러 초기화 완료")
            
            # 요약기 초기화 (API 키가 있을 때만)
            if OPENAI_API_KEY:
                self.summarizer = BusanNewsSummarizer()
                logger.info("✅ 요약기 초기화 완료")
            else:
                logger.warning("⚠️ OpenAI API 키가 없어 요약기를 비활성화합니다")
                
        except Exception as e:
            logger.error(f"❌ 컴포넌트 초기화 실패: {e}")
            logger.error(f"상세 오류: {traceback.format_exc()}")
    
    def run_crawling(self, max_pages: int = 5) -> List[Dict]:
        """보도자료 크롤링 실행"""
        logger.info(f"🕷️ 부산시 보도자료 크롤링 시작 (최대 {max_pages}페이지)...")
        
        try:
            if not self.crawler:
                logger.error("❌ 크롤러가 초기화되지 않았습니다")
                return []
            
            # 크롤링 실행
            crawler_results = self.crawler.crawl_news(max_pages=max_pages)
            
            if crawler_results:
                logger.info(f"✅ 크롤링 완료: {len(crawler_results)}개 파일 처리")
                
                # 🔧 신규/기존 파일 분류
                new_files = [r for r in crawler_results if r.get('status') == 'downloaded']
                existing_files = [r for r in crawler_results if r.get('status') in ['already_exists', 'already_exists_similar']]
                
                logger.info(f"   📥 신규 다운로드: {len(new_files)}개")
                logger.info(f"   📋 기존 파일: {len(existing_files)}개")
                
                # 결과 요약 출력 (신규 파일만)
                for result in new_files[:3]:
                    logger.info(f"📄 신규: {result['filename']} → {result['url']}")
                
                if len(new_files) > 3:
                    logger.info(f"... 외 {len(new_files) - 3}개 신규 파일")
            else:
                logger.warning("⚠️ 크롤링 결과가 없습니다")
            
            return crawler_results
            
        except Exception as e:
            logger.error(f"❌ 크롤링 실패: {e}")
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return []
    
    def run_summarization(self, crawler_results: List[Dict] = None) -> List[str]:
        """🔧 신규 크롤링된 PDF만 요약 생성"""
        logger.info("📝 보도자료 요약 생성 시작...")
        
        if not self.summarizer:
            logger.warning("⚠️ 요약기가 없습니다. 기존 MD 파일을 사용합니다.")
            existing_md_files = list(Path(MD_DIR).glob("*.md"))
            return [str(f) for f in existing_md_files]
        
        if not crawler_results:
            logger.warning("⚠️ 크롤러 결과가 없어 요약을 건너뜁니다")
            return []
        
        try:
            # 🔧 신규 다운로드된 PDF만 필터링
            new_pdfs = [
                result for result in crawler_results 
                if result.get('status') == 'downloaded'  # 새로 다운로드된 것만
            ]
            
            if not new_pdfs:
                logger.info("📋 신규 다운로드된 PDF가 없어 요약을 건너뜁니다")
                
                # 기존 MD 파일 목록 반환
                existing_md_files = list(Path(MD_DIR).glob("*.md"))
                logger.info(f"📄 기존 MD 파일: {len(existing_md_files)}개")
                return [str(f) for f in existing_md_files]
            
            logger.info(f"📋 신규 PDF 파일: {len(new_pdfs)}개 요약 생성 시작")
            processed_files = []
            
            for idx, pdf_info in enumerate(new_pdfs, 1):
                try:
                    pdf_path = pdf_info['path']
                    source_url = pdf_info['url']
                    pdf_filename = pdf_info['filename']
                    
                    logger.info(f"[{idx}/{len(new_pdfs)}] 🔗 신규 처리: {pdf_filename}")
                    logger.info(f"   📂 파일: {pdf_path}")
                    logger.info(f"   🌐 URL: {source_url}")
                    
                    # PDF 처리
                    md_file = self.summarizer.process_pdf_file(pdf_path, source_url)
                    
                    if md_file:
                        processed_files.append(md_file)
                        logger.info(f"✅ 요약 완료: {Path(md_file).name}")
                    else:
                        logger.warning(f"⚠️ 요약 실패: {pdf_filename}")
                
                except Exception as e:
                    logger.error(f"❌ PDF 처리 실패 {pdf_info.get('filename', 'unknown')}: {e}")
                    continue
            
            logger.info(f"🎉 신규 요약 생성 완료: {len(processed_files)}개")
            
            # 전체 MD 파일 목록 반환 (기존 + 신규)
            all_md_files = list(Path(MD_DIR).glob("*.md"))
            logger.info(f"📊 전체 MD 파일: {len(all_md_files)}개")
            
            return [str(f) for f in all_md_files]
            
        except Exception as e:
            logger.error(f"❌ 요약 생성 실패: {e}")
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return []

def parse_arguments():
    """명령행 인수 파싱"""
    parser = argparse.ArgumentParser(description="부산시청 보도자료 포털 로컬 실행")
    
    # 실행 모드
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--crawl-only', action='store_true', help='크롤링만 실행')
    group.add_argument('--summarize-only', action='store_true', help='요약만 실행')
    
    # 설정
    parser.add_argument('--max-pages', type=int, default=5, help='최대 크롤링 페이지 수 (기본: 5)')
    parser.add_argument('--test', action='store_true', help='테스트 모드 (2페이지만)')
    
    return parser.parse_args()

def main():
    """메인 실행 함수"""
    try:
        logger.info("🚀 부산시청 보도자료 포털 로컬 실행 시작")
        logger.info(f"📍 실행 환경: {'로컬' if IS_LOCAL else '배포'}")
        
        # 명령행 인수 파싱
        args = parse_arguments()
        
        # 파이프라인 매니저 초기화
        manager = LocalPipelineManager()
        
        # 실행 모드에 따른 처리
        if args.crawl_only:
            # 크롤링만 실행
            max_pages = 2 if args.test else args.max_pages
            crawler_results = manager.run_crawling(max_pages)
            
            logger.info("✅ 크롤링 작업 완료!")
            
            # 🔧 신규/기존 파일 통계
            new_count = len([r for r in crawler_results if r.get('status') == 'downloaded'])
            existing_count = len(crawler_results) - new_count
            
            logger.info(f"📊 결과: 총 {len(crawler_results)}개 (신규 {new_count}개, 기존 {existing_count}개)")
            
        elif args.summarize_only:
            # 요약만 실행 (기존 PDF 대상)
            md_files = manager.run_summarization()
            
            logger.info("✅ 요약 작업 완료!")
            logger.info(f"📊 결과: {len(md_files)}개 MD 파일")
            
        else:
            # 🔧 전체 파이프라인 실행 (신규 PDF만 요약)
            max_pages = 2 if args.test else args.max_pages
            
            logger.info("🔄 전체 파이프라인 실행 시작 (크롤링 + 신규 PDF 요약)")
            
            # 1. 크롤링
            logger.info("1️⃣ 크롤링 단계")
            crawler_results = manager.run_crawling(max_pages)
            
            # 2. 신규 PDF만 요약 생성
            logger.info("2️⃣ 신규 PDF 요약 생성 단계")
            md_files = manager.run_summarization(crawler_results)
            
            # 결과 요약
            new_pdfs = len([r for r in crawler_results if r.get('status') == 'downloaded'])
            existing_pdfs = len(crawler_results) - new_pdfs
            
            logger.info("🎉 전체 파이프라인 완료!")
            logger.info(f"📊 최종 결과:")
            logger.info(f"   - 크롤링: {len(crawler_results)}개 PDF (신규 {new_pdfs}개, 기존 {existing_pdfs}개)")
            logger.info(f"   - 요약: {len(md_files)}개 MD 파일")
            logger.info(f"   - 신규 요약: {new_pdfs}개 (신규 PDF만 처리)")
        
        logger.info("✅ 모든 작업이 완료되었습니다!")
        
    except KeyboardInterrupt:
        logger.info("⏹️ 사용자에 의해 중단되었습니다")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"❌ 파이프라인 실행 실패: {e}")
        logger.error(f"상세 오류: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()