"""
부산시청 업무계획 파이프라인 매니저 - PlansProcessor
=================================================
업무계획 PDF들을 일괄 처리하는 파이프라인 관리 클래스

주요 기능:
- 29개 업무계획 PDF 일괄 처리
- 진행상황 모니터링
- 부서별 분류 자동화
- 오류 처리 및 재시도
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import time

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent))

from config import (
    PLANS_PDF_DIR, PLANS_MD_DIR, PLAN_DEPARTMENTS,
    OPENAI_API_KEY, IS_LOCAL
)
from plans_summarizer import SimplePlansSummarizer

logger = logging.getLogger(__name__)

def get_priority(item):
    dept = item.get('department', '')
    if dept.startswith("부산광역시"):
        return ''  # 무조건 맨 앞
    return dept or '~~~'

class PlansProcessor:
    """업무계획 파이프라인 매니저"""
    
    def __init__(self):
        """초기화"""
        self.pdf_dir = PLANS_PDF_DIR
        self.md_dir = PLANS_MD_DIR
        self.summarizer = None
        
        # 디렉토리 생성
        self._create_directories()
        
        # 컴포넌트 초기화
        self._initialize_components()
        
        logger.info("✅ PlansProcessor 초기화 완료")
    
    def _create_directories(self):
        """필요한 디렉토리 생성"""
        directories = [self.pdf_dir, self.md_dir]
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
            logger.info(f"📁 디렉토리 확인: {directory}")
    
    def _initialize_components(self):
        """컴포넌트 초기화"""
        try:
            if OPENAI_API_KEY:
                self.summarizer = SimplePlansSummarizer()
                logger.info("✅ 업무계획 요약기 초기화 완료")
            else:
                logger.warning("⚠️ OpenAI API 키가 없어 요약기를 비활성화합니다")
                
        except Exception as e:
            logger.error(f"❌ 컴포넌트 초기화 실패: {e}")
            logger.error(f"상세 오류: {traceback.format_exc()}")
    
    def scan_pdf_files(self) -> List[Dict]:
        """업무계획 PDF 파일 스캔"""
        try:
            pdf_files = list(Path(self.pdf_dir).glob("*.pdf"))
            
            if not pdf_files:
                logger.warning(f"⚠️ PDF 파일이 없습니다: {self.pdf_dir}")
                return []
            
            logger.info(f"📋 발견된 PDF 파일: {len(pdf_files)}개")
            
            file_info_list = []
            for pdf_file in pdf_files:
                try:
                    # 파일 기본 정보
                    file_size = pdf_file.stat().st_size
                    
                    # 부서명 추출
                    department = self._extract_department_from_filename(pdf_file.name)
                    
                    # 분류 추출
                    category = self._get_department_category(department)
                    
                    file_info = {
                        'filename': pdf_file.name,
                        'path': str(pdf_file),
                        'size': file_size,
                        'department': department,
                        'category': category,
                        'size_mb': round(file_size / (1024 * 1024), 2)
                    }
                    
                    file_info_list.append(file_info)
                    
                except Exception as e:
                    logger.warning(f"⚠️ 파일 정보 추출 실패 {pdf_file.name}: {e}")
                    continue
            
            # 부서명순 정렬
            file_info_list.sort(key=get_priority)
            
            return file_info_list
            
        except Exception as e:
            logger.error(f"❌ PDF 파일 스캔 실패: {e}")
            return []
    
    def _extract_department_from_filename(self, filename: str) -> str:
        """파일명에서 부서명 추출"""
        try:
            # "2025년 부서명 주요업무계획.pdf" 형태에서 부서명 추출
            if "주요업무계획" in filename:
                dept_part = filename.replace("2025년 ", "").replace(" 주요업무계획.pdf", "")
                return dept_part
            
            return "미분류"
            
        except Exception as e:
            logger.error(f"부서명 추출 실패: {e}")
            return "미분류"
    
    def _get_department_category(self, department: str) -> str:
        """부서명으로부터 분류 카테고리 찾기"""
        for display_name, dept_list in PLAN_DEPARTMENTS:
            if dept_list != "전체" and any(dept in department for dept in dept_list):
                # "🏛️ 기획감사" -> "기획감사" 추출
                return display_name.split(' ', 1)[1] if ' ' in display_name else display_name
        
        return "전체"
    
    def check_existing_md_files(self) -> List[str]:
        """기존 MD 파일 확인"""
        try:
            existing_md_files = list(Path(self.md_dir).glob("*.md"))
            existing_names = [md_file.name for md_file in existing_md_files]
            
            logger.info(f"📄 기존 MD 파일: {len(existing_md_files)}개")
            
            if existing_md_files:
                logger.info("기존 MD 파일 목록:")
                for md_file in existing_names[:5]:  # 처음 5개만 표시
                    logger.info(f"  - {md_file}")
                if len(existing_names) > 5:
                    logger.info(f"  ... 외 {len(existing_names) - 5}개")
            
            return existing_names
            
        except Exception as e:
            logger.error(f"❌ 기존 MD 파일 확인 실패: {e}")
            return []
    
    def generate_processing_plan(self, pdf_files: List[Dict]) -> Dict:
        """처리 계획 생성"""
        try:
            # 분류별 통계
            category_stats = {}
            for file_info in pdf_files:
                category = file_info['category']
                category_stats[category] = category_stats.get(category, 0) + 1
            
            # 예상 처리 시간 계산 (파일당 평균 30초 + API 대기 3초)
            estimated_time_per_file = 33  # 초
            total_estimated_time = len(pdf_files) * estimated_time_per_file
            estimated_minutes = total_estimated_time // 60
            
            processing_plan = {
                'total_files': len(pdf_files),
                'category_distribution': category_stats,
                'estimated_time_minutes': estimated_minutes,
                'estimated_time_seconds': total_estimated_time,
                'files_by_category': {}
            }
            
            # 분류별 파일 목록
            for file_info in pdf_files:
                category = file_info['category']
                if category not in processing_plan['files_by_category']:
                    processing_plan['files_by_category'][category] = []
                processing_plan['files_by_category'][category].append(file_info)
            
            return processing_plan
            
        except Exception as e:
            logger.error(f"❌ 처리 계획 생성 실패: {e}")
            return {}
    
    def run_processing(self, pdf_files: List[Dict] = None) -> List[str]:
        """업무계획 PDF 일괄 처리 실행"""
        try:
            if not self.summarizer:
                logger.error("❌ 요약기가 초기화되지 않았습니다")
                return []
            
            if pdf_files is None:
                pdf_files = self.scan_pdf_files()
            
            if not pdf_files:
                logger.warning("⚠️ 처리할 PDF 파일이 없습니다")
                return []
            
            logger.info(f"🚀 업무계획 PDF 일괄 처리 시작: {len(pdf_files)}개")
            
            # 처리 계획 출력
            plan = self.generate_processing_plan(pdf_files)
            if plan:
                logger.info(f"📊 처리 계획:")
                logger.info(f"  - 총 파일 수: {plan['total_files']}개")
                logger.info(f"  - 예상 소요 시간: {plan['estimated_time_minutes']}분")
                logger.info(f"  - 분류별 분포:")
                for category, count in plan['category_distribution'].items():
                    logger.info(f"    * {category}: {count}개")
            
            generated_files = []
            start_time = time.time()
            
            for idx, file_info in enumerate(pdf_files, 1):
                try:
                    pdf_path = file_info['path']
                    department = file_info['department']
                    category = file_info['category']
                    
                    logger.info(f"[{idx}/{len(pdf_files)}] 🏛️ 처리 중: {department}")
                    logger.info(f"  📂 파일: {file_info['filename']}")
                    logger.info(f"  📋 분류: {category}")
                    logger.info(f"  💾 크기: {file_info['size_mb']}MB")
                    
                    # PDF 처리
                    file_start_time = time.time()
                    md_file = self.summarizer.process_single_pdf(pdf_path)
                    file_end_time = time.time()
                    
                    if md_file:
                        generated_files.append(md_file)
                        processing_time = round(file_end_time - file_start_time, 1)
                        logger.info(f"✅ 완료: {Path(md_file).name} ({processing_time}초)")
                    else:
                        logger.warning(f"⚠️ 처리 실패: {department}")
                    
                    # 진행률 표시
                    progress = (idx / len(pdf_files)) * 100
                    elapsed_time = time.time() - start_time
                    remaining_files = len(pdf_files) - idx
                    if idx > 0:
                        avg_time_per_file = elapsed_time / idx
                        eta_seconds = remaining_files * avg_time_per_file
                        eta_minutes = int(eta_seconds // 60)
                        logger.info(f"📊 진행률: {progress:.1f}% (남은 시간: 약 {eta_minutes}분)")
                    
                except Exception as e:
                    logger.error(f"❌ 파일 처리 실패 {file_info.get('filename', 'unknown')}: {e}")
                    continue
            
            total_time = time.time() - start_time
            total_minutes = int(total_time // 60)
            
            logger.info(f"🎉 업무계획 일괄 처리 완료!")
            logger.info(f"📊 최종 결과:")
            logger.info(f"  - 처리된 파일: {len(generated_files)}/{len(pdf_files)}개")
            logger.info(f"  - 총 소요 시간: {total_minutes}분 {int(total_time % 60)}초")
            logger.info(f"  - 저장 위치: {self.md_dir}")
            
            return generated_files
            
        except Exception as e:
            logger.error(f"❌ 일괄 처리 실패: {e}")
            logger.error(f"상세 오류: {traceback.format_exc()}")
            return []
    
    def print_summary_report(self, generated_files: List[str]):
        """처리 결과 요약 보고서 출력"""
        try:
            if not generated_files:
                logger.info("📋 생성된 파일이 없습니다.")
                return
            
            logger.info("="*60)
            logger.info("📊 업무계획 처리 결과 요약")
            logger.info("="*60)
            
            # 분류별 통계
            category_counts = {}
            for md_file in generated_files:
                try:
                    # 파일명에서 부서명 추출하여 분류 확인
                    filename = Path(md_file).name
                    if "2025년_" in filename and "_업무계획.md" in filename:
                        dept_part = filename.replace("2025년_", "").replace("_업무계획.md", "")
                        category = self._get_department_category(dept_part)
                        category_counts[category] = category_counts.get(category, 0) + 1
                except:
                    continue
            
            logger.info(f"총 생성된 MD 파일: {len(generated_files)}개")
            logger.info(f"분류별 분포:")
            for category, count in sorted(category_counts.items()):
                logger.info(f"  - {category}: {count}개")
            
            logger.info(f"저장 경로: {self.md_dir}")
            
            # 샘플 파일 목록
            logger.info("생성된 파일 샘플:")
            for i, md_file in enumerate(generated_files[:5], 1):
                filename = Path(md_file).name
                logger.info(f"  {i}. {filename}")
            
            if len(generated_files) > 5:
                logger.info(f"  ... 외 {len(generated_files) - 5}개")
            
            logger.info("="*60)
            
        except Exception as e:
            logger.error(f"❌ 요약 보고서 생성 실패: {e}")
    
    def validate_results(self) -> Dict:
        """처리 결과 검증"""
        try:
            pdf_files = self.scan_pdf_files()
            md_files = list(Path(self.md_dir).glob("*.md"))
            
            validation_result = {
                'pdf_count': len(pdf_files),
                'md_count': len(md_files),
                'success_rate': 0.0,
                'missing_departments': [],
                'issues': []
            }
            
            if len(pdf_files) > 0:
                validation_result['success_rate'] = (len(md_files) / len(pdf_files)) * 100
            
            # 누락된 부서 확인
            pdf_departments = {file_info['department'] for file_info in pdf_files}
            
            md_departments = set()
            for md_file in md_files:
                try:
                    filename = md_file.name
                    if "2025년_" in filename and "_업무계획.md" in filename:
                        dept_part = filename.replace("2025년_", "").replace("_업무계획.md", "")
                        md_departments.add(dept_part)
                except:
                    continue
            
            validation_result['missing_departments'] = list(pdf_departments - md_departments)
            
            # 문제점 체크
            if validation_result['success_rate'] < 100:
                validation_result['issues'].append(f"처리 성공률 {validation_result['success_rate']:.1f}%")
            
            if validation_result['missing_departments']:
                validation_result['issues'].append(f"누락된 부서: {', '.join(validation_result['missing_departments'])}")
            
            return validation_result
            
        except Exception as e:
            logger.error(f"❌ 결과 검증 실패: {e}")
            return {'issues': [f"검증 실패: {e}"]}


# 유틸리티 함수
def get_processor_status():
    """프로세서 상태 확인"""
    try:
        processor = PlansProcessor()
        
        pdf_files = processor.scan_pdf_files()
        existing_md = processor.check_existing_md_files()
        
        status = {
            'pdf_files_found': len(pdf_files),
            'existing_md_files': len(existing_md),
            'api_available': OPENAI_API_KEY is not None,
            'directories_ready': processor.pdf_dir.exists() and processor.md_dir.exists()
        }
        
        return status
        
    except Exception as e:
        logger.error(f"❌ 상태 확인 실패: {e}")
        return {'error': str(e)}


# 테스트 함수
def test_processor():
    """프로세서 테스트"""
    print("🧪 업무계획 프로세서 테스트 시작...")
    
    try:
        processor = PlansProcessor()
        
        # 상태 확인
        status = get_processor_status()
        print(f"📊 상태:")
        for key, value in status.items():
            print(f"  - {key}: {value}")
        
        # PDF 파일 스캔
        pdf_files = processor.scan_pdf_files()
        if pdf_files:
            print(f"📋 발견된 PDF 파일: {len(pdf_files)}개")
            for file_info in pdf_files[:3]:
                print(f"  - {file_info['department']} ({file_info['category']})")
        
        # 처리 계획
        if pdf_files:
            plan = processor.generate_processing_plan(pdf_files)
            if plan:
                print(f"⏱️ 예상 처리 시간: {plan['estimated_time_minutes']}분")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


if __name__ == "__main__":
    test_processor()

    