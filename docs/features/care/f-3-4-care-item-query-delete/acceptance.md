# F-3.4 인수 조건

## AC-F-3.4-001 사용자 소유 활성 목록

전제: 두 사용자가 영양제·의약품 CareItem을 가지고 있고 일부 항목은 소프트 삭제됐다.

행동: 한 사용자가 `GET /api/v1/care/items`를 요청한다.

결과: 현재 사용자 소유의 deleted_at NULL 항목만 200으로 반환하고 다른 사용자·삭제
항목은 포함하지 않는다. 비게시 제품의 등록 항목도 포함한다.

## AC-F-3.4-002 재구매 분리·표시 정보·정렬

같은 제품의 재구매분은 합산하지 않고 각각 반환한다. 각 항목은 현재 Product의 유형·
브랜드·이름·이미지와 CareItem의 구매일·복용 시작일·총수량·단위·복용 계획·등록 시각을
제공하고 `created_at DESC, id DESC`로 안정 정렬한다. 성분 스냅샷은 노출하지 않는다.

## AC-F-3.4-003 페이지네이션

- 기본 page=1·page_size=20이고 page_size는 최대 100이다.
- total은 현재 사용자의 활성 항목 전체 개수이며 has_next는 다음 페이지 존재 여부다.
- 범위를 넘는 페이지는 200과 빈 items, page·page_size·total·has_next를 반환한다.
- page<1 또는 page_size 범위 밖은 422 `VALIDATION_FAILED`다.

## AC-F-3.4-004 사용자 소유 항목 삭제

전제: 현재 사용자의 활성 CareItem과 성분 스냅샷이 있다.

행동: `DELETE /api/v1/care/items/{care_item_id}`를 요청한다.

결과: 204와 `Cache-Control: no-store`를 반환하고 deleted_at·updated_at을 같은 서버
시각으로 기록한다. CareItem과 성분 스냅샷 행은 보존되고 다음 활성 목록에서 제외된다.

## AC-F-3.4-005 삭제 소유권과 존재 숨김

존재하지 않는 ID, 다른 사용자 소유 ID와 이미 삭제된 ID를 삭제하면 모두 같은 404
`CARE_ITEM_NOT_FOUND`와 메시지를 반환하며 어떤 행도 변경하지 않는다.

## AC-F-3.4-006 인증·장애·캐시

- 미인증 목록·삭제는 401 `AUTH_REQUIRED`다.
- DB 실패는 503 `SERVICE_UNAVAILABLE`이고 삭제는 rollback된다.
- 목록 200과 삭제 204는 `Cache-Control: no-store`를 포함한다.
- 요청·응답에 user_id, deleted_at과 성분 스냅샷을 노출하지 않는다.

## 데이터·ERD 인수 조건

## AC-F-3.4-007 0014 데이터·ERD 일치

- 0014는 기존 CareItem을 deleted_at NULL 활성 상태로 유지한다.
- deleted_at nullable·시간 순서 CHECK·활성 목록 부분 인덱스가 ORM·마이그레이션·ERD에
  일치한다.
- downgrade는 CareItem과 성분 스냅샷을 보존하고 부분 인덱스·deleted_at만 제거하며
  재-upgrade할 수 있다.
- 사용자 데이터 시드와 AWS·AI·외부 서비스 의존성을 추가하지 않는다.

## 근거 연결표

| 인수 조건 ID | 자동 테스트 | 참고 사항 |
| --- | --- | --- |
| AC-F-3.4-001~002 | 목록 인수·저장소 통합 테스트 | 소유권·활성 필터·재구매·정렬·제품 join |
| AC-F-3.4-003 | 계약·인수 테스트 | 페이지 기본값·범위·빈 페이지 |
| AC-F-3.4-004~005 | 삭제 인수·서비스·저장소 테스트 | 소프트 삭제·보존·404 통일 |
| AC-F-3.4-006 | 인증·오류 계약 테스트 | 401·503·no-store·비노출 |
| AC-F-3.4-007 | 0014 왕복·스키마·ERD 검사 | ORM·마이그레이션·ERD 일치 |
