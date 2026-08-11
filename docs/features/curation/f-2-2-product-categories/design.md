# F-2.2 설계

## API 계약

- 메서드와 경로: GET /api/v1/curation/categories
- 인증: 없음. 공개 읽기 API이며 AccessCookieAuth를 요구하지 않는다.
- 요청: 본문·쿼리 없음
- 성공 응답: 200 `{"items":[{"slug":"all","name":"전체"}, ...]}`
- 오류 응답: 503 SERVICE_UNAVAILABLE
- 멱등성: 읽기 전용 GET이며 같은 DB 상태에서 같은 순서와 내용을 반환한다.
- 페이지네이션: 카테고리는 작은 기준 목록이므로 적용하지 않는다.

## 데이터 설계

- 엔티티: product_categories 신규
- 필드: id UUID PK, slug varchar(50), name varchar(50), is_active boolean,
  sort_order integer
- 관계와 카디널리티: F-2.2에서는 독립 기준 엔티티다. products와의 N:M 매핑은
  F-2.3에서 추가한다.
- 제약 조건: slug UNIQUE·소문자 영숫자/내부 하이픈 CHECK, name trim 길이 CHECK,
  sort_order >= 0 CHECK, 전 필드 NOT NULL
- 인덱스: (is_active, sort_order, slug) 비고유 조회 인덱스
- 마이그레이션: 20260812_0006_product_categories, 이전 head 20260811_0005 뒤에 적용
- 백필과 기존 데이터 영향: 신규 빈 테이블이라 백필 없음. 마이그레이션 뒤 별도 시드로
  기준 행을 적재한다.
- 이력과 삭제: 운영자 API는 없다. 공개 제외는 is_active=false를 사용하며 시드 기준
  행은 다음 시드 실행 시 승인 상태로 복원된다.

## ERD 영향

- docs/architecture/erd.md 변경: 예
- 변경 전 구조: product_categories가 논리 ERD에만 있고 ORM·마이그레이션은 없다.
- 변경 후 구조: 동일 필드의 실제 테이블, slug·값 CHECK와 활성 정렬 인덱스가 존재한다.
  products와의 관계는 논리 ERD에 남지만 실제 매핑은 F-2.3까지 미구현임을 표시한다.
- 마이그레이션 고려: downgrade는 인덱스 뒤 테이블을 제거하며 F-2.3이 적용된 뒤에는
  독립 downgrade하지 않는다.
- ERD 검증 방법: validate_erd.py, 빈 PostgreSQL upgrade head, alembic check,
  ORM·마이그레이션 제약 직접 비교

## 애플리케이션 흐름

1. 라우터가 공개 GET 요청을 서비스로 전달한다.
2. 저장소가 is_active=true 조건과 sort_order·slug 정렬로 DB 행을 읽는다.
3. 서비스가 DB와 무관한 `all`·`전체` 항목을 맨 앞에 한 번 추가한다.
4. 라우터가 items 응답 스키마로 직렬화한다.
5. SQLAlchemy 오류는 저장소 경계에서 감추고 서비스가 503 AppError로 변환한다.

## 보안과 개인정보

- 소유권 검사: 공개 기준 데이터이므로 사용자 소유권과 인증이 없다.
- 입력 공격면: 사용자 입력, 동적 SQL과 외부 URL을 받지 않는다.
- 민감 필드: 개인정보·건강정보·token을 조회하거나 반환하지 않는다.
- 로그 제외 항목: DB 예외 상세는 공개 응답에 포함하지 않는다.

## 로컬 어댑터

- 데이터베이스: PostgreSQL 16, SQLAlchemy 동기 읽기와 PostgreSQL upsert 시드
- 시간: 사용하지 않음
- 이메일: 사용하지 않음
- 스케줄러: 사용하지 않음

## 호환성

- OpenAPI 영향: 공개 GET /curation/categories와 200·503 스키마 추가
- 기존 데이터 영향: 신규 테이블이라 기존 회원·세션 데이터 영향 없음
- 롤백: API·시드 등록·ORM을 제거한 뒤 0006 downgrade로 인덱스와 테이블을 제거한다.
