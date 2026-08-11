# 개념 데이터 모델

이 문서는 기능 간 데이터 책임을 설명한다. 논리 엔티티와 관계는 docs/architecture/erd.md를 기준으로 하며 실제 컬럼과 제약은 Feature Packet과 마이그레이션에서 확정한다.

## 회원과 인증

- User(사용자): 로그인 아이디, 정규화 값, 이메일, 이메일 정규화 값, 비밀번호 해시, 인증 상태
- HealthProfile(건강 프로필): 생년월일, 성별, 키, 몸무게
- EmailVerification(이메일 인증): 사용자별 발급 이력, HMAC 인증번호 해시, 만료,
  재전송 가능 시각, 실패 횟수, 사용·대체 시각
- RefreshSession(리프레시 세션): 사용자, 토큰 식별자, 만료, 폐기 시각

## 카탈로그

- ProductCategory(제품 카테고리)
- Product(제품): 영양제 또는 의약품 유형, 브랜드, 이름, 이미지, 단위 형태, 총 용량, 게시 상태
- Nutrient(영양성분)
- ProductNutrient(제품 영양성분): 제품의 단위당 성분 함량
- ExpertComment(전문가 코멘트)
- PurchaseLink(구매 링크)

## 마이케어

- CareItem(복용 항목): 사용자, 제품, 구매일, 복용 시작일, 보유 수량, 회당 복용량, 하루 횟수, 활성·재고 상태
- CareNutrientSnapshot(복용 성분 스냅샷): CareItem 등록 시점의 성분과 단위당 함량
- CareHistory 또는 상태 이력: 소진과 사용 중단의 추적

재구매는 기존 소진 기록을 덮어쓰지 않고 새 CareItem 또는 명시적인 구매 이력으로 보존한다. 정확한 모델은 F-3.3 Feature Packet에서 결정한다.

## 알림

- Notification(알림): 사용자, CareItem, 종류, 기준일, 예약 시각, 화면 읽음 상태
- EmailDelivery(이메일 발송): Notification, 수신 주소, 상태, 시도 횟수, 마지막 오류

## 기준 데이터

- 영양소 기준 CSV: 나이 범위, 성별, 성분, 기준량, 단위, 출처와 버전

CSV는 적재 전에 필수 열, 나이 구간 중복, 단위와 키 중복을 검증한다.
