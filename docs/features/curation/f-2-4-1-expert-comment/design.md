# F-2.4.1 설계

## API 계약

- 메서드와 경로: 기존 `GET /api/v1/curation/products/{product_id}`
- 인증: 없음
- 요청: 기존 UUID path parameter
- 성공 응답: 기존 ProductDetailResponse에 `expert_comments[]` 추가
- 오류 응답: 기존 잘못된 UUID 422, 공개 제품 없음 404, DB 장애 503 유지
- 멱등성: 읽기 API이며 같은 DB 상태에서 같은 코멘트 순서를 반환한다.

## 데이터 설계

- 엔티티: expert_comments
- 관계와 카디널리티: products 1:N expert_comments
- 제약 조건: UUID PK, product FK, trim author_label 1~100자, trim content
  1~2000자, sort_order >= 0, is_active 필수
- 인덱스: `(product_id, is_active, sort_order, id)`
- 마이그레이션: `20260812_0009_expert_comments`, 선행 0008
- 백필과 기존 데이터 영향: 신규 테이블만 추가하며 기존 상세·제품 행 백필은 없다.
- 이력과 삭제: 제품 삭제 시 코멘트 CASCADE, 비노출은 is_active=false를 사용한다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: expert_comments는 필드가 있는 논리 예정 엔티티
- 변경 후 구조: F-2.4.1 실제 테이블의 값 제약·인덱스·삭제·노출 정책 확정
- 변경하지 않는 경우의 이유: 해당 없음
- ERD 검증 방법: `make erd-check`, 0009 downgrade/upgrade와 `alembic check`

## 애플리케이션 흐름

1. 기존 상세 저장소가 F-2.4 공개 제품 조건을 확인한다.
2. 활성 코멘트를 product_id로 조회해 sort_order·id로 정렬한다.
3. 저장소·서비스의 상세 결과에 코멘트를 전달한다.
4. router가 id·author_label·content 일반 문자열 배열을 응답한다.
5. 기존 공개 제품 없음과 DB 장애 변환을 그대로 재사용한다.

## 보안과 개인정보

- 소유권 검사: 공개 기준 콘텐츠라 해당 없음
- 민감 필드: 사용자·건강·토큰 데이터가 없고 author_label은 전문가 계정이 아닌
  시드 표시 문자열이다.
- 로그 제외 항목: DB 오류·SQL 상세를 응답에 노출하지 않는다. content를 별도 로그에
  기록하지 않는다.

## 로컬 어댑터

- 데이터베이스: 로컬 PostgreSQL 개발·테스트 DB
- 시간: 새 시간 계산 없음
- 이메일: 해당 없음
- 스케줄러: 해당 없음

## 호환성

- OpenAPI 영향: ProductDetailResponse에 필수 expert_comments 배열을 추가하는 additive 변경
- 기존 데이터 영향: 신규 테이블이 비어 있으면 기존 상세가 expert_comments=[]로 정상 동작
- 롤백: 앱을 되돌리고 0009에서 0008로 downgrade하면 코멘트만 제거되고 F-2.4
  제품 상세는 유지된다.
