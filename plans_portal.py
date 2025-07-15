"""
부산시청 업무계획 포털 - BusanPlansPortal
=========================================
업무계획 MD 파일들을 로드하고 필터링하는 전용 클래스

주요 기능:
- 업무계획 MD 파일 로드
- 부서별/분야별 필터링
- 검색 기능
- 통계 정보 제공
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import logging

from config import (
    PLANS_MD_DIR, PLAN_DEPARTMENTS, AVAILABLE_PLAN_TAGS, PLAN_TAG_COLORS
)

logger = logging.getLogger(__name__)

class BusanPlansPortal:
    """부산시청 업무계획 포털 클래스"""
    
    def __init__(self):
        self.md_dir = PLANS_MD_DIR
        self.plans_data = []
        self.load_plans_data()
    
    def load_plans_data(self) -> List[Dict]:
        """업무계획 MD 파일들에서 데이터 로드"""
        plans_list = []
        
        if not self.md_dir.exists():
            logger.error(f"📁 업무계획 디렉토리가 없습니다: {self.md_dir}")
            return []
        
        md_files = list(self.md_dir.glob("*.md"))
        
        if not md_files:
            logger.warning("📄 업무계획 MD 파일이 없습니다.")
            return []
        
        for md_file in md_files:
            try:
                plan_item = self._parse_markdown_file(md_file)
                if plan_item:
                    plans_list.append(plan_item)
            except Exception as e:
                logger.error(f"업무계획 파일 파싱 오류 {md_file.name}: {e}")
                continue
        
        # 부서명순 정렬
        plans_list.sort(key=lambda x: x.get('department', ''))
        self.plans_data = plans_list
        
        logger.info(f"✅ 업무계획 {len(plans_list)}개 로드 완료")
        return plans_list
    
    def _parse_markdown_file(self, md_file: Path) -> Optional[Dict]:
        """업무계획 MD 파일에서 메타데이터와 내용 추출"""
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # frontmatter 파싱
            if not content.startswith('---'):
                return None
            
            frontmatter_end = content.find('---', 3)
            if frontmatter_end == -1:
                return None
            
            frontmatter = content[3:frontmatter_end]
            body = content[frontmatter_end + 3:].strip()
            
            # 메타데이터 추출
            metadata = {}
            for line in frontmatter.split('\n'):
                line = line.strip()
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    
                    if key == 'tags':
                        # JSON 형태의 태그 파싱
                        try:
                            metadata[key] = json.loads(value)
                        except:
                            # 간단한 형태 파싱
                            tags = value.strip('[]').replace('"', '').split(',')
                            metadata[key] = [tag.strip() for tag in tags if tag.strip()]
                    else:
                        metadata[key] = value
            
            # 본문에서 예산 정보 추출
            budget_info = self._extract_budget_from_body(body)
            
            # 부서명 추출 (파일명에서)
            department = self._extract_department_from_filename(md_file.name)
            
            return {
                'title': metadata.get('title', '업무계획'),
                'date': metadata.get('date', '2025-01-01'),
                'tags': metadata.get('tags', ['전체']),
                'department': metadata.get('department', department),
                'thumbnail_summary': metadata.get('thumbnail_summary', ''),
                'budget_info': budget_info,
                'detailed_summary': self._extract_summary_from_body(body),
                'file_path': str(md_file)
            }
            
        except Exception as e:
            logger.error(f"업무계획 MD 파싱 오류: {e}")
            return None
    
    def _extract_department_from_filename(self, filename: str) -> str:
        """파일명에서 부서명 추출"""
        try:
            # "2025년 부서명 주요업무계획.md" 형태에서 부서명 추출
            if "주요업무계획" in filename:
                # "2025년 " 제거하고 " 주요업무계획.md" 제거
                dept_part = filename.replace("2025년 ", "").replace(" 주요업무계획.md", "")
                
                # 🔧 특별 케이스 처리
                if dept_part == "부산광역시" or dept_part == "부산시":
                    return "부산광역시"  # 통합 시정
                
                return dept_part
            
            return "미분류"
            
        except Exception as e:
            logger.error(f"부서명 추출 실패: {e}")
            return "미분류"
    
    def _extract_budget_from_body(self, body: str) -> str:
        """본문에서 예산 정보 추출"""
        lines = body.split('\n')
        budget_lines = []
        
        # "## 💰 예산현황" 또는 "예산" 관련 섹션 찾기
        in_budget_section = False
        
        for line in lines:
            line = line.strip()
            if '## 💰 예산' in line or '예산현황' in line or '예산:' in line:
                in_budget_section = True
                continue
            elif line.startswith('##') and in_budget_section:
                break
            elif in_budget_section and line and not line.startswith('#'):
                budget_lines.append(line)
        
        if budget_lines:
            return '\n'.join(budget_lines[:3])  # 처음 3줄만
        
        # 예산 관련 키워드가 포함된 줄 찾기
        for line in lines:
            if any(keyword in line for keyword in ['억원', '백만원', '세출', '세입', '예산']):
                return line[:100]
        
        return "예산 정보 없음"
    
    def _extract_summary_from_body(self, body: str) -> str:
        """본문에서 요약 추출"""
        lines = body.split('\n')
        summary_lines = []
        
        # "## 📋 기본현황" 또는 "## 🎯 주요 추진과제" 부분 찾기
        target_sections = ['## 📋 기본현황', '## 🎯 주요', '## 📋 주요']
        
        for section in target_sections:
            in_target_section = False
            section_lines = []
            
            for line in lines:
                line = line.strip()
                if section in line:
                    in_target_section = True
                    continue
                elif line.startswith('##') and in_target_section:
                    break
                elif in_target_section and line and not line.startswith('#'):
                    section_lines.append(line)
            
            if section_lines:
                summary_lines.extend(section_lines[:3])  # 각 섹션에서 3줄까지
        
        if summary_lines:
            return '\n'.join(summary_lines)
        
        # 대안: 전체 본문에서 처음 200자
        return body[:200] + "..." if len(body) > 200 else body
    
    def get_department_stats(self) -> Dict:
        """부서별 통계 계산"""
        dept_counts = {}
        
        for plan in self.plans_data:
            dept = plan.get('department', '미분류')
            dept_counts[dept] = dept_counts.get(dept, 0) + 1
        
        return dept_counts
    
    def get_tag_stats(self) -> Dict:
        """분야별 통계 계산"""
        tag_counts = {}
        
        for plan in self.plans_data:
            tags = plan.get('tags', ['전체'])
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        # 전체 개수 추가
        tag_counts["전체"] = len(self.plans_data)
        
        return tag_counts
    
    def filter_plans(self, selected_departments: List[str] = None, 
                    search_query: str = "", 
                    selected_tags: List[str] = None) -> List[Dict]:
        """업무계획 필터링"""
        filtered_plans = self.plans_data.copy()
        
        # 부서별 필터링
        if selected_departments and "전체" not in selected_departments:
            # 선택된 분류에 해당하는 실제 부서명들 추출
            target_departments = []
            for dept_category in selected_departments:
                for display_name, dept_list in PLAN_DEPARTMENTS:
                    if display_name.endswith(dept_category) and dept_list != "전체":
                        target_departments.extend(dept_list)
            
            if target_departments:
                filtered_plans = [
                    plan for plan in filtered_plans
                    if any(dept in plan.get('department', '') for dept in target_departments)
                ]
        
        # 태그 필터링
        if selected_tags and "전체" not in selected_tags:
            filtered_plans = [
                plan for plan in filtered_plans
                if any(tag in selected_tags for tag in plan.get('tags', []))
            ]
        
        # 검색어 필터링
        if search_query:
            search_query = search_query.lower()
            filtered_plans = [
                plan for plan in filtered_plans
                if (search_query in plan.get('title', '').lower() or 
                    search_query in plan.get('department', '').lower() or
                    search_query in plan.get('detailed_summary', '').lower())
            ]
        
        return filtered_plans
    
    def get_plans_by_department_category(self, category: str) -> List[Dict]:
        """특정 분류에 속하는 업무계획들 반환"""
        if category == "전체":
            return self.plans_data
        
        # 해당 분류에 속하는 부서들 찾기
        target_departments = []
        for display_name, dept_list in PLAN_DEPARTMENTS:
            if display_name.endswith(category) and dept_list != "전체":
                target_departments.extend(dept_list)
        
        if not target_departments:
            return []
        
        return [
            plan for plan in self.plans_data
            if any(dept in plan.get('department', '') for dept in target_departments)
        ]
    
    def get_department_category(self, department: str) -> str:
        """부서명으로부터 분류 카테고리 찾기"""
        for display_name, dept_list in PLAN_DEPARTMENTS:
            if dept_list != "전체" and any(dept in department for dept in dept_list):
                # "🏛️ 기획감사" -> "기획감사" 추출
                return display_name.split(' ', 1)[1] if ' ' in display_name else display_name
        
        return "전체"
    
    def search_plans(self, query: str) -> List[Dict]:
        """업무계획 검색"""
        if not query:
            return self.plans_data
        
        query_lower = query.lower()
        results = []
        
        for plan in self.plans_data:
            score = 0
            
            # 제목 매칭 (가중치 3)
            if query_lower in plan.get('title', '').lower():
                score += 3
            
            # 부서명 매칭 (가중치 2)
            if query_lower in plan.get('department', '').lower():
                score += 2
            
            # 내용 매칭 (가중치 1)
            if query_lower in plan.get('detailed_summary', '').lower():
                score += 1
            
            if score > 0:
                plan_with_score = plan.copy()
                plan_with_score['search_score'] = score
                results.append(plan_with_score)
        
        # 점수순 정렬
        results.sort(key=lambda x: x.get('search_score', 0), reverse=True)
        return results


# 유틸리티 함수들

def get_plans_portal_stats(portal: BusanPlansPortal) -> Dict:
    """업무계획 포털 통계 정보"""
    dept_stats = portal.get_department_stats()
    tag_stats = portal.get_tag_stats()
    
    return {
        'total_plans': len(portal.plans_data),
        'department_count': len(dept_stats),
        'tag_distribution': tag_stats,
        'largest_department': max(dept_stats.items(), key=lambda x: x[1]) if dept_stats else ("없음", 0),
        'categories': len(PLAN_DEPARTMENTS) - 1  # 전체 제외
    }

def validate_plans_data(portal: BusanPlansPortal) -> Dict:
    """업무계획 데이터 유효성 검사"""
    issues = []
    
    if not portal.plans_data:
        issues.append("업무계획 데이터가 없습니다")
        return {"valid": False, "issues": issues}
    
    # 필수 필드 체크
    for i, plan in enumerate(portal.plans_data):
        if not plan.get('title'):
            issues.append(f"계획 {i+1}: 제목 누락")
        if not plan.get('department'):
            issues.append(f"계획 {i+1}: 부서명 누락")
        if not plan.get('file_path'):
            issues.append(f"계획 {i+1}: 파일 경로 누락")
    
    # 중복 체크
    titles = [plan.get('title', '') for plan in portal.plans_data]
    duplicates = [title for title in set(titles) if titles.count(title) > 1]
    if duplicates:
        issues.append(f"중복 제목 발견: {', '.join(duplicates)}")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "total_checked": len(portal.plans_data)
    }


# 테스트 함수
def test_plans_portal():
    """업무계획 포털 테스트"""
    print("🧪 업무계획 포털 테스트 시작...")
    
    try:
        portal = BusanPlansPortal()
        stats = get_plans_portal_stats(portal)
        validation = validate_plans_data(portal)
        
        print(f"📊 통계:")
        print(f"  - 총 업무계획: {stats['total_plans']}개")
        print(f"  - 부서 수: {stats['department_count']}개")
        print(f"  - 분류 수: {stats['categories']}개")
        
        print(f"✅ 유효성 검사: {'통과' if validation['valid'] else '실패'}")
        if validation['issues']:
            for issue in validation['issues'][:3]:
                print(f"  - {issue}")
        
        # 검색 테스트
        search_results = portal.search_plans("교육")
        print(f"🔍 '교육' 검색 결과: {len(search_results)}개")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")


if __name__ == "__main__":
    test_plans_portal()