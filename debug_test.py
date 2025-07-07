#!/usr/bin/env python3
"""
URL 매핑 디버깅 테스트 스크립트
현재 크롤러와 요약기의 연동 상태를 확인합니다.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

from core.crawler import BusanNewsCrawler
from core.summarizer import BusanNewsSummarizer
import json

def test_crawler_output():
    """크롤러 출력 테스트"""
    print("🔍 크롤러 출력 테스트 시작...")
    
    crawler = BusanNewsCrawler()
    
    # 1페이지만 테스트
    results = crawler.crawl_news(max_pages=1)
    
    print(f"\n📊 크롤링 결과: {len(results)}개")
    
    if results:
        print("\n📋 첫 번째 결과:")
        first_result = results[0]
        print(json.dumps(first_result, indent=2, ensure_ascii=False))
        
        print(f"\n🔑 포함된 키들: {list(first_result.keys())}")
        
        # URL 필드 확인
        if 'url' in first_result:
            print(f"✅ URL 필드 존재: {first_result['url']}")
        else:
            print("❌ URL 필드 없음!")
            
        # 경로 필드 확인
        path_keys = [k for k in first_result.keys() if 'path' in k.lower()]
        print(f"📁 경로 관련 키들: {path_keys}")
    
    return results

def test_summarizer_input(crawler_results):
    """요약기 입력 테스트"""
    print("\n🔍 요약기 입력 테스트 시작...")
    
    if not crawler_results:
        print("❌ 크롤러 결과가 없습니다.")
        return
    
    summarizer = BusanNewsSummarizer()
    
    # 첫 번째 파일만 테스트
    test_result = crawler_results[0]
    
    print(f"📄 테스트 파일: {test_result.get('filename', 'unknown')}")
    print(f"🔗 URL: {test_result.get('url', 'N/A')}")
    
    # 파일 경로 확인
    pdf_path = None
    for path_key in ['path', 'filepath', 'file_path', 'pdf_path']:
        if path_key in test_result:
            pdf_path = Path(test_result[path_key])
            print(f"📁 PDF 경로 ({path_key}): {pdf_path}")
            break
    
    if not pdf_path:
        filename = test_result.get('filename')
        if filename:
            pdf_path = Path("data/pdfs") / filename
            print(f"📁 파일명으로 경로 구성: {pdf_path}")
    
    if pdf_path and pdf_path.exists():
        print(f"✅ PDF 파일 존재: {pdf_path}")
        
        # 요약 테스트
        source_url = test_result.get('url', 'https://www.busan.go.kr/nbtnewsBU')
        print(f"🔗 사용할 URL: {source_url}")
        
        md_file = summarizer.process_pdf_file(str(pdf_path), source_url=source_url)
        
        if md_file:
            print(f"✅ 요약 성공: {md_file}")
            
            # 생성된 MD 파일 내용 확인
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if source_url in content:
                print(f"✅ MD 파일에 URL 포함됨")
            else:
                print(f"❌ MD 파일에 URL 누락!")
                print(f"파일 내용 일부:\n{content[:500]}...")
        else:
            print("❌ 요약 실패")
    else:
        print(f"❌ PDF 파일 없음: {pdf_path}")

def test_existing_md_files():
    """기존 MD 파일들의 URL 확인"""
    print("\n🔍 기존 MD 파일 URL 확인...")
    
    md_dir = Path("data/md")
    if not md_dir.exists():
        print("❌ MD 디렉토리 없음")
        return
    
    md_files = list(md_dir.glob("*.md"))
    print(f"📄 MD 파일 수: {len(md_files)}개")
    
    url_counts = {
        "기본_URL": 0,
        "세부_URL": 0,
        "URL_없음": 0
    }
    
    for md_file in md_files[:5]:  # 처음 5개만 확인
        with open(md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'source_url:' in content:
            if 'view' in content or 'boardUid' in content:
                url_counts["세부_URL"] += 1
                print(f"✅ {md_file.name}: 세부 URL 포함")
            elif 'nbtnewsBU' in content:
                url_counts["기본_URL"] += 1
                print(f"⚠️ {md_file.name}: 기본 URL만 포함")
            else:
                url_counts["URL_없음"] += 1
                print(f"❌ {md_file.name}: URL 형식 불명")
        else:
            url_counts["URL_없음"] += 1
            print(f"❌ {md_file.name}: source_url 필드 없음")
    
    print(f"\n📊 URL 상태 요약:")
    for status, count in url_counts.items():
        print(f"  {status}: {count}개")

def main():
    """메인 테스트 함수"""
    print("🚀 URL 매핑 디버깅 테스트 시작\n")
    
    # 1. 크롤러 출력 테스트
    crawler_results = test_crawler_output()
    
    # 2. 요약기 입력 테스트
    if crawler_results:
        test_summarizer_input(crawler_results)
    
    # 3. 기존 MD 파일 확인
    test_existing_md_files()
    
    print("\n🎯 디버깅 테스트 완료!")

if __name__ == "__main__":
    main()